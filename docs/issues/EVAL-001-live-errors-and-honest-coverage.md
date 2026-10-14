# EVAL-001: Report live baseline errors and honest coverage

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Phase: 1. Priority: launch blocker. Dependencies: OUTCOME-001, COLLECT-001, and LEDGER-002 implemented and owner-reviewed. Session estimate: about 2.5 agent hours plus owner review. Scope is player launch metrics/report evidence, not the trained-model promotion harness, drift, or dashboard.

## Goal and contracts

Produce reproducible prediction-versus-outcome errors and coverage without treating missing forecasts or outcomes as success. Use shared report operations callable by nightly jobs and notebooks. Deadline: October 20, 2026 at 19:00 UTC for a working reporting path, even if regular-season accuracy is initially unavailable.

Read AGENTS.md and skills `hoop-ml-lifecycle`, `hoop-postgres`, `hoop-python-testing`, and `hoop-notebooks`. Contracts: [PRD populations](../PRD.md#eval-01-report-populations-and-denominators), [design evaluation tables](../design.md#63-forecasts-and-outcomes-phase-1), and [ADR 0010 historical comparisons](../decisions/0010-publish-an-independent-dashboard-with-honest-history.md).

## Report contract

- Add immutable `platform.evaluation_reports` by migration: report_id UUID; domain, report_kind, policy_version; period_start, period_end, created_at UTC; predictions_manifest_id, outcomes_manifest_id, report_artifact_id FKs; summary JSONB with counts/primary metrics. Restrict runtime to required read/append, deny mutation and anonymous private reads.
- Freeze one report cutoff, eligible forecast IDs/receipts, roster/schedule opportunity evidence, outcome-version IDs, input manifests, policy, and code/dependency identity. Choose outcome revisions known by that report cutoff before computing. Corrections produce new reports and preserve older manifests/results.
- Initial periods are seven days, 30 days, and season to date, with explicit UTC half-open bounds. Assign games by effective scheduled UTC start known at report cutoff, retaining that observation in the manifest. Do not group by collection/upload day. Rehearsal/preseason and historical replay never enter regular-season live summaries.
- Valid official predictions require timely receipts and no applicable invalidation/excluded occurrence. Keep stored-unverified, invalidated, postponed/canceled, abstained, and unresolved categories separately, with reason counts. A known exclusion cannot become valid because its audit append is pending.
- Per numeric target, resolve prediction, actual, signed error (prediction minus actual), and absolute error in that target's units. MAE is sum of absolute errors divided by scored count. Include confirmed DNP zeros in overall MAE and show played-only MAE separately. Unknown outcomes remain unscored, never zero.
- Show model/bundle versions, scored observations/distinct games, outcome resolution, exclusions, invalid/unverified predictions, and comparison counts. Keep units separate; do not average minutes and points into one unlabeled loss.
- Schedule coverage counts expected supported regular-season occurrences and those with a valid complete player batch. Player numeric coverage divides valid numeric predictions by expected saved roster-player-target opportunities; abstentions stay in the denominator. For missing/unknown rosters, report uncovered games and an unknown denominator rather than zero or perfect coverage. Excluded occurrences are identified separately, with retained original attempt history.
- For published batches, use their frozen cohorts. For uncovered games, only independently saved roster evidence eligible before that occurrence's publication cutoff may establish expected opportunities. Never reconstruct a missing pregame denominator from a later roster or final participant list; keep those retrospective diagnostics separate.
- Add actual-participant coverage as a retrospective diagnostic, showing missed roster additions. Diagnostic groups may use actual minutes bands (<10, 10 to <25, at least 25), team, and role/availability only when supported. Label actual-outcome groups as diagnostics, never pregame features or promotion groups. Small groups show counts; unavailable metadata is explicit.
- Compare future model outputs on identical subject/game/target rows only, exposing unmatched cases. At launch only the official recent-history baseline exists; do not invent a challenger or claim improvement from comparing it with itself.
- Store compact input-ID manifests and reproducible calculations rather than duplicate every numeric ledger row into another table or daily full-season JSON. Detailed errors can be queried/rebuilt from frozen references, with a small saved fixture/example. Measure report growth before scheduling repeated reports. A zero scored count/denominator yields unavailable with reasons, not zero MAE or 100% coverage.

## Acceptance criteria

- [ ] Hand-calculated fixtures independently verify signed/absolute errors, per-target MAE, confirmed DNP treatment, period bounds, and both coverage denominators.
- [ ] Reports preserve prediction/receipt/outcome versions and reproduce after later corrections; excluded/replay/rehearsal/unverified records cannot enter valid live accuracy.
- [ ] Empty season, insufficient metadata, unresolved outcomes, unknown rosters, and unmatched comparisons produce explicit unavailable/count states.
- [ ] Migration/actual-role tests pass; report artifacts/references verify on read, and repeated exact report input identity cannot overwrite prior evidence.
- [ ] Shared CLI/fixture notebook reporting works; PR checks pass; README/AGENTS.md explain metrics, limitations, and regular-season accuracy availability.

## Required tests

- Independent small fixtures with nonzero positive/negative errors, fractional values, multiple targets/units, played and confirmed DNP cases, unresolved actuals, missing history abstentions, and zero scored rows.
- Valid receipt versus missing/late receipt, invalidation/cancellation/postponement, unknown roster denominator, multiple games/rosters, duplicate IDs, missed actual participants, and excluded categories. Verify counts reconcile without silently dropping rows.
- Seven/30-day/season bounds at UTC boundaries, revised schedule/outcome observations after report cutoff, and mixed rehearsal/preseason/replay/live records. Later labels cannot rewrite prior report inputs or pregame features.
- Corrected outcomes retain the old report and create a new version; corrupt artifact, missing reference, interrupted write, and conflicting retry fail safely.
- Actual-role migration/permissions and fixture CLI/notebook equivalence. Later promotion thresholds/drift tests are out of scope, not silently declared passed.

## Files and handoff

Likely files: evaluation-report/grant migration; shared evaluation/report/manifests operations; NBA target/outcome adapters; CLI and reporting policy; unit/integration/leakage/notebook fixtures; compact reporting cells in the baseline notebook; README.md, AGENTS.md, Weaknesses.md. No Evidently, LightGBM, dashboard, or automatic promotion dependency.

Return PR/check outcomes, independent arithmetic/coverage report, report/input IDs/hashes, correction reproduction, usage measurement, and metric availability. Explain why confirmed DNP affects MAE while an unknown actual does not, and why coverage is separate from accuracy.

Approval: the owner's October 14 batch approval locks this specification. A separate assignment starts execution. No report migration, accuracy calculation, notebook run, or live season performance has been produced by this document.
