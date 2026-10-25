# DB-003: Store NBA history and import the launch seed

Status: LOCKED by the project owner on October 14, 2026.

Prepared: October 14, 2026

Phase: 0. Priority: launch blocker. Dependencies: DATA-001, DB-001, and DB-002 implemented and owner-reviewed. Required inputs are accepted 2025-26 regular-season Parquet/manifests, source mappings, verified artifact storage, and migration/runtime access. SOURCE-001 acceptance remains necessary for each used capability; locked specifications alone do not establish source or seed acceptance.

Session estimate: about 3 to 4 focused hours plus owner review and measured upload/import time. Limit this session to stored contracts, compact seed selection/import, and fixture checks. Broader history, baseline calculation, scheduling, and availability modeling remain separate work.


## October 25 execution context

The owner resumed sequential execution with the [historical-data amendment](../PRD-data-source-amendment.md).
Use accepted pinned seed/repair artifacts, preserve quarantine and unknowns,
and never infer historical pregame cohorts from outcomes. Injury ingestion is
deferred for the first release. The original October 20 target is past;
all timing/readiness gates now apply to the first approved future slate.
This task is backlog until its implemented/reviewed dependencies pass.
No runtime source acceptance, merge, deployment, or retrospective publication
is established by this amendment. Required tests and contracts below remain.


## Goal and context

Make verified recent history available to cloud/local jobs without requiring the owner's laptop archive. Preserve versioned facts, source timing, identities, and coverage so a later predictor can select prior appearances honestly. Add eight phase-specific tables and a repeatable seed import using existing platform evidence operations.

Launch predicts player minutes, points, rebounds, assists, and threes made using up to 10 prior regular-season appearances, crossing teams and seasons. The deadline is October 20, 2026 at 19:00 UTC, targeting publication at 17:00 UTC. Team forecasts follow launch; their full chronological Elo initialization is outside this compact import.

