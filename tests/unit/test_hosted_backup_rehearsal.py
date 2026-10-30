"""Manual rehearsal defaults and target guards need no hosted credentials."""

import pytest

from hoop.platform.backup import BackupError
from scripts.rehearse_hosted_backup import local_restore_admin, main, project


def test_default_plan_needs_no_credentials_or_network(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["hosted-backup"])
    assert main() == 0
    assert '"automation_enabled": false' in capsys.readouterr().out


@pytest.mark.parametrize(
    "dsn",
    [
        "host=hosted.invalid dbname=baseline_test password=private-fixture",
        "host=127.0.0.1 dbname=postgres password=private-fixture",
        "host=127.0.0.1 dbname=production password=private-fixture",
    ],
)
def test_restore_admin_refuses_remote_and_unrelated_databases(dsn: str) -> None:
    with pytest.raises(BackupError, match="explicit_local_test_admin") as error:
        local_restore_admin(dsn)
    assert "private-fixture" not in str(error.value)


def test_mismatched_project_is_rejected_before_connection(monkeypatch) -> None:
    monkeypatch.setenv("BASELINE_BACKUP_PROJECT_ID", "fixture")
    monkeypatch.setenv("BASELINE_SUPABASE_URL", "https://other.supabase.co")
    with pytest.raises(BackupError, match="project_mismatch"):
        project()


def test_restore_project_identity_needs_no_original_source_credential(monkeypatch) -> None:
    monkeypatch.setenv("BASELINE_BACKUP_PROJECT_ID", "fixture")
    monkeypatch.setenv("BASELINE_SUPABASE_URL", "https://fixture.supabase.co")
    monkeypatch.delenv("BASELINE_MIGRATION_DSN", raising=False)
    assert project() == "fixture"


@pytest.mark.parametrize("budget", [0, -1, 1801, True])
def test_readback_budget_is_bounded_before_private_setup(tmp_path, budget) -> None:
    from scripts.rehearse_hosted_backup import restore_downloaded

    with pytest.raises(BackupError, match="bounded_readback_budget_required"):
        restore_downloaded(tmp_path, readback_seconds=budget)


@pytest.mark.parametrize("value", [{}, [], ["invalid"], [{"label": "x"}]])
def test_invalid_history_inventory_is_rejected_before_private_setup(tmp_path, monkeypatch, value):
    import json

    from scripts.rehearse_hosted_backup import export_current

    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(value))

    def forbidden(*args, **kwargs):
        raise AssertionError("No private setup or provider access on invalid inventory")

    monkeypatch.setattr("scripts.rehearse_hosted_backup.project", forbidden)
    with pytest.raises(BackupError):
        export_current(tmp_path / "out", archive_inventory=path)


def test_dirty_backup_implementation_is_rejected_before_private_setup(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from scripts.rehearse_hosted_backup import export_current

    monkeypatch.setattr(
        "scripts.rehearse_hosted_backup.subprocess.run",
        lambda *a, **k: SimpleNamespace(returncode=1),
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("No source access with uncommitted implementation")

    monkeypatch.setattr("scripts.rehearse_hosted_backup.project", forbidden)
    with pytest.raises(BackupError, match="implementation_must_be_committed"):
        export_current(tmp_path / "out")


@pytest.mark.parametrize("reason", ["remote_readback_budget_exhausted", "private token text"])
def test_rehearsal_failure_exposes_only_allowlisted_reason(tmp_path, monkeypatch, capsys, reason):
    import json

    def failed(*args, **kwargs):
        raise BackupError(reason)

    monkeypatch.setattr("scripts.rehearse_hosted_backup.restore_downloaded", failed)
    monkeypatch.setattr("sys.argv", ["hosted-backup", "restore", "--output", str(tmp_path)])
    assert main() == 1
    body = json.loads(capsys.readouterr().out)
    assert body["failure_type"] == "BackupError"
    assert body.get("failure_detail") == (
        "remote_readback_budget_exhausted" if reason.startswith("remote_") else None
    )
    assert "private token" not in json.dumps(body)
