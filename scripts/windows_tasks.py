"""Render disabled owner tasks or rehearse one disposable interactive task."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from hoop.platform.local_artifacts import atomic_json
from hoop.platform.windows_tasks import definition

ROOT = Path(__file__).resolve().parents[1]


def powershell(script: str, **values: str) -> str:
    if sys.platform != "win32":
        raise RuntimeError("Windows setup only")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        env={**os.environ, **values},
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise RuntimeError("Task operation failed; inspect intended-session prerequisites")
    return result.stdout.strip()


def plan(output: Path) -> dict[str, object]:
    if not (ROOT / ".venv/Scripts/pythonw.exe").exists():
        raise RuntimeError("Project pythonw environment required")
    sid = powershell("[Security.Principal.WindowsIdentity]::GetCurrent().User.Value")
    output.mkdir(parents=True, exist_ok=True)
    for name, collector in [("Baseline-Watchdog", False), ("Baseline-LocalCollector", True)]:
        (output / (name + ".xml")).write_text(
            definition(ROOT, sid, collector=collector), encoding="utf-8"
        )
    return {
        "task_names": ["Baseline-Watchdog", "Baseline-LocalCollector"],
        "enabled": False,
        "principal": "current interactive owner",
        "credentials_in_definitions": False,
    }


def register_disabled(output: Path) -> dict[str, object]:
    result = plan(output)
    names = result["task_names"]
    assert isinstance(names, list)
    for name in names:
        powershell(
            """$ErrorActionPreference='Stop'
          if(Get-ScheduledTask -TaskName $env:BASELINE_TASK_NAME -ErrorAction SilentlyContinue){
            throw 'Task exists; preserve and review it'
          }
          $baselineXml = [IO.File]::ReadAllText($env:BASELINE_TASK_XML)
          $baselineTask = Register-ScheduledTask -TaskName $env:BASELINE_TASK_NAME -Xml $baselineXml
          if($baselineTask.State -ne 'Disabled'){throw 'Expected disabled task'}
          """,
            BASELINE_TASK_NAME=str(name),
            BASELINE_TASK_XML=str((output / (str(name) + ".xml")).resolve()),
        )
    atomic_json(output / "registration.json", result)
    return result


def rehearsal(output: Path) -> dict[str, object]:
    sid = powershell("[Security.Principal.WindowsIdentity]::GetCurrent().User.Value")
    name = "Baseline-Rehearsal-" + uuid4().hex[:12]
    invocation = uuid4()
    output.mkdir(parents=True, exist_ok=True)
    xml = output / (name + ".xml")
    xml.write_text(
        definition(ROOT, sid, rehearsal=True, output=output, invocation=str(invocation)),
        encoding="utf-8",
    )
    created = False
    try:
        powershell(
            """$ErrorActionPreference='Stop'
          if(Get-ScheduledTask -TaskName $env:BASELINE_TASK_NAME -ErrorAction SilentlyContinue){
            throw 'Task exists'
          }
          $baselineXml = [IO.File]::ReadAllText($env:BASELINE_TASK_XML)
          Register-ScheduledTask -TaskName $env:BASELINE_TASK_NAME -Xml $baselineXml | Out-Null
          try {
            Start-ScheduledTask -TaskName $env:BASELINE_TASK_NAME
          } catch {
            Unregister-ScheduledTask -TaskName $env:BASELINE_TASK_NAME -Confirm:$false
            throw
          }
          """,
            BASELINE_TASK_NAME=name,
            BASELINE_TASK_XML=str(xml.resolve()),
        )
        created = True
        deadline = time.monotonic() + 40
        report = output / "latest-health.json"
        while time.monotonic() < deadline:
            if report.exists():
                saved = json.loads(report.read_text())
                if saved.get("invocation_id") == str(invocation):
                    state = json.loads(
                        powershell(
                            """$info=Get-ScheduledTaskInfo -TaskName $env:BASELINE_TASK_NAME
                      $task=Get-ScheduledTask -TaskName $env:BASELINE_TASK_NAME
                      @{state=[string]$task.State;last_result=$info.LastTaskResult;
                        last_run=[string]$info.LastRunTime}|ConvertTo-Json -Compress
                      """,
                            BASELINE_TASK_NAME=name,
                        )
                    )
                    if state["state"] != "Running":
                        return {
                            "task_name": name,
                            "invocation_id": str(invocation),
                            "task": state,
                            "report_state": saved["state"],
                            "notification": saved.get("notification"),
                            "actual_provider_access": False,
                            "production_enabled": False,
                        }
            time.sleep(0.5)
        raise RuntimeError("Task completion was not verified within the bounded rehearsal")
    finally:
        if created:
            assert name.startswith("Baseline-Rehearsal-") and len(name) == 31
            powershell(
                "Unregister-ScheduledTask -TaskName $env:BASELINE_TASK_NAME -Confirm:$false",
                BASELINE_TASK_NAME=name,
            )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["plan", "register-disabled", "rehearse"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    action = {"plan": plan, "register-disabled": register_disabled, "rehearse": rehearsal}[
        args.operation
    ]
    try:
        result = action(args.output.resolve())
        atomic_json(args.output / "task-report.json", result)
        print(json.dumps(result, sort_keys=True))
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired):
        print(json.dumps({"state": "unverified", "reason_code": "windows_task_setup_failed"}))
        raise SystemExit(1) from None
