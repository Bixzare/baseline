# DB-001: Establish migrations, roles, and Supabase connectivity

Status: LOCKED by the project owner on October 13, 2026.

Prepared: October 13, 2026

Phase: 0. Priority: launch blocker. Dependency: BOOT-001 implemented and owner-reviewed. SOURCE-001 and DATA-001 do not need to finish for migration tooling and isolated tests to proceed; actual seed import is a later issue.

Session estimate: about 2.5 hours plus owner review, assuming the Supabase account has a free project slot and credentials can be configured. Account, network, or managed-role restrictions are explicit setup gates. Do not spend the session debugging an unavailable paid feature or installing a new VM environment.

## Goal and context

Give Baseline a reproducible application database foundation: ordered SQL migrations, restricted runtime credentials, private platform/NBA schemas, and tested cloud/local connectivity. The owner confirmed a new dedicated Supabase Free project named baseline, subject to account allowance. No existing project may be reused or replaced silently.

Launch player baselines and the immutable ledger must be operational before October 20, 2026 at 19:00 UTC, targeting publication at 17:00 UTC. This issue establishes infrastructure only. Source/history tables, private object storage, seed import, forecast tables/functions, and backup automation are later tasks.

Required guidance: AGENTS.md and `.agents/skills/hoop-postgres/SKILL.md`; use `.agents/skills/hoop-python-testing/SKILL.md` for integration checks. Locked references: [storage and access decision](../decisions/0003-store-operational-records-and-versioned-artifacts.md) and [design migration strategy](../design.md#15-migrations-ci-and-test-strategy). The contracts below are sufficient to implement this issue without prior chat.

## Infrastructure and access contract

- Use the owner's new dedicated Free project. Verify account ownership, available allowance, actual plan, region, Postgres major version, current database/object/connection limits, and project identity during setup. Record nonsecret settings and the reason for the selected region. No paid plan, IPv4 add-on, or automatic upgrade is authorized. If no free slot is available, report the blocker rather than deleting another project.
- Use Python 3.12 and psycopg with explicit SQL; no ORM. Pin a driver installation that works on Windows and Linux, with a small bounded connection count and mandatory TLS for hosted connections.
- Prefer a direct connection when supported. Test the shared session pooler as the IPv4 fallback for required operations; do not silently substitute transaction pooling. Obtain host and username from the actual project's supported connection settings rather than guessing them. [Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres).
- Separate privileged migration/deployment access from restricted runtime access and anonymous public access. Ordinary collection jobs must never receive migration credentials. All credential values come from environment variables or configured environment secrets, never committed SQL/configuration, printed DSNs, or notebook output.
- Create private application schemas `platform` and `nba`, plus an initially empty `api` schema reserved for sanitized public read tables. Do not expose private schemas through the Data API or grant public reads in anticipation of later features.
- Runtime identities cannot create or alter application objects, apply migrations, change grants, own application tables, or assume the migration role. Anonymous access cannot read private application tables or mutate records. Configure safe default application privileges so later objects do not acquire unintended PUBLIC/anonymous grants.
- Keep provider-managed schemas and roles intact. Map the anonymous test identity to Supabase's actual anonymous role for hosted verification. The later ledger issue introduces its narrow nonlogin function owner and publication execute grants; do not implement forecast permissions or functions here.

## Migration contract

Ordered SQL files live in `migrations/` with stable IDs. Store applied IDs, exact file checksums, and database-recorded application times in a privileged migration-history table. Implement a small shared migration command with inspect/pending and apply operations; record actual commands after they work.

The privileged bootstrap path creates the history table and required schemas/roles from repository-controlled SQL. Handle the initially absent history table under the same migration lock rather than requiring a manual SQL-console step. Runtime credentials cannot invoke this bootstrap path. Credential provisioning must use a controlled environment-based operation without putting password values into migration files or logs.

Acquire one database migration lock on the connection used to apply files, with bounded lock wait. Apply unapplied files in order and execute each supported file transactionally, recording its history row in that same transaction. A failed migration must not appear applied. Stop on failure before later files. Never edit an applied file, mark a failed file successful, or accept a changed checksum as an ordinary rerun.

Repeat application skips matching completed files without changing their timestamps. Reject changed applied checksums, duplicate IDs, invalid order/history, and missing applied files with actionable errors. New changes require a new file. This issue's committed migration creates foundation schemas, application roles/grants, and history only; test migrations for upgrade/failure scenarios stay in isolated fixtures.

## Scope and execution sequence

1. Inspect the existing repo and account setup. Configure the dedicated Free project only when this issue is assigned for execution. Record its nonsecret identity/limits and verify credentials are supplied securely; do not ask for passwords in issue comments or chat.
2. Add the driver, migration command, ordered bootstrap SQL, and role/environment documentation. Keep database policy in shared platform code with no NBA imports or basketball-specific migration-runner behavior.
3. Add a disposable Postgres service to Linux PR CI matching the verified project major version. Run migrations and role tests against that service with isolated fixtures, without production credentials or hosted Supabase dependence. Keep Windows driver/import/path checks. Document any existing local rehearsal option; installing Docker/WSL or a VM is outside this issue.
4. Test empty creation, repeat application, ordered upgrade, checksum failure, interruption, lock contention, and actual restricted/anonymous permissions before applying the reviewed migration to the chosen project through the same command. Hosted application is an explicit reviewed setup operation, not an automatic PR-CI step.
5. Verify the intended role and TLS session from the owner's Windows machine and a manually invoked GitHub Actions connection check. Hosted checks need only the restricted runtime credential; keep privileged credentials out of the workflow. Record which direct/session paths actually work.
6. Verify logical export access over the selected privileged connection path and document the supported restore route. Use only an isolated test target for a small foundation export/restore smoke check when available. Full off-device backup delivery and recovery remain a later mandatory launch gate; report them as unverified here.
7. Update README and AGENTS.md with actual migration/check commands, role mapping, connection prerequisites, CI evidence, and unverified infrastructure. Retain the report of initial allowance usage; the later seed-import task measures data growth.

## Acceptance criteria

- [ ] The dedicated owner-owned project is on the verified Free plan, with nonsecret identity, region, Postgres version, included allowances, and chosen connection modes documented. No unrelated resource or paid option is changed.
- [ ] A fresh isolated database obtains the foundation exclusively through committed migration tooling. Repeated application is a no-op for matching files and preserves application times.
- [ ] Applied-file changes, invalid history, interrupted files, and concurrent runners cannot yield a false successful migration. History and schema changes commit together where supported.
- [ ] Actual runtime and anonymous roles cannot migrate, create/alter private application objects, change grants, read private fixture records anonymously, or assume privileged application roles. Default privileges remain restricted for newly created fixture tables/functions.
- [ ] Windows and actual GitHub Actions runtime connections use the intended restricted identity with TLS. The report distinguishes verified direct/session paths from unavailable or untested alternatives.
- [ ] PR CI runs real Postgres integration tests on disposable data and passes lint/type/tests plus Windows compatibility checks. Missing database setup must fail required checks rather than silently skip them.
- [ ] Credentials and DSNs with passwords are absent from logs, tracked files, fixtures, and browser configuration. Application permissions and schemas are reproducible; provider internals remain intact.
- [ ] The privileged export/restore route is documented with its actual verification status. Full backup recovery is not claimed complete. README and AGENTS.md commands are current and the guide remains under 200 lines.

## Required tests

- Migrate from empty state, rerun unchanged files, and upgrade through ordered fixture migrations. Check schema/history state and unchanged timestamps, not just process exit codes.
- Inject invalid SQL after an earlier statement in one migration. Verify that file's schema/history changes roll back and later files do not run; an earlier successfully committed migration remains recorded.
- Change an applied file, remove an applied file from the available history, supply duplicate/out-of-order IDs, and simulate interrupted application. Verify clear refusal without corrupting recorded history.
- Use two independent Postgres connections for migration-lock contention and bounded timeout. The second runner cannot apply duplicate bootstrap/history records or bypass the lock.
- Connect as real restricted roles and attempt application DDL, grant changes, migration invocation/history mutation, private reads by anonymous access, and privileged role switching. Verify rejection. Test safe defaults on newly created fixture objects under the actual migration owner.
- Exercise environment/configuration errors and connection failures with sanitized reporting. Verify hosted connection checks report current role, server version, and TLS status without printing credentials.
- This issue adds no forecast features or outcome calculations, so model leakage tests are not applicable. Database-access tests are required now; forecast cutoff/receipt and outcome integrity tests belong to their implementing issues.

## Failure decision and likely files

Local migration implementation can progress while account setup is blocked, but hosted readiness stays unverified until both required execution environments connect safely. A managed-role or pooler restriction needs a supported, reviewed correction; never supply admin credentials to the collector as a workaround. A paid resource or a different database/project choice requires an owner decision.

Likely files: `migrations/` for the foundation SQL; `src/hoop/platform/database/` and `src/hoop/cli.py`; dependency/lock files; nonsecret configuration and environment-variable examples; `tests/integration/`, `tests/unit/`, and migration fixtures; `.github/workflows/ci.yml` and a manual connection-check workflow; `docs/database-setup.md`, README.md, AGENTS.md, and Weaknesses.md for evidenced limitations. Source/history table migrations and data import are deliberately absent.

## Handoff

Return the PR, exact check commands/outcomes, project/connection verification report, migration history/checksums, real-role failure evidence, CI and manual runtime workflow links, usage measurements, and export/restore status. Explain the difference between a safe migration path and runtime access, why session pooling is verified rather than assumed, and one migration failure/recovery scenario. The next database issue adds source/history contracts, required private artifacts, and recent-seed import from DATA-001.

Approval: the owner explicitly said "lock" on October 13, 2026. This finalizes the specification; a separate assignment to the coding agent starts execution. No Supabase project, migration, hosted connection, or database-role test has been executed by this planning record.
