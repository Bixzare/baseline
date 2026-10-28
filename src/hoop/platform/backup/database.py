"""Shared-snapshot logical export and guarded isolated restore."""

import hashlib
import os
import re
import shutil
import subprocess
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from hoop.platform.backup import BackupError, contained, exclusive, verify_set
from hoop.platform.database import inspect, migrations
from hoop.platform.local_artifacts import LocalArtifacts


def application_schemas(names: list[str]) -> tuple[str, ...]:
    if (
        "platform" not in names
        or len(names) != len(set(names))
        or any(
            not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name)
            or name in {"auth", "storage", "information_schema"}
            or name.startswith(("pg_", "supabase_"))
            for name in names
        )
    ):
        raise BackupError("only_explicit_application_schemas_may_be_backed_up")
    return tuple(names)


def one(conn: psycopg.Connection[Any], query: str) -> tuple[Any, ...]:
    row = conn.execute(query).fetchone()
    assert row is not None
    return tuple(row)


ENV_FIELDS = {
    "host": "PGHOST",
    "port": "PGPORT",
    "dbname": "PGDATABASE",
    "user": "PGUSER",
    "password": "PGPASSWORD",
    "sslmode": "PGSSLMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "sslcert": "PGSSLCERT",
    "sslkey": "PGSSLKEY",
    "connect_timeout": "PGCONNECT_TIMEOUT",
}


