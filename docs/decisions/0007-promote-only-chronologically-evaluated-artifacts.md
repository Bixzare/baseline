# ADR 0007: Promote only the exact chronologically evaluated artifact

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD evaluation harness](../PRD.md#eval-02-chronological-harness), [promotion gates](../PRD.md#model-02-promotion-gates), [rollback requirements](../PRD.md#model-03-model-history-and-rollback), and [design Section 10](../design.md#10-evaluation-and-exact-artifact-promotion). This record documents approved policies; no candidate evaluation or promotion has been performed.

## Context

Baseline will retrain automatically, but successful training does not establish that a candidate should replace the champion. A fair comparison needs the same eligible observations, features available at each prediction cutoff, and an artifact that has not learned from its evaluation outcomes.

Refitting a model on its evaluation period produces a different artifact. Combining the live results of several historical champion versions also does not measure the current champion against one fixed challenger.

## Decision

- Use a recent 30-day interval ending at a recorded UTC boundary after reconciliation. Train the challenger strictly before that interval starts, using earlier development data for tuning, preprocessing selection, and probability calibration.
- Reconstruct each prediction from inputs and roster evidence available at its historical cutoff. Replay the current fixed champion and the challenger on identical snapshots. Keep official live performance, with its original version changes, separately labeled.
- Freeze the eligible cohort, input manifest, outcome revisions, candidate configuration, and evaluation policy before comparing. Do not repeatedly tune against the promotion window. Preserve failed comparisons and disclose overlapping-window reuse.
- Allow stateful baselines to update from earlier available outcomes as they would online. Keep trained parameters fixed during comparison; features can incorporate new prior-game information without incorporating the target outcome.
- Require candidate primary loss at most 0.98 times champion loss, at least 100 distinct completed games, full required prediction coverage, and valid data, leakage, artifact, and compatibility checks. Extra player rows do not count as extra games.
- Require every blocking secondary or group loss to be at most 1.05 times its champion value. Each required player group needs at least 100 observations. Use the same versioned last-10 baseline minutes prediction to assign both models' groups: below 10, 10 to below 25, and at least 25 minutes. Missing required evidence retains the champion.
- Evaluate minutes by minutes MAE, with guardrails on the final counting stats affected by a minutes change. Evaluate each rate component by MAE of its composed counting-stat output, with required group and coverage checks. Rate error alone cannot justify promotion.
- Evaluate team win probability by Brier score, with log loss and calibration error as blocking secondary metrics. Evaluate margin and total by their MAE, with coverage and output validity checks; team and venue slices remain diagnostics initially.
- Measure calibration as the sample-weighted absolute difference between mean predicted home-win probability and observed home-win frequency in five fixed equal-width bins. Show bin counts and empty bins. Clip only for log-loss computation under a recorded epsilon; preserve published probabilities.
- If champion primary loss is zero, the required relative improvement cannot be established. A zero-loss guardrail allows no worsening. The 2%, 5%, and sample thresholds are starting operating policies, not statistical-significance guarantees.
- Promote one component at a time and regenerate its bundle. Re-evaluate if the champion bundle changes before activation. Change the active pointer atomically with the decision record; validate artifact readability and compatibility first.
- Deploy the exact tested artifact without refitting on the held-out interval. Log approval, rejection, insufficient evidence, failed activation, and rollback with versions, policy, and evaluation references. Activation changes only future forecasts; failed activation retains or restores the prior usable champion.
- Require defensible full-roster evidence, including confirmed DNPs. If historical reconstruction is inadequate, retain the baseline and collect prospective evidence under the same gates. Participant-only exploration and shadow records cannot become official live proof.

## Reason and alternatives

This connects a promotion decision to a reproducible paired comparison and the precise model used afterward. Stable group assignment prevents a candidate from changing group membership to hide difficult observations. Coverage checks prevent apparent gains from dropping predictions.

Random train/test splits would mix future and earlier observations. Deploying an untested refit would disconnect validation from the production artifact. Promoting on overall loss alone could conceal degraded playing-time groups or dependent outputs. Those alternatives are not selected.

## Consequences

The deployed fitting cutoff is at least 30 days behind the evaluation endpoint, although its features may use newer prior games. This deliberately trades training freshness for a reviewable evaluation interval. A later prospective promotion policy would require a separate design decision.

Small samples, missing groups, imperfect historical evidence, or zero reference loss can prevent promotion despite successful training. The baseline remains champion until all gates pass. Reconstructed backtests are disclosed as historical replay and do not enter the official ledger.

## Verification required during implementation

- Exercise cutoff boundaries, future features, training/tuning/calibration overlap, changed input or outcome manifests, and attempted deployment of a refitted artifact.
- Test exactly 2% improvement and 5% regression, zero primary/guardrail losses, 99 versus 100 distinct games, and 99 versus 100 required group observations.
- Verify shared group assignments, composed-output guardrails, missing predictions, confirmed DNPs, and insufficient historical cohort evidence.
- Verify calibration bins, empty bins, per-bin counts, metric-only log-loss clipping, and unchanged published probabilities.
- Test stale champion generations, incompatible or unreadable artifacts, atomic activation, recorded rejection, rollback, and preservation of earlier forecasts and live track-record versions.

Approval: the owner explicitly said "lock" on October 12, 2026. This record does not establish measured model superiority, promotion readiness, or a deployed model.
