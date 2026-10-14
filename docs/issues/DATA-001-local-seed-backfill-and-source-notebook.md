# DATA-001: Build the local seed backfill and source walkthrough

Status: LOCKED by the project owner on October 13, 2026.

Prepared: October 13, 2026

Phase: 0. Priority: launch blocker. Dependencies: BOOT-001 implemented and owner-reviewed; SOURCE-001 implemented with owner-accepted local historical adapters, reviewed fixtures, request policy, and recorded source limitations. Source acceptance is an execution gate, not established by locking an issue specification.

Session estimate: about 3 hours of agent work plus owner review and the measured collection time. Source outages or unexpectedly large requests must be reported rather than extending collection indefinitely. Limit scope to the 2025-26 regular-season seed and the first compact notebook.

## Goal and context

Produce a resumable local historical archive for Baseline's opening-night player baselines. Preserve raw inputs, validate player/team game records, write versioned Parquet artifacts, and report completeness and limitations. Deliver `notebooks/01_sources_and_backfill.ipynb` as the owner's executable route through the same tested operations.

Launch predicts minutes, points, rebounds, assists, and threes made using up to 10 prior regular-season appearances. The window can cross teams and seasons. The seed starts with 2025-26; three-season model history and era analysis are later work. The deadline remains October 20, 2026 at 19:00 UTC, with opening publication targeted at 17:00 UTC.

Required guidance: AGENTS.md; `.agents/skills/hoop-data-quality/SKILL.md` and `.agents/skills/hoop-notebooks/SKILL.md`. Use `.agents/skills/hoop-python-testing/SKILL.md` for failure and leakage fixtures. Locked references: [source access](../decisions/0001-verify-nba-sources-by-environment.md), [storage](../decisions/0003-store-operational-records-and-versioned-artifacts.md), and [shared notebook operations](../decisions/0009-share-tested-operations-with-learning-notebooks.md).

## Input and output contract

- Inputs: the accepted local source configuration and parser mapping from SOURCE-001, explicit season `2025-26`, verified regular-season classification, source/request budgets, and a configurable local archive root outside tracked files. Keep personal paths and secrets out of committed configuration.
- Use local nba_api historical requests only. Prefer the accepted player/team game-log interfaces. Request detailed box scores only for an identified required-field gap, with the request count explained; do not fetch every game's detail automatically.
- Retain raw bodies and fetch manifests with run/source identity, credential-free request parameters, collection/validation times, supplied publication times, content checksum, parser/schema/configuration/dependency/code versions, and failure evidence. Missing source times stay missing.
- Player records preserve string game/player/team IDs, season/competition, source game date, actual start time only if supported, participation evidence, numeric minutes in seconds with original precision documented, points, rebounds, assists, and threes made. Preserve optional start-status evidence without inventing it. Values that are unknown stay null or explicitly invalid, not zero.
- Team records preserve string game/team/opponent IDs, season/competition, source date, supported venue identity, points for and against including overtime, and provenance. Reconcile both team sides for each supported completed game. If an accepted source lacks a field, report the limitation and resolve the mapping before treating it as validated.
- A source date without a tip-off time is not a UTC timestamp. Do not manufacture midnight starts. Historical availability assumptions and revision uncertainty are separate evidence, not live observation claims.
- Outputs: immutable raw artifacts, validated player/team Parquet versions, manifests with IDs/checksums/row counts/schema and source references, checkpoint state, validation/quarantine reports, and a season coverage summary. A current convenience pointer may select a completed version; it cannot overwrite accepted artifacts.
- This task writes no operational database rows. A later database task imports the validated seed subset needed for recent baselines; the full season remains in the independently backed-up local archive. Backup setup and verification are separate tasks, so report backup state honestly here.

## Scope and execution sequence

1. Implement local collection, normalization, validation, persistence, and resume as reusable package operations with a thin CLI entry point. Reuse SOURCE-001's transport, raw-evidence, and request-policy helpers instead of duplicating them in the notebook.
2. Use sequential requests, a configurable minimum three-second gap, a 30-second timeout, and at most two retries for temporary failures. Honor a longer Retry-After within the declared budget, otherwise stop with an explicit reason. Access denial or bot challenges stop the source run; never bypass protection or run historical collection in GitHub Actions.
3. Checkpoint completed requests/chunks using input and configuration identity plus verified artifact references. Mark a unit complete only after validation and durable file/manifest finalization. Recover from interrupted writes without treating temporary or partial files as accepted data.
4. Repeated collection of unchanged content reuses validated normalized versions when raw/parser/configuration identities match. Retain each fetch observation. Changed source content or parser/configuration creates a distinct version; preserve the older evidence and do not silently replace it.
5. Validate a small fixture/sample path before an explicit full-seed run. Reconcile player records with team-game identities and validate season coverage against an accepted expected-game inventory when available. If expected coverage cannot be established, mark it unknown rather than infer completeness from the same returned file.
6. Run the 2025-26 seed locally after the accepted sample passes. Report missing games, missing/invalid fields, conflicts, and unexpected competitions separately. Do not synthesize historical rosters or DNP rows by crossing current rosters with past games.
7. Deliver the compact source/backfill notebook, add fixture execution to PR CI, and document exact working CLI/kernel commands, artifact locations, resume behavior, source gaps, and archive/backup status.

