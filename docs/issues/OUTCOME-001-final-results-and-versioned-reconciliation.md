# OUTCOME-001: Collect final results and reconcile versioned outcomes

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Phase: 1. Priority: launch blocker. Dependencies: COLLECT-001, LEDGER-002, and DB-003 implemented and owner-reviewed, with an accepted final-box-score adapter from SOURCE-001. Session estimate: about 3 agent hours plus actual final-source rehearsal and owner review.


## October 25 execution context

The owner resumed sequential execution with the [historical-data amendment](../PRD-data-source-amendment.md).
Use accepted pinned seed/repair artifacts, preserve quarantine and unknowns,
and never infer historical pregame cohorts from outcomes. Injury ingestion is
deferred for the first release. The original October 20 target is past;
all timing/readiness gates now apply to the first approved future slate.
This task is backlog until its implemented/reviewed dependencies pass.
No runtime source acceptance, merge, deployment, or retrospective publication
is established by this amendment. Required tests and contracts below remain.


## Goal and scope

Append validated final player/team facts and outcome versions for saved game occurrences without editing forecasts. Supply reusable reconciliation commands and the final portion of the launch baseline notebook. No accuracy report, training, or scheduler here. Deadline: October 20, 2026 at 19:00 UTC; final outcomes will accumulate after games.

Read AGENTS.md and skills `hoop-data-quality`, `hoop-postgres`, `hoop-python-testing`, and `hoop-notebooks`. Contracts: [PRD outcome rules](../PRD.md#ledger-03-schedule-changes-and-outcomes), [design forecast/outcome tables](../design.md#63-forecasts-and-outcomes-phase-1), and [ADR 0004](../decisions/0004-enforce-immutable-pregame-publication.md).

## Data and persistence contract

- Add `platform.outcome_versions` through a migration: outcome_version_id UUID primary key; event_id FK; observed_at UTC; source_check_id FK; outcome_artifact_id FK; state. Outcome artifacts contain subject/target values or explicit unknowns, participation/units, game/season identity, and references to normalized source revisions. Rows/artifacts are immutable under runtime credentials.
- Discover pending final work from persisted schedule occurrences and prior reconciliation state, not today's scoreboard alone. Explicit IDs/date-range commands support late finals and older correction checks. Skip excluded postponed/canceled predecessors; unresolved suspensions remain pending until supported treatment is established.
- Use the accepted final adapter with raw retention, original receipt/validation/publication metadata, hash checks, existing retry/denial policy, and a measured run budget. Overtime is included. A status label alone is insufficient if required final identities/fields fail validation.
- Validate both team sides, game/team/player joins, scores, counting-stat types, source minute precision in seconds, duplicates/conflicts, and completeness. Do not equate a missing player row, rounded zero minutes, or an incomplete payload with DNP.
- Assign zero minutes and counting stats to a saved-cohort player only when accepted source semantics establish confirmed nonparticipation in that completed occurrence. Record the evidence. Otherwise preserve unresolved outcomes and coverage impact. Later roster/participant evidence is an outcome diagnostic, never a replacement pregame cohort.
- Persist normalized player/team revisions using DB-003 and upload the outcome artifact before a short database transaction. Append a new outcome version on changed facts or parser/configuration, retaining prior IDs and times. Exact retries reuse the same semantic version/checkpoint, while distinct source observations remain saved. No forecast/receipt/slot mutation.
- Version states distinguishing pending, partially resolved, and supported final outcomes. Supported individual targets may resolve while another field remains unknown, with explicit per-target resolution in the artifact. Never publish a fake zero error or claim complete outcomes from partial data.
- Initially recheck the last seven days of completed games under the request budget, plus all unresolved known IDs. This is a project workload policy, not a guarantee about source corrections. Older changes require the explicit ID/range command; record this limitation in Weaknesses.md. Detect changed bytes and preserve both versions.

## Notebook and acceptance

Extend `02_baseline_and_ledger.ipynb` using fixture shared operations: final ingestion, confirmed DNP versus unknown, matching saved predictions, and corrected outcome readback. Keep Run All in rehearsal/disposable data, with live sources and production writes disabled. Explain that accuracy aggregation is EVAL-001, not an outcome-row overwrite.

- [ ] A migration creates immutable outcome versions and required grants; fresh/upgrade and real runtime-role checks pass.
- [ ] Pending-ID/range reconciliation retains source/fact/artifact provenance and distinguishes final, partial, unresolved, excluded, and failed processing.
- [ ] Confirmed DNP zeros require evidence. Missing/incomplete data stays unscored; overtime and original precision remain supported.
- [ ] Repeated/corrected ingestion preserves forecast values and every prior outcome version, while exposing the new comparison revision.
- [ ] Notebook/CLI fixture results agree; PR checks pass. An actual accepted final-source rehearsal is separately recorded, labeled preseason if applicable, with unresolved regular-season limitations.

## Required tests

- Complete and incomplete finals, missing game/player/team side, identity/score mismatch, missing stats, invalid values, overtime minutes, explicit DNP versus absent row/rounded zero, and a player no longer present in the later roster.
- Night/UTC boundaries, late finalization from persisted IDs, no rediscovery via current scoreboard, postponed predecessor/new occurrence, suspended game, and correction outside the automatic recheck horizon.
- Exact retry, changed body/parser, partial database transaction, corrupt/missing artifact, exhausted source budget, and retry after interruption. Forecast IDs, values, recording times, and receipts remain identical.
- Leakage fixture: append later final participation, corrected facts, and rosters, then reproduce the earlier features/cohort. Outcome data cannot enter the original input snapshot.
- Fresh/upgrade Postgres migration and actual-role mutation denial, plus fresh-kernel notebook/CLI equivalence with production connections/live transport blocked.

## Files and handoff

Likely files: outcome/grant migration; NBA final adapter/normalization/reconciliation operations; generic outcome-artifact contracts and CLI; reconciliation policy/checkpoints; unit/integration/leakage/notebook fixtures; baseline notebook, README.md, AGENTS.md, source notes, Weaknesses.md.

Return the PR, checks, real-source scope, final/partial/unresolved counts, IDs/hashes, corrected-outcome demonstration, notebook walkthrough, measured requests/runtime, and limitations. A missing final source blocks trusted reconciliation, not permission to synthesize labels.

Approval: the owner's October 14 batch approval locks this specification. A separate assignment starts execution. No final result, outcome migration, reconciliation, or notebook run has been performed by this document.
