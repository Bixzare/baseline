from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from hoop.platform.backup import BackupError, contained, finalize, remote_readback, verify_set
from hoop.platform.backup.onedrive import OneDrive
from hoop.platform.local_artifacts import LocalArtifacts
from hoop.platform.provenance import digest


def fixture_set(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    stage, sync = tmp_path / "stage", tmp_path / "sync"
    raw = tmp_path / "fixture.dump"
    raw.write_bytes(b"fixture-dump")
    artifact = LocalArtifacts(stage).put(raw, kind="database", format="pg_custom")
    manifest = {
        "backup_id": str(uuid4()),
        "schema_version": 1,
        "represented_cutoff": "2026-10-27T08:00:00Z",
        "source_project": "fixture",
        "files": [{"label": "database", **artifact}],
        "artifact_inventory": [],
        "archive_inventory": [],
    }
    return stage, sync, manifest


@pytest.mark.parametrize(
    "path", ["../outside", "/absolute", "objects/../secret", "C:\\secret", "a//b"]
)
def test_backup_path_escape_refused(tmp_path: Path, path: str) -> None:
    with pytest.raises(BackupError):
        contained(tmp_path, path)


def test_immutable_finalization_deduplicates_and_stops_partial_or_conflicting_sets(
    tmp_path: Path,
) -> None:
    stage, sync, manifest = fixture_set(tmp_path)
    sha = finalize(stage, sync, manifest)
    assert finalize(stage, sync, manifest) == sha
    assert verify_set(sync, manifest["backup_id"], sha) == manifest
    changed = {**manifest, "source_project": "changed"}
    with pytest.raises(BackupError, match="conflicting"):
        finalize(stage, sync, changed)
    (sync / "sets" / manifest["backup_id"] / "COMPLETE").unlink()
    with pytest.raises(FileNotFoundError):
        verify_set(sync, manifest["backup_id"], sha)


def test_local_presence_is_not_remote_readback_and_old_cutoff_is_preserved(tmp_path: Path) -> None:
    stage, sync, manifest = fixture_set(tmp_path)
    sha = finalize(stage, sync, manifest)

    class Missing:
        evidence_kind = "synthetic_remote_fixture"

        def download(self, *args: Any) -> None:
            raise BackupError("remote_pending")

    with pytest.raises(BackupError, match="remote_pending"):
        remote_readback(
            Missing(),
            tmp_path / "download",
            backup_id=manifest["backup_id"],
            expected_hash=sha,
            source_project="fixture",
            forbidden_roots=[sync, stage],
        )
    assert (
        verify_set(sync, manifest["backup_id"], sha)["represented_cutoff"] == "2026-10-27T08:00:00Z"
    )
    with pytest.raises(BackupError, match="independent"):
        remote_readback(
            Missing(),
            sync / "download",
            backup_id=manifest["backup_id"],
            expected_hash=sha,
            source_project="fixture",
            forbidden_roots=[sync, stage],
        )


def test_wrong_manifest_hash_and_missing_archive_fail(tmp_path: Path) -> None:
    stage, sync, manifest = fixture_set(tmp_path)
    manifest["archive_inventory"] = [{"label": "missing", "sha256": digest(b"x"), "byte_count": 1}]
    with pytest.raises(BackupError, match="archive_not_in_complete"):
        finalize(stage, sync, manifest)
    assert not sync.exists()


@pytest.mark.parametrize(
    "remote", ["local:/tmp/backup", "onedrive:../other", "C:/backup", ":local:/tmp"]
)
def test_onedrive_rejects_unconfigured_or_unsafe_remote(remote: str) -> None:
    with pytest.raises(BackupError):
        OneDrive(Path("not-installed"), remote, "v1.0.0")


def test_rclone_local_backend_cannot_count_as_off_device(monkeypatch: Any) -> None:
    import subprocess

    def fake(command: Any, **kwargs: Any) -> Any:
        return subprocess.CompletedProcess(
            command, 0, b"rclone v1.0.0\n" if command[1] == "version" else b"backup: local\n", b""
        )

    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(BackupError, match="not_verified_onedrive"):
        OneDrive(Path("rclone"), "backup:Baseline backups", "v1.0.0")


def test_daily_backup_task_is_disabled_and_uses_utc(tmp_path: Path) -> None:
    from xml.etree import ElementTree as ET

    from hoop.platform.windows_tasks import NAMESPACE, definition

    tree = ET.fromstring(definition(tmp_path, "S-1-5-21-111", backup=True))
    ns = {"t": NAMESPACE}
    assert tree.find("t:Settings/t:Enabled", ns).text == "false"
    assert tree.find("t:Triggers/t:CalendarTrigger/t:ScheduleByDay/t:DaysInterval", ns).text == "1"
    boundary = tree.find("t:Triggers/t:CalendarTrigger/t:StartBoundary", ns).text
    assert boundary.endswith("08:17:00+00:00")
    assert "hoop.platform.backup run" in tree.find("t:Actions/t:Exec/t:Arguments", ns).text


def test_shared_objects_are_deduplicated_across_sets_and_wrong_hash_fails(tmp_path: Path) -> None:
    stage, sync, manifest = fixture_set(tmp_path)
    finalize(stage, sync, manifest)
    original = {p.relative_to(sync) for p in (sync / "objects").rglob("*") if p.is_file()}
    other = {**manifest, "backup_id": str(uuid4())}
    finalize(stage, sync, other)
    assert {p.relative_to(sync) for p in (sync / "objects").rglob("*") if p.is_file()} == original
    assert len(original) == 1
    with pytest.raises(BackupError, match="manifest_hash"):
        verify_set(sync, manifest["backup_id"], "0" * 64)


def test_disabled_backup_cli_needs_no_secrets_or_database(tmp_path: Path, monkeypatch: Any) -> None:
    import sys

    from hoop.platform.backup.__main__ import main

    monkeypatch.delenv("BASELINE_BACKUP_ENABLE", raising=False)
    monkeypatch.setattr(sys, "argv", ["backup", "run", "--output", str(tmp_path)])
    assert main() == 0
    assert not list(tmp_path.iterdir())


def test_database_secret_stays_out_of_subprocess_arguments(monkeypatch: Any) -> None:
    import subprocess

    from hoop.platform.backup.database import Tools

    captured = []

    def fake(command: Any, **kwargs: Any) -> Any:
        captured.append((command, kwargs["env"]))
        return subprocess.CompletedProcess(command, 0, b"pg_dump (PostgreSQL) 17.11\n", b"")

    monkeypatch.setattr(subprocess, "run", fake)
    Tools().run(
        "pg_dump",
        ["--version"],
        "host=localhost dbname=baseline_test_fixture user=postgres password=private-fixture-only",
    )
    command, env = captured[0]
    assert "private-fixture-only" not in " ".join(command)
    assert env["PGPASSWORD"] == "private-fixture-only"
    assert "BASELINE_SUPABASE_ADMIN_KEY" not in env


def test_interrupted_finalization_does_not_publish_completion(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import hoop.platform.backup as backup

    stage, sync, manifest = fixture_set(tmp_path)

    def failed(*args: Any, **kwargs: Any) -> None:
        raise OSError("fixture interruption")

    monkeypatch.setattr(backup.LocalArtifacts, "put", failed)
    with pytest.raises(OSError):
        finalize(stage, sync, manifest)
    assert not (sync / "sets" / manifest["backup_id"] / "COMPLETE").exists()


def test_historical_inventory_cannot_include_known_credential_files(tmp_path: Path) -> None:
    from hoop.platform.backup.database import retain_inputs

    credential = tmp_path / ".env"
    credential.write_bytes(b"synthetic-private-fixture-only")
    with pytest.raises(BackupError, match="credential_file_refused"):
        retain_inputs(
            {"artifact_inventory": [], "files": []},
            tmp_path / "stage",
            None,
            [{"label": "history", "source": str(credential)}],
        )


@pytest.mark.parametrize(
    "schemas", [["platform", "auth"], ["platform", "storage"], ["platform", "pg_catalog"]]
)
def test_provider_schema_credentials_cannot_enter_application_dump(schemas: list[str]) -> None:
    from hoop.platform.backup.database import application_schemas

    with pytest.raises(BackupError, match="application_schemas"):
        application_schemas(schemas)
    assert application_schemas(["platform", "arena", "api"]) == ("platform", "arena", "api")


@pytest.mark.parametrize("explicit", [False, True])
def test_native_export_preserves_ca_and_keeps_setup_credentials_out(
    monkeypatch: Any, explicit: bool
) -> None:
    import subprocess

    from hoop.platform.backup.database import Tools

    monkeypatch.setenv("PGSSLROOTCERT", "public-environment-ca.crt")
    monkeypatch.setenv("BASELINE_SUPABASE_ADMIN_KEY", "synthetic-never-forwarded")
    monkeypatch.setenv("BASELINE_MIGRATION_DSN", "synthetic-never-forwarded")
    captured = []

    def fake(command: Any, **kwargs: Any) -> Any:
        captured.append((command, kwargs["env"]))
        return subprocess.CompletedProcess(command, 0, b"pg_dump (PostgreSQL) 17.11", b"")

    monkeypatch.setattr(subprocess, "run", fake)
    dsn = (
        "host=fixture.invalid user=fixture dbname=fixture "
        "sslmode=verify-full password=fixture-private"
    )
    if explicit:
        dsn += " sslrootcert=explicit-ca.crt"
    Tools().run("pg_dump", ["--version"], dsn)
    command, environment = captured[0]
    assert environment["PGSSLROOTCERT"] == (
        "explicit-ca.crt" if explicit else "public-environment-ca.crt"
    )
    assert environment["PGSSLMODE"] == "verify-full"
    assert environment["PGPASSWORD"] == "fixture-private"
    assert not any(key.startswith("BASELINE_") for key in environment)
    assert "fixture-private" not in " ".join(command)


def test_onedrive_keeps_windows_dns_environment_but_excludes_setup_secrets(
    monkeypatch: Any,
) -> None:
    import subprocess

    monkeypatch.setenv("SYSTEMROOT", "C:/Windows-fixture")
    monkeypatch.setenv("BASELINE_SUPABASE_ADMIN_KEY", "synthetic-not-forwarded")
    monkeypatch.setenv("PGPASSWORD", "synthetic-not-forwarded")
    captured = []

    def fake(command: Any, **kwargs: Any) -> Any:
        captured.append(kwargs["env"])
        return subprocess.CompletedProcess(
            command,
            0,
            b"rclone v1.75.2\n" if command[1] == "version" else b"fixture: onedrive\n",
            b"",
        )

    monkeypatch.setattr(subprocess, "run", fake)
    client = OneDrive(Path("rclone"), "fixture:BaselineBackups", "v1.75.2")
    assert client.env["SYSTEMROOT"] == "C:/Windows-fixture"
    assert "BASELINE_SUPABASE_ADMIN_KEY" not in client.env and "PGPASSWORD" not in client.env
    assert len(captured) == 2 and all(env == client.env for env in captured)
