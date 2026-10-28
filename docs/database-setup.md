# Database foundation and verification

DB-001 supplies repository migrations and separate privileged/runtime operations.
The dedicated Free project `baseline` is now created in eu-west-1 on Postgres
17.11. Reviewed migrations 0001 through 0008 are applied, including the owner's
approved managed Auth and publisher corrections. Exact hashes and role boundaries
were read back through MCP. Actual runtime login, Windows/Actions TLS, Auth/Storage
APIs and account allowance measurements remain gates. See the current
[hosted setup evidence](supabase-setup-status.md).

## Roles and boundaries

`baseline_owner` is a nonlogin application object owner. The privileged setup
connection must have supported role-creation rights; the bootstrap grants that
connection membership. `baseline_runtime` starts as a restricted nonlogin role.
Only the separate provisioning operation enables its login and sets a password
from the environment. It has schema usage but receives table privileges only
through specific later migrations. Runtime has no migration-history access.

Private schemas are `platform` and `nba`. Empty `api` is reserved, with no public
read grants. Keep private schemas out of Supabase's exposed-schema configuration.
Provider roles such as `anon` are not created or altered by application migrations.
Global default function EXECUTE and type USAGE for PUBLIC are revoked for the
application owner; table/sequence defaults are restricted too. Future migrations
must create application objects as this owner. Database administrators remain
outside the runtime protection boundary.

## Commands

Configure secrets privately in the terminal or its secret store. Never paste
DSNs into chat or commit them. From the project environment:

```powershell
uv run --locked python -m hoop.platform.database inspect
uv run --locked python -m hoop.platform.database apply
uv run --locked python -m hoop.platform.database provision-runtime
uv run --locked python -m hoop.platform.database check
```

The first three use `BASELINE_MIGRATION_DSN`; provisioning additionally requires
`BASELINE_RUNTIME_PASSWORD` (at least 20 characters, generate randomly).
Remove privileged variables from ordinary job environments afterward. Rotation
uses the same controlled provisioning operation, then updates runtime secrets.
Existing connections retain their sessions; coordinate rotation with running jobs.
The last command uses only `BASELINE_RUNTIME_DSN` and rejects any identity except
`baseline_runtime`. No migration credential enters the manual hosted workflow.

Hosted DSNs require `sslmode=verify-full` and a trusted CA configured using
supported libpq settings, such as the provider CA via `sslrootcert`. Use the actual
connection settings from the new project, not guessed host/user values. Set
`BASELINE_DB_CONNECTION_MODE` to `direct` or `session`; transaction pooling is
unsupported and the common transaction-pooler port 6543 is refused. A declared
mode is not proof of pooler behavior: verify the actual endpoint settings.
Only explicit loopback rehearsals may set `BASELINE_DB_LOCAL_TEST=1`; these report
their real TLS state and do not establish hosted security.

The health report's `tls` field describes the local libpq client connection.
`postgres_backend_tls` separately records `pg_stat_ssl` for the database backend.
With session pooling these describe different network legs. A successful
`verify-full` connection and client TLS do not establish pooler-to-Postgres TLS.
The hosted check rejects a plaintext client even if the backend reports TLS.

## Migration behavior

Files use contiguous IDs starting at `0001`, for example `0001_foundation.sql`.
SQL bytes use LF line endings for stable checksums across Windows/Linux. Each
file must contain transaction-compatible SQL, without explicit transaction
control or operations such as concurrent index creation. Files are trusted,
reviewed deployment inputs, not arbitrary user SQL.

The runner checks privileged access, takes a session advisory lock with a bounded
five-second wait, bootstraps under that lock, and commits each file together with
its history row. The row stores exact file hash and database `clock_timestamp()`.
Repeated matching files preserve timestamps. Changed, missing, duplicated or
noncontiguous IDs are refused. A failed file rolls back; earlier completed files
remain applied and later files do not run. Restore original files when history
differs and add a new migration for legitimate changes. Do not alter history by
hand. Session connections are required for the session lock.

## Local tests and measured evidence

The existing Docker installation ran the pinned official Postgres 17 image:
`sha256:b8faeff7712663c2773a190181e1246e37e364b887611c04658c28b44e2408fe`.
The actual server reports 17.11. Postgres 17 is a **provisional test major**, not
a claimed match to an uncreated hosted project. Verify and align after creation.
No Docker, WSL or VM installation is part of this task.

Set `BASELINE_TEST_DSN` privately to an isolated local admin test connection, then
run `uv run --locked pytest`. Integration fixtures reject remote hosts, create
random disposable databases and remove only those databases. Missing setup fails
required Postgres tests. Linux CI supplies the disposable service. The Windows
CI job explicitly runs `pytest -m "not postgres"`; it checks imports, paths,
configuration and notebooks while Linux covers real database behavior.

Verified locally: empty/repeat/upgrade migrations, exact timestamp preservation,
failed-file rollback, missing/changed/invalid history, two-connection lock
contention, real runtime login and denied DDL/grants/private reads/owner switching.
Anonymous role context cannot read private records. These tests use synthetic
fixture data and do not establish current NBA access or hosted readiness.

The actual CLI applied `0001`, repeated with no changes, provisioned a synthetic
runtime login and reported that role, server 17.11 and TLS false on loopback.
A `pg_dump -Fc` export restored successfully using `pg_restore --exit-on-error`
into a separate disposable database, retaining the history hash
`5572f7a8401dfc002e5c374cdd509e3b17e22bba7c94a86ed898744d655a31ab`.
The restore target was removed afterward. This is a foundation smoke check,
not an independent backup, off-device copy or production recovery rehearsal.

All 166 local tests passed, including the existing offline notebook. Ruff
lint/format, mypy and platform boundaries passed. Required Postgres tests were
executed, not skipped. Hosted CI and manual hosted checks are separate evidence.

## Hosted gates after owner review

- [ ] Create the dedicated owner-owned Free project; record identity, region,
  actual major version, limits and initial usage without secrets.
- [ ] Confirm supported direct access or IPv4 session-pooler fallback with TLS
  from Windows; record each tested and untested mode.
- [ ] Review migrations, apply through the same command, provision runtime.
- [ ] Configure only runtime credentials in protected `database-rehearsal`
  environment and dispatch `database-check.yml`; save its result.
- [ ] Confirm private schemas are not exposed and actual `anon` is denied.
- [ ] Verify hosted logical export and an isolated supported restore path.

Do not treat local fixture success as completion of these gates or DB-001's
hosted acceptance criteria. No paid feature, broad runtime grant or unrelated
project replacement is authorized.