@dataclass(frozen=True)
class Tools:
    directory: Path | None = None
    rehearsal_container: str | None = None

    def run(
        self,
        name: str,
        args: list[str],
        dsn: str,
        *,
        outgoing: Path | None = None,
        incoming: Path | None = None,
    ) -> bytes:
        options = {k: str(v) for k, v in conninfo_to_dict(dsn).items() if v is not None}
        env = {
            key: os.environ[key]
            for key in [
                "PATH",
                "SystemRoot",
                "TEMP",
                "TMP",
                "USERPROFILE",
                "APPDATA",
                "LOCALAPPDATA",
                "HOME",
                "DOCKER_CONFIG",
                "DOCKER_HOST",
                "DOCKER_CONTEXT",
            ]
            if key in os.environ
        }
        env.update({value: options[key] for key, value in ENV_FIELDS.items() if key in options})
        env["PGCONNECT_TIMEOUT"] = "5"
        env["PGOPTIONS"] = "-c timezone=UTC -c statement_timeout=120000"
        command = [str(self.directory / name) if self.directory else name, *args]
        if self.rehearsal_container:
            if options.get("host") not in {
                "localhost",
                "127.0.0.1",
                "::1",
                "postgres",
            } or not options.get("dbname", "").startswith(("baseline_test_", "baseline_restore_")):
                raise BackupError("container_tools_are_disposable_rehearsal_only")
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", self.rehearsal_container):
                raise BackupError("invalid_fixture_container")
            env.update(PGHOST="127.0.0.1", PGPORT="5432", PGSSLMODE="disable")
            command = (
                ["docker", "exec", "-i"]
                + [part for key in env if key.startswith("PG") for part in ["-e", key]]
                + [self.rehearsal_container, name, *args]
            )
        try:
            with ExitStack() as handles:
                stdout = handles.enter_context(outgoing.open("xb")) if outgoing else subprocess.PIPE
                stdin = (
                    handles.enter_context(incoming.open("rb")) if incoming else subprocess.DEVNULL
                )
                result = subprocess.run(
                    command,
                    env=env,
                    stdin=stdin,
                    stdout=stdout,
                    stderr=subprocess.PIPE,
                    timeout=180,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode:
                    raise BackupError("postgres_tool_failed")
                return result.stdout or b""
        except (OSError, subprocess.TimeoutExpired):
            raise BackupError("postgres_tool_unavailable_or_timed_out") from None

    def verify(self, dsn: str, version: int) -> str:
        versions = []
        for name in ["pg_dump", "pg_restore"]:
            value = self.run(name, ["--version"], dsn).decode().strip()
            match = re.search(r"PostgreSQL\) (\d+)\.", value)
            if not match or int(match[1]) != version:
                raise BackupError("postgres_tool_major_mismatch")
            versions.append(value)
        return "; ".join(versions)


def inventory(conn: psycopg.Connection[Any], schemas: tuple[str, ...]) -> dict[str, Any]:
    tables = conn.execute(
        "SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname=ANY(%s) AND c.relkind='r' ORDER BY n.nspname,c.relname",
        (list(schemas),),
    ).fetchall()
    result = {}
    for schema, table in tables:
        digestor, count = hashlib.sha256(), 0
        query = sql.SQL(
            'SELECT to_jsonb(t)::text FROM {}.{} t ORDER BY to_jsonb(t)::text COLLATE "C"'
        ).format(sql.Identifier(schema), sql.Identifier(table))
        with conn.cursor(name="backup_inventory_" + uuid4().hex) as cursor:
            cursor.execute(query)
            for row in cursor:
                digestor.update(row[0].encode("utf-8") + b"\n")
                count += 1
        result[schema + "." + table] = {"count": count, "sha256": digestor.hexdigest()}
    return result


def export(
    conn: psycopg.Connection[Any],
    dsn: str,
    tools: Tools,
    stage: Path,
    *,
    source_project: str,
    migration_dir: Path,
    code_hash: str,
    lock_hash: str,
    archive_files: list[dict[str, Any]],
    schemas: list[str],
    after_snapshot: Any = None,
) -> dict[str, Any]:
    schema_names = application_schemas(schemas)
    if not conn.autocommit or stage.exists():
        raise BackupError("export_requires_idle_connection_and_new_stage")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", source_project):
        raise BackupError("invalid_source_project_identity")
    if inspect(conn, migrations(migration_dir)):
        raise BackupError("all_reviewed_migrations_required_before_backup")
    server = one(conn, "SELECT current_setting('server_version_num')::int")[0]
    version = tools.verify(dsn, server // 10000)
    acquired = one(conn, "SELECT pg_try_advisory_lock(617420260017)")[0]
    if not acquired:
        raise BackupError("backup_overlap")
    stage.mkdir(parents=True)
    try:
        cutoff = one(conn, "SELECT clock_timestamp()")[0]
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            conn.execute("SET LOCAL TIME ZONE 'UTC'")
            snapshot = one(conn, "SELECT pg_export_snapshot()")[0]
            state = inventory(conn, schema_names)
            with conn.cursor(row_factory=dict_row) as cursor:
                artifacts = cursor.execute(
                    "SELECT * FROM platform.artifacts ORDER BY artifact_id"
                ).fetchall()
                history = cursor.execute(
                    "SELECT migration_id,filename,sha256 FROM platform.schema_migrations "
                    "ORDER BY migration_id"
                ).fetchall()
                policies = cursor.execute(
                    "SELECT schemaname,tablename,policyname,roles,cmd,qual,with_check "
                    "FROM pg_policies WHERE schemaname='storage' AND policyname LIKE 'baseline_%%' "
                    "ORDER BY policyname"
                ).fetchall()
            provider_history = []
            if one(conn, "SELECT to_regclass('supabase_migrations.schema_migrations')")[0]:
                with conn.cursor(row_factory=dict_row) as cursor:
                    provider_history = cursor.execute(
                        "SELECT version,name FROM supabase_migrations.schema_migrations "
                        "ORDER BY version"
                    ).fetchall()
            with conn.cursor(row_factory=dict_row) as cursor:
                role_metadata = cursor.execute(
                    "SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,"
                    "rolreplication,rolbypassrls FROM pg_roles "
                    "WHERE rolname IN('baseline_owner','baseline_runtime','baseline_publisher') "
                    "ORDER BY rolname"
                ).fetchall()
            source_bytes = one(conn, "SELECT pg_database_size(current_database())")[0]
            projected_bytes = (
                source_bytes
                + sum(a["byte_count"] for a in artifacts)
                + sum(a["byte_count"] for a in archive_files)
            )
            if shutil.disk_usage(stage).free < projected_bytes + 16 * 1024 * 1024:
                raise BackupError("insufficient_staging_disk_capacity")
            if after_snapshot:
                after_snapshot()
            tools.run(
                "pg_dump",
                [
                    "--format=custom",
                    "--no-password",
                    "--snapshot=" + snapshot,
                    *["--schema=" + s for s in schema_names],
                ],
                dsn,
                outgoing=stage / "database.dump",
            )
        store = LocalArtifacts(stage)
        files = [
            {
                "label": "database",
                **store.put(stage / "database.dump", kind="database", format="pg_custom"),
            }
        ]
        manifest = {
            "schema_version": 1,
            "schemas": list(schema_names),
            "backup_id": str(uuid4()),
            "source_project": source_project,
            "represented_cutoff": cutoff.isoformat(),
            "snapshot_inventory": state,
            "migration_history": list(history),
            "provider_migration_history": list(provider_history),
            "application_role_metadata": list(role_metadata),
            "source_server_major": server // 10000,
            "capacity": {
                "source_database_bytes": source_bytes,
                "conservative_set_bytes": projected_bytes,
                "provider_free_bytes": None,
            },
            "tool_version": version,
            "code_hash": code_hash,
            "lock_hash": lock_hash,
            "artifact_inventory": list(artifacts),
            "provider_policies": list(policies),
            "archive_count": len(archive_files),
            "archive_inventory": [
                {k: item[k] for k in ["label", "sha256", "byte_count"]} for item in archive_files
            ],
            "files": files,
            "provider_setup": (
                "Auth identities and private buckets need separate setup; "
                "passwords and tokens are excluded"
            ),
            "automation_enabled": False,
        }
        # Downloading starts only after the snapshot transaction and pg_dump finish.
        return manifest
    except Exception:
        # A partial stage has no complete manifest and cannot count as a backup.
        raise
    finally:
        conn.execute("SELECT pg_advisory_unlock(617420260017)")


def retain_inputs(
    manifest: dict[str, Any],
    stage: Path,
    store: Any,
    archive_files: list[dict[str, Any]],
    *,
    max_seconds: float = 1800,
) -> None:
    deadline = time.monotonic() + max_seconds
    local = LocalArtifacts(stage)
    for artifact in manifest["artifact_inventory"]:
        if time.monotonic() >= deadline:
            raise BackupError("artifact_backup_budget_exhausted")
        body = store.read(artifact)
        temporary = stage / ("input-" + uuid4().hex)
        exclusive(temporary, body)
        descriptor = local.put(temporary, kind="artifact", format="bin")
        if (
            descriptor["sha256"] != artifact["sha256"]
            or descriptor["byte_count"] != artifact["byte_count"]
        ):
            raise BackupError("required_artifact_mismatch")
        manifest["files"].append(
            {"label": "artifact:" + str(artifact["artifact_id"]), **descriptor}
        )
        temporary.unlink()
    for item in archive_files:
        if time.monotonic() >= deadline:
            raise BackupError("archive_backup_budget_exhausted")
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,240}", item["label"]) or ".." in item["label"]:
            raise BackupError("unsafe_archive_label")
        path = Path(item["source"])
        if (
            path.name.startswith(".env")
            or path.name == "rclone.conf"
            or path.suffix in {".key", ".pem"}
        ):
            raise BackupError("credential_file_refused_in_historical_archive")
        if path.is_symlink():
            raise BackupError("archive_symlink_refused")
        descriptor = local.put(path, kind="archive", format="bin")
        if descriptor["sha256"] != item["sha256"] or descriptor["byte_count"] != item["byte_count"]:
            raise BackupError("historical_archive_mismatch")
        manifest["files"].append({"label": "archive:" + item["label"], **descriptor})


def restore(
    conn: psycopg.Connection[Any],
    dsn: str,
    tools: Tools,
    root: Path,
    backup_id: str,
    expected_hash: str,
    *,
    expected_project: str,
) -> dict[str, Any]:
    manifest = verify_set(root, backup_id, expected_hash)
    if manifest["source_project"] != expected_project:
        raise BackupError("restore_source_project_mismatch")
    schemas = application_schemas(manifest["schemas"])
    options = {k: str(v) for k, v in conninfo_to_dict(dsn).items() if v is not None}
    if options.get("host") not in {"localhost", "127.0.0.1", "::1", "postgres"} or not options.get(
        "dbname", ""
    ).startswith(("baseline_restore_", "baseline_test_")):
        raise BackupError("restore_requires_explicit_disposable_local_target")
    if conn.info.dbname != options["dbname"] or conn.info.dbname == expected_project:
        raise BackupError("restore_target_identity_mismatch")
    occupied = conn.execute(
        "SELECT EXISTS(SELECT FROM pg_namespace WHERE nspname=ANY(%s))", (list(schemas),)
    ).fetchone()
    if occupied is None or occupied[0]:
        raise BackupError("restore_target_has_application_schemas")
    actual_major = one(conn, "SELECT current_setting('server_version_num')::int")[0] // 10000
    if actual_major != manifest["source_server_major"]:
        raise BackupError("restore_server_major_mismatch")
    tools.verify(dsn, manifest["source_server_major"])
    for name in ["baseline_owner", "baseline_runtime", "baseline_publisher"]:
        role = conn.execute(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
            "FROM pg_roles WHERE rolname=%s",
            (name,),
        ).fetchone()
        if role is None or any(role):
            raise BackupError("restore_requires_reviewed_application_roles")
    database = next(f for f in manifest["files"] if f["label"] == "database")
    tools.run(
        "pg_restore",
        [
            "--exit-on-error",
            "--single-transaction",
            "--no-password",
            "--dbname=" + options["dbname"],
        ],
        dsn,
        incoming=contained(root, database["path"]),
    )
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        conn.execute("SET LOCAL TIME ZONE 'UTC'")
        if inventory(conn, schemas) != manifest["snapshot_inventory"]:
            raise BackupError("restored_rows_differ_from_snapshot")
    return {
        "backup_id": backup_id,
        "represented_cutoff": manifest["represented_cutoff"],
        "tables_verified": len(manifest["snapshot_inventory"]),
        "original_rows_preserved": True,
        "automation_enabled": False,
        "provider_apis_verified": False,
    }
