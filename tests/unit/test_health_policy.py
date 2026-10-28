import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from hoop.domains.nba.health_policy import assess
from hoop.platform.windows_tasks import definition

NOW = datetime(2026, 10, 27, 10, tzinfo=UTC)


def good() -> dict[str, Any]:
    data = json.loads((Path(__file__).parents[1] / "fixtures/ops/health.json").read_text())[
        "snapshot"
    ]
    data["events"][0]["valid_forecast"] = True
    data["runs"] = {
        name: {"started": NOW.isoformat(), "succeeded": NOW.isoformat()}
        for name in ["nightly", "dispatcher"]
    }
    data["backup"] = {"verified": True, "cutoff": NOW.isoformat()}
    data["missing_capabilities"] = []
    data["capacity"] = {
        name: {
            "used_bytes": 10,
            "limit_bytes": 100,
            "limit_verified": True,
            "provider_usage_known": True,
        }
        for name in ["database", "objects"]
    }
    return data


def condition(report: dict[str, Any], key: str) -> dict[str, Any]:
    return next(c for c in report["conditions"] if c["alert_key"] == key)


@pytest.mark.parametrize("seconds,bad", [(2699, False), (2700, True), (2701, True)])
def test_heartbeat_threshold_uses_operation_completion(seconds: int, bad: bool) -> None:
    data = good()
    data["runs"]["dispatcher"]["succeeded"] = (NOW - timedelta(seconds=seconds)).isoformat()
    report = assess(NOW, data)
    assert (condition(report, "nba:dispatcher:succeeded")["state"] == "open") == bad
    assert condition(report, "nba:dispatcher:started")["state"] == "resolved"


@pytest.mark.parametrize(
    "minutes,attempt,critical",
    [
        (91, False, False),
        (90, True, False),
        (15, False, True),
        (14, False, True),
        (-5, False, True),
    ],
)
def test_missing_forecast_recovery_and_strict_cutoff(
    minutes: int, attempt: bool, critical: bool
) -> None:
    data = good()
    data["events"][0].update(
        valid_forecast=False, start=(NOW + timedelta(minutes=minutes)).isoformat()
    )
    data["fallback_enabled"] = True
    report = assess(NOW, data)
    assert bool(report["recovery_event_ids"]) == attempt
    if minutes <= 90:
        event = condition(report, "nba:event:" + data["events"][0]["event_id"])
        assert (event["severity"] == "critical") == critical


def test_nightly_equality_utc_offset_and_backup_age_do_not_refresh_on_upload() -> None:
    data = good()
    data["runs"]["nightly"]["succeeded"] = None
    before = assess(datetime(2026, 10, 27, 9, 16, 59, tzinfo=UTC), data)
    assert not any(c["alert_key"] == "nba:nightly:completion" for c in before["conditions"])
    assert (
        condition(
            assess(datetime.fromisoformat("2026-10-27T11:17:00+02:00"), data),
            "nba:nightly:completion",
        )["state"]
        == "open"
    )
    data = good()
    data["backup"].update(
        cutoff=(NOW - timedelta(hours=24)).isoformat(), uploaded_at=NOW.isoformat()
    )
    assert condition(assess(NOW, data), "nba:backup:age")["state"] == "resolved"
    assert (
        condition(assess(NOW + timedelta(microseconds=1), data), "nba:backup:age")["state"]
        == "open"
    )


@pytest.mark.parametrize(
    "used,warning,paused",
    [(59, False, False), (60, True, False), (79, True, False), (80, True, True)],
)
def test_capacity_thresholds_preserve_required_work(used: int, warning: bool, paused: bool) -> None:
    data = good()
    data["capacity"]["database"]["used_bytes"] = used
    report = assess(NOW, data)
    assert (condition(report, "nba:capacity:database")["state"] == "open") == warning
    assert report["pause_optional"] == paused


def test_unknowns_and_stale_essential_inputs_never_enable_recovery() -> None:
    data = good()
    assert assess(NOW, data)["state"] == "healthy"
    data["events"][0].update(valid_forecast=False, essential_fresh=False)
    data["fallback_enabled"] = True
    data["capacity"]["objects"]["provider_usage_known"] = False
    data["backup"] = {}
    report = assess(NOW, data)
    assert not report["recovery_event_ids"]
    assert condition(report, "nba:backup:age")["state"] == "open"
    assert condition(report, "nba:capacity:objects_provider")["state"] == "open"


def test_unresolved_finals_stay_visible_without_guessing_finish_time() -> None:
    data = good()
    data["pending_outcomes"] = [
        {"event_id": "fixture", "state": "final", "outcome_state": "partial"},
        {"event_id": "ongoing", "state": "in_progress", "outcome_state": None},
    ]
    report = assess(NOW, data)
    assert condition(report, "nba:outcome:fixture")["state"] == "open"
    assert not any(c["alert_key"] == "nba:outcome:ongoing" for c in report["conditions"])


def test_windows_definitions_are_disabled_interactive_and_have_no_secrets(tmp_path: Path) -> None:
    from xml.etree import ElementTree as ET

    from hoop.platform.windows_tasks import NAMESPACE

    root = ET.fromstring(definition(tmp_path, "S-1-5-21-111", collector=False))
    ns = {"t": NAMESPACE}
    assert root.find("t:Settings/t:Enabled", ns).text == "false"
    assert root.find("t:Principals/t:Principal/t:LogonType", ns).text == "InteractiveToken"
    assert root.find("t:Principals/t:Principal/t:RunLevel", ns).text == "LeastPrivilege"
    assert root.find("t:Actions/t:Exec/t:Command", ns).text.endswith("pythonw.exe")
    text = ET.tostring(root).decode()
    for forbidden in ["PASSWORD", "TOKEN", "DSN", "Bypass"]:
        assert forbidden not in text