Required guidance: AGENTS.md and `.agents/skills/hoop-postgres/SKILL.md`, `hoop-data-quality`, `hoop-python-testing`, and `hoop-notebooks`. Locked references: [design events/facts](../design.md#6-logical-database-schemas), [ADR 0003](../decisions/0003-store-operational-records-and-versioned-artifacts.md), and [ADR 0006](../decisions/0006-start-with-baselines-and-model-minutes-first.md). Contracts below stand alone without chat history.

## Table and identity contract

Use ordered migrations after DB-002. Platform IDs are UUIDs, external NBA IDs are strings, references below are foreign keys, and observation times are timezone-aware UTC. Unknown values stay null. Version enums and validation policy in code/migrations; retain source/configuration provenance.

| Table | Columns and behavior |
| --- | --- |
| `platform.events` | event_id; domain, source_event_id, competition, season; occurrence_no; optional predecessor_event_id; created_at. Unique domain/source_event_id/occurrence_no, positive occurrence number, no self-predecessor. NBA source game ID is not the platform occurrence ID. |
| `platform.event_observations` | observation_id; event_id; source_check_id; observed_at; optional scheduled_start and actual_start; state; details. Immutable observations; preserve validated source game date and its interpretation in details when only a date is supplied. |
| `nba.teams` | team_id TEXT primary key; display_name; abbreviation. Mutable display labels, stable identity. |
| `nba.players` | player_id TEXT primary key; display_name. Names are labels, never join keys. |
| `nba.games` | event_id primary/foreign key; home_team_id, away_team_id; source_season_type. Team references must exist and differ. Never infer home/away from scores or row order. |
| `nba.roster_snapshots` | roster_id; team_id; season; source_check_id; validated_at; members_artifact_id. Membership is a verified versioned artifact of stable player IDs, not historical box-score membership. |
| `nba.player_game_versions` | fact_id; event_id; player_id; team_id; source_check_id; observed_at; evidence_tier; participation; optional minutes_seconds NUMERIC, points, rebounds, assists, threes_made INT, started BOOLEAN. Unique event/player/source revision, using source_check_id as the revision identity. |
| `nba.team_game_versions` | fact_id; event_id; team_id; source_check_id; observed_at; evidence_tier; points_for, points_against INT; optional extras_artifact_id. Unique event/team/source revision, using source_check_id as the revision identity. |

Evidence/event/fact/roster rows are immutable under runtime credentials; only team/player display columns may receive narrowly scoped updates. Prevent update/delete/truncate of evidence and retain DB-001's ownership/DDL/grant restrictions. Validate references, game-team membership, accepted source state, and consistent revision identity with tested SQL constraints or narrow database guards. Keep basketball checks out of the generic platform modules.

Use stable IDs recorded with input/checkpoint identity so an exact rerun preserves records. Reject conflicting reuse of the same ID/revision. A corrected body or parser/configuration produces distinct validated source/fact versions. Current-state queries select an explicit accepted revision with a deterministic tie rule; historical reads apply a cutoff before choosing the revision, rather than choosing latest first.

## Seed selection and evidence contract

- Read only owner-accepted DATA-001 manifests and verify checksums, schema/parser/configuration versions, source mapping, season, and coverage before selecting rows. No new live NBA requests or unreviewed sources in this task.
- Approved compact seed: up to the latest 10 supported regular-season appearances for every player represented in the accepted seed, plus each team's latest 10 completed regular-season games. Do not restrict players to an opening-night roster. Keep shorter or missing history visible for the later abstention policy. Do not replace a recent incomplete appearance with an older row merely to make a target complete.
- Include the supporting event/game identities and both team-result sides for every retained player/team game. Reconcile scores using the complete accepted team records, not a sum of the selected player subset. This supporting closure may retain more than 10 team records; document counts and bytes before upload.
- Order seed appearances using supported event timing or the source game date's verified convention. A date alone does not become midnight UTC. Ambiguous ordering or venue identity is a reported gap; do not assign invented times or interpret a game ID as chronology. Preserve date-only evidence so the later predictor can handle it explicitly.
- Participation and fields follow accepted source semantics. Confirmed DNP has explicit evidence and zero outcomes; absence of a row, an unknown status, or rounded zero minutes is not proof of DNP. Preserve valid overtime minutes, numeric precision, and nonnegative integer counting stats. Unknown start status stays null. No player-by-game cross product or reconstructed historical roster.
- Register required raw and selected normalized artifacts/manifests in private cloud storage using DB-002's verified client. Keep the complete normalized season archive local with its independent backup gate. Cloud consumers must be able to resolve required references without the laptop. If a retained row depends on a bulk raw response, retain that response rather than inventing a smaller original source body. Measure required bytes and supported upload limits first.
- Preserve original source collection/validation/publication metadata from verified manifests, plus a separate import run and actual database insertion evidence. Current collection of past games cannot prove those values were available at an old prediction cutoff. Version an evidence tier distinguishing archived historical observations/assumptions from live saved observations; do not relabel imported history as live pregame evidence.
- This compact seed does not establish full historical roster opportunities or initialize Elo across the full 2025-26 season. Later Elo work must replay the full accepted team history through its own recorded initialization step.

## Execution sequence

1. Inspect DATA-001's accepted manifest and DB-002's actual evidence interfaces. Implement a shared selection/validation plan that reports retained identities, supporting closure, unresolved gaps, required objects, and measured bytes before any upload or database write.
2. Add the eight tables and runtime grants through migrations. Provide small typed write/read operations: event observations, identity labels, roster snapshots, and versioned player/team facts. Define initial historical occurrence identity only; live postponement detection/publication handling belongs to the later collector/ledger issues. Preserve predecessor links where supplied and reject cross-event or cyclic predecessor chains.
3. Implement an explicit import command with a dry-run plan and a controlled apply mode. Register artifacts before short database transactions; reuse DB-002 evidence helpers. Chunk related rows with a transaction and checkpoint only committed chunks. Retain verified objects after a database failure and resume safely. No network calls inside database transactions.
4. Test the import against disposable Postgres fixtures and read back semantic rows/counts/source references. Then apply reviewed migrations and import the accepted compact seed through the same command using intended runtime credentials. Never paste schema or seed SQL into the hosted console.
5. Produce a seed report identifying actual player/team/game coverage, short histories, missing fields/identities, quarantine reasons, unknown expectations, evidence tiers, reference resolution, and storage growth. A partial import is not a complete seed. Owner review determines readiness; missing history remains visible for the predictor.
6. Extend `01_sources_and_backfill.ipynb` with a concise fixture-based seed selection/validation walkthrough using shared operations: purpose, inputs, plan, inspect, interpretation. Default execution remains read-only planning without live services or production writes. Show the separate controlled import command and its saved report; do not auto-apply it from the notebook.
7. Update README, AGENTS.md under 200 lines, setup/import documentation, and Weaknesses.md with exact commands, usage, and remaining gates. Full independent backup and recovery remain separate mandatory launch tasks.

## Acceptance criteria

- [ ] Fresh and upgraded Postgres schemas implement the eight tables via migrations, with correct IDs, keys/FKs, role permissions, revision behavior, and null semantics.
- [ ] Dry-run selection is deterministic and measured. Supporting games/team sides and raw references are complete or explicitly unresolved; selected rows are not silently dropped to improve coverage.
- [ ] Controlled import is restartable after partial failure. Exact reruns preserve IDs/counts/content; source/parser revisions append distinct evidence instead of overwriting.
- [ ] Current and cutoff-aware reads choose the correct accepted revision. Imported historical data remains distinguishable from live saved observations and unsupported historical availability assumptions.
- [ ] Accepted seed artifacts and operational references resolve from the actual cloud runner without laptop files. The report records measured rows/bytes/index growth and remaining coverage/backup limitations.
- [ ] Missing participation, names, starts, timestamps, and optional fields are not invented. Confirmed DNP, overtime, trades, string IDs, and date-only history retain their supported meanings.
- [ ] The notebook runs from a fresh kernel on fixtures, matches the CLI selection plan semantically, and cannot perform production import by default. Real database import is tested separately in integration CI.
- [ ] PR lint/type/tests, relevant validation/leakage checks, and role tests pass. The owner receives actual hosted import/readback evidence or a truthful failed/incomplete gate report.

## Required tests

- Migrate fresh/upgrade databases and exercise real runtime/anonymous roles. Verify stable IDs/FKs, invalid team membership, duplicate/conflicting revisions, invalid counters/minutes, unknown values, evidence mutation denial, and allowed display-label updates only.
- Test more/fewer/exactly 10 appearances, no history, trades, season/competition exclusions, missing recent fields, date-only records, ambiguous chronology, missing venue mapping, supporting team-side closure, and consistent versus conflicting scores. Do not infer DNP from a missing player row.
- Interrupt before/after artifact registration, within a database chunk, and before checkpoint persistence. Verify transaction rollback, safe resume, unchanged row counts/IDs, and rejection of corrupted manifests/files.
- Reimport the same normalized version, changed source bytes, and changed parser/configuration. Verify correct reuse versus new revision and preservation of original observations and insertion evidence.
- Leakage fixtures: future game, target-game final membership, post-cutoff roster snapshot, later correction with older game/publication time, and historical import collected today. Cutoff-aware observed reads must reject unavailable versions; replay assumptions must stay explicitly labeled.
- Test roster artifact identity/version/hash and source acceptance without generating historical memberships. Verify a synthetic non-NBA event uses the shared platform tables without NBA imports or required basketball fields.
- Execute the notebook with live transport and production writes blocked. Compare its selection plan with the CLI and reject stale cached input/configuration identity. Integration CI checks actual import/readback on disposable Postgres.

## Failure decision, likely files, and handoff

Invalid manifests or required reference failures block affected import; do not broaden source scope, invent facts, or discard problem rows silently. A storage/role/capacity problem needs a supported reviewed correction, not administrator credentials in the importer or a paid upgrade. Coverage gaps may cause later visible abstentions; they cannot be declared resolved because the command exits successfully.

Likely files: ordered `migrations/`; generic event/evidence modules under `src/hoop/platform/`; `src/hoop/domains/nba/history/`, identity/validation/read-write modules, and thin CLI operations; seed configuration; `tests/unit/`, `tests/integration/`, `tests/leakage/`, `tests/notebooks/`, and fixtures; `notebooks/01_sources_and_backfill.ipynb`; a manual seed-readback workflow if needed; `docs/seed-import.md`, database/artifact setup notes, README.md, AGENTS.md, and Weaknesses.md. Complete data, personal paths, credentials, and large reports remain outside Git.

Return the PR, exact check outcomes, migration history, source/seed manifest IDs and hashes, dry-run and hosted readback reports, actual cloud reference-resolution evidence, counts/gaps/usage, and resume/revision demonstrations. Explain appearance history versus roster opportunity, why imported past games do not prove past source availability, and one failed-chunk recovery scenario. No baseline prediction or full Phase 0 completion is implied by this issue alone.

Approval: the owner explicitly said "lock" on October 14, 2026. This finalizes the specification; a separate coding-agent assignment starts execution. No history migration, seed selection/import, notebook update, or cloud readback has been implemented by this planning record.
