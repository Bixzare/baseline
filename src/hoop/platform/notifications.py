"""Bounded Windows notices; shell events do not establish owner-visible delivery."""

import json
import os
import subprocess
import sys
from typing import Any

SCRIPT = """$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
$baselineContext = New-Object System.Windows.Forms.ApplicationContext
$baselineTimer = New-Object System.Windows.Forms.Timer
$baselineNotice = New-Object System.Windows.Forms.NotifyIcon
$script:baselineShown = $false
try {
  $baselineNotice.Icon = [System.Drawing.SystemIcons]::Information
  $baselineNotice.Text = 'Baseline'
  $baselineNotice.add_BalloonTipShown({$script:baselineShown = $true})
  $baselineNotice.Visible = $true
  $baselineMessage = if($env:BASELINE_NOTIFICATION_REHEARSAL -eq '1') {
    'Rehearsal completed; production remains disabled.'
  } else {
    'Operational check needs review. See the local health report.'
  }
  $baselineTimer.Interval = 10000
  $baselineTimer.add_Tick({$baselineContext.ExitThread()})
  $baselineTimer.Start()
  $baselineNotice.ShowBalloonTip(10000, 'Baseline', $baselineMessage,
    [System.Windows.Forms.ToolTipIcon]::Info)
  [System.Windows.Forms.Application]::Run($baselineContext)
  @{queued=$true;shell_shown_event=$script:baselineShown}|ConvertTo-Json -Compress
} finally {
  $baselineTimer.Stop()
  $baselineTimer.Dispose()
  $baselineNotice.Visible = $false
  $baselineNotice.Dispose()
  $baselineContext.Dispose()
}
"""


def notify(*, rehearsal: bool = False) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"attempted": False, "delivery": "unverified"}
    failed = {"attempted": True, "queued": False, "delivery": "unverified"}
    # The desktop helper needs session paths, never provider or database secrets.
    env = {
        key: os.environ[key]
        for key in [
            "PATH",
            "SystemRoot",
            "WINDIR",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
        ]
        if key in os.environ
    }
    env["BASELINE_NOTIFICATION_REHEARSAL"] = "1" if rehearsal else "0"
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-Command", SCRIPT],
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode:
            return failed
        payload = json.loads(result.stdout)
        if (
            not isinstance(payload, dict)
            or payload.get("queued") is not True
            or type(payload.get("shell_shown_event")) is not bool
        ):
            return failed
        return {
            "attempted": True,
            "queued": True,
            "shell_shown_event": payload["shell_shown_event"],
            "delivery": "unverified",
        }
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        return failed
