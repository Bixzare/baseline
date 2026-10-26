# Compact history import

DB-003 adds eight event/history tables, cutoff-aware revision reads and a staged
seed importer. Planning is local and writes no database rows or cloud objects.
Real import remains blocked by seed acceptance and hosted gates. No NBA request,
roster reconstruction, baseline forecast or official publication runs here.

## Plan before applying

```powershell
uv run --locked python -m hoop.domains.nba.history plan --archive artifacts/seed-2025-26 --source-manifest artifacts/source-bulk/266d94cf4e094533ad650e53bcacab8a/manifest.json --downloads artifacts/dataset-comparison/8be6ca7339144953bdd1e7422e423c22/eoinamoore-downloads.json --report artifacts/seed-import-plan.json
```

The retained October 26 real-data plan selects 5,447 player appearances and
1,698 supporting team rows for 849 games, with 76 short player histories.
Selecting each player's latest ten appearances can retain many older games;
supporting closure intentionally includes both team sides. Counts do not imply
complete player coverage. Four blockers are reported:

- Missing explicit seed acceptance tied to the immutable seed manifest/parser.
- 135 unresolved quarantined source rows.
- Unverified source calendar convention. Dates remain dates, not midnight UTC.
- Required original raw files total 438,321,084 bytes. The player file and team
  file exceed the client's verified 16 MiB per-object limit.

The limit is the current client bound, not a measured Supabase allowance. No raw
body is silently truncated or substituted with an invented smaller response.
A separately reviewed archival design or supported upload path is required before
real import; SQL/fixture success cannot waive this gate. No source repair requests
are added to this issue.

The planner verifies every artifact hash and original provenance, selects at most
ten regular-season appearances per player plus each team's latest ten games,
then closes over supporting games/team sides. It preserves missing target fields
and reports ambiguous date ordering. IDs are not used as game chronology.
Original per-file request start/receipt times come from saved download reports;
absence is a blocker. Collection time is never substituted for an unknown request
time. All normalized code/config/manifest identities remain inspectable.

## Controlled apply and recovery

The same command supports `apply`, adding `--acceptance PATH` and
`--confirm-hosted-gates`. Actual application uses the restricted runtime DSN and
backend artifact credentials. Review migrations and all source/storage gates
before enabling it. A flag is operator confirmation, not proof of hosted health.

An acceptance file must match the seed manifest SHA-256 and parser version, with
`kind: owner_review` and `calendar_convention: source_calendar_verified`. Do not
create one until the owner has accepted the actual evidence. Any quarantine still
blocks apply. Tests use `kind: synthetic_fixture`, which cannot authorize a
production import. The default notebook only plans with invented fixture inputs.

Apply verifies raw/normalized inputs, stores original raw bodies, selected Parquet
and a portable cloud-reference manifest before short per-game transactions.
Events use stable NBA source/occurrence identities. Revised input/parser versions
append new checks, observations and facts. Exact retries compare existing rows,
never update them. Checkpoints advance only after a committed game chunk. If a
chunk fails it rolls back; if checkpoint persistence fails after commit, retry
verifies the existing identities and resumes safely. Each attempt appends run
events with measured duration and counts; database failure cannot masquerade as
durable recording. Raw/object failures occur outside database transactions.

`player_history` reads facts and event status from one repeatable-read snapshot,
filters source receipt/validation/publication and observation time before choosing
latest revisions, and flags conflicting equivalent-time revisions. Historical
assumptions do not qualify as observed inputs. A later correction cannot erase a
previously eligible version at an earlier cutoff. Imported historical observations
retain their real later capture times and do not prove pregame availability.

Runtime cannot mutate evidence, change identities or apply DDL. Only explicit
team/player display-label updates are granted. `save_roster` stores a verified
current roster artifact after validating its accepted source capability; it never
derives membership from historical box scores. The probe bridge now records its
capability with a versioned v2 observation identity, preserving earlier records.

## Verification boundary

Real Postgres fixtures exercise import/readback, runtime denials, source/team
guards, unknown labels/times, cross-domain events, late corrections, interrupted
chunks and verified artifact resolution. The source notebook runs from a fresh
kernel with network and database calls blocked. Its fixture acceptance is not an
owner acceptance record. Hosted import, cloud reference resolution, measured
season capacity and independent backup/recovery remain unverified.

DB-003's initial checks and the final missing-status regression passed, followed
by 326 tests on the complete three-issue stack. Ruff lint/format, mypy, platform
boundaries, build and fresh-kernel checks passed. Hosted CI is separate evidence.

An additional offline October 26 comparison found all 1,230 source game dates
equal to `GAME_DATE` in the separately saved NBA inventory, with zero mismatches.
`.cache/calendar-comparison.json` retains the local summary. This supports the
date-only mapping review; it does not establish UTC tip-off times, DST semantics
or an owner acceptance record. Those flags were not automatically changed.
