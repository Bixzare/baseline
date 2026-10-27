"""Versioned least-privilege definitions; no credentials or visible console helpers."""

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

NAMESPACE = "http://schemas.microsoft.com/windows/2004/02/mit/task"


def definition(
    root: Path,
    sid: str,
    *,
    rehearsal: bool = False,
    output: Path | None = None,
    invocation: str | None = None,
    collector: bool = False,
) -> str:
    if not sid.startswith("S-1-") or any(ch not in "S-0123456789" for ch in sid):
        raise ValueError("Verified Windows user SID required")
    root = root.resolve()
    output = output or root / "artifacts/windows-health"
    task = ET.Element("Task", {"version": "1.4", "xmlns": NAMESPACE})

    def node(
        parent: ET.Element, name: str, value: str | None = None, **attributes: str
    ) -> ET.Element:
        child = ET.SubElement(parent, name, attributes)
        if value is not None:
            child.text = value
        return child

    registration = node(task, "RegistrationInfo")
    node(registration, "Description", "Baseline operational check; production defaults disabled")
    triggers = node(task, "Triggers")
    trigger = node(triggers, "TimeTrigger")
    repetition = node(trigger, "Repetition")
    node(repetition, "Interval", "PT15M")
    node(repetition, "StopAtDurationEnd", "false")
    begin = datetime.now(UTC) + (timedelta(days=1) if rehearsal else timedelta())
    node(trigger, "StartBoundary", begin.replace(microsecond=0).isoformat())
    node(trigger, "Enabled", "true")
    principals = node(task, "Principals")
    principal = node(principals, "Principal", id="Owner")
    node(principal, "UserId", sid)
    node(principal, "LogonType", "InteractiveToken")
    node(principal, "RunLevel", "LeastPrivilege")
    settings = node(task, "Settings")
    for name, value in {
        "MultipleInstancesPolicy": "IgnoreNew",
        "DisallowStartIfOnBatteries": "false",
        "StopIfGoingOnBatteries": "false",
        "StartWhenAvailable": "true",
        "RunOnlyIfNetworkAvailable": "false",
        "Enabled": "true" if rehearsal else "false",
        "Hidden": "true",
        "WakeToRun": "false",
        "ExecutionTimeLimit": "PT12M",
    }.items():
        node(settings, name, value)
    actions = node(task, "Actions", Context="Owner")
    execute = node(actions, "Exec")
    node(execute, "Command", str(root / ".venv/Scripts/pythonw.exe"))
    args = [
        "-m",
        "hoop.domains.nba.watchdog",
        "--mode",
        "rehearsal" if rehearsal else "production",
        "--output",
        str(output),
    ]
    if rehearsal:
        args += ["--fixture-state", str(root / "tests/fixtures/ops/health.json"), "--notify"]
        if invocation:
            args += ["--invocation", invocation]
    elif collector:
        args = [
            "-m",
            "hoop.domains.nba.operations",
            "local_sources",
            "--mode",
            "production",
            "--environment",
            "local",
            "--output",
            str(root / "artifacts/local-collection"),
        ]
    node(execute, "Arguments", subprocess.list2cmdline(args))
    node(execute, "WorkingDirectory", str(root))
    return ET.tostring(task, encoding="unicode")
