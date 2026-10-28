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