## Notebook contract

Use concise sections with clearly labeled purpose, inputs, run, inspect, and interpretation. Show the accepted source-capability report, raw-to-normalized flow, a small schema/record sample, validation counts, checkpoint recovery, and saved-artifact readback. Explain one important limitation of historical timing evidence.

The default fresh-kernel path uses fixed local fixtures, requires no NBA or production Supabase access, and cannot start a full live backfill, publish forecasts, or promote models. Full collection is a separate explicit opt-in operation. Use the project environment, record the dependency lock hash and input manifest identities, and display whether work executed or reused validated artifacts. Changed inputs/configuration must invalidate reuse. Keep large data outside the notebook and commit only concise outputs.

## Acceptance criteria

- [ ] Collection and normalization run locally through shared package operations, with an actual documented CLI and project-kernel walkthrough.
- [ ] The archive includes source evidence, validated player/team Parquet, manifests, and readback validation for the 2025-26 regular-season seed, or an explicit failed/incomplete seed report. A partial seed is not reported as complete.
- [ ] Resume reuses only completed units with valid identities and hashes. Unchanged reruns do not duplicate normalized versions; legitimate revisions remain independently inspectable.
- [ ] Player/team identities, game classification, target types/units, minute precision, duplicates, nulls, and team-side consistency are checked. Missing players or rounded zero minutes do not automatically become DNP outcomes.
- [ ] Coverage identifies the expected-game source, observed games and gaps, unresolved expectations, and how missing history can affect later baselines. It does not assume a fixed player count per game or silently omit incomplete rows from the report.
- [ ] The notebook runs sequentially from a fresh kernel on fixtures, matches the CLI's semantic outputs for the same inputs, and labels artifact reuse. Its default path cannot contact live services or perform production operations.
- [ ] PR CI includes lightweight fixture notebook execution with the locked environment. No full backfill or NBA uptime is needed for CI to pass.
- [ ] Raw data, complete datasets, credentials, and personal absolute paths are absent from tracked outputs. README, AGENTS.md commands, and Weaknesses.md reflect measured results and unresolved limitations.

## Required tests

- Validate string IDs including leading zeros, season/competition boundaries, trades, repeated records, conflicting team identities, missing/nonfinite/negative values, noninteger counting stats, explicit versus unknown participation, and source minute formats/precision. Preserve valid overtime data rather than enforcing a universal 48-minute cap.
- Interrupt after raw storage, during Parquet creation, and before checkpoint finalization. Resume must retain evidence, reject partial artifacts, and avoid duplicate accepted versions. Corrupt an archived file and verify checksum/readback failure prevents reuse.
- Replay unchanged content, a corrected source body, and a parser/configuration change. Verify reuse versus a new version and preserve each observation's collection time.
- Reconcile a fixture with two team sides and supported player records; inject a missing game, extra competition, inconsistent scores, and unavailable expected-game inventory. The report must expose each gap rather than declare completion from row counts alone.
- Leakage fixtures preserve a late correction's later collection time and cannot label it available at an earlier cutoff. A previous-season row's game date is not proof of its original publication time. Final box-score membership or a current roster cannot become a historical forecast cohort.
- Execute the notebook from a fresh kernel on fixtures and compare semantic tables/manifests with the CLI. Inject stale cache identity and confirm rejection. Block live transport and production writes to prove the default walkthrough stays within its rehearsal boundary.

## Failure decision and likely files

The agent may complete implementation with a truthful failed/incomplete collection report, but launch seed acceptance remains blocked until required history is valid or the owner explicitly revises coverage. Missing history must remain visible for the later abstention/coverage policy. Do not add older seasons, substitute a new unreviewed source, or bypass access controls to make the report pass.

Likely files: `src/hoop/domains/nba/sources/`, `src/hoop/domains/nba/normalization/`, shared artifact/checkpoint helpers under `src/hoop/platform/`, `src/hoop/cli.py`, `configs/sources/`, `notebooks/01_sources_and_backfill.ipynb`, `tests/unit/`, `tests/leakage/`, `tests/notebooks/`, reviewed `tests/fixtures/nba/`, `.github/workflows/ci.yml`, dependency files where Parquet/kernel execution support is needed, README.md, AGENTS.md, and Weaknesses.md. Full archive/checkpoint/report files live in ignored configured paths.

## Handoff

Return the PR, exact commands/check outcomes, full-seed run evidence, artifact manifest IDs/checksums, coverage and quarantine summary, resume/revision demonstration, notebook walkthrough, measured request volume/runtime/archive size, and backup state. Explain the data flow, why source precision and historical timing limit later evaluation, and one recovery failure scenario. Owner review accepts the history for later database import; no full Phase 0 completion is implied by this task alone.

Approval: the owner explicitly said "lock" on October 13, 2026. This finalizes the specification; a separate assignment to the coding agent starts execution. No history collection, notebook execution, or seed acceptance has been performed by this planning record.
