# Baseline: Product Requirements

Status: LOCKED by the project owner on October 12, 2026. This approves the requirements; implementation remains assigned to a separate coding agent.

Version: 1.1

Prepared: October 12, 2026

Season: 2026-27 NBA regular season

Owner: Bixzare

Sources of intent: [Project proposal](../Initial-project-description.md), [locked critical path](critical-path.md), and the owner's subsequent confirmed planning decisions. Confirmed decisions supersede conflicting proposal language. The clarifications in Section 15 were accepted when this document was locked. Changes to these requirements require an explicit owner decision.

Version 1.1 incorporates the [locked notebook amendment](PRD-notebook-amendment.md) and [locked awards eligibility and validation amendment](PRD-awards-eligibility-amendment.md), approved October 12, 2026. The [locked technical design](design.md) supplies implementation contracts and verification gates. Document version 1.1 does not change the product's v1 and v1.5 delivery boundaries.

## 1. Purpose and users

Build an autonomous NBA ML service that produces predictions before games, collects outcomes, reports its own accuracy and coverage, monitors data and model health, and retrains and promotes models under explicit rules. A public dashboard makes this evidence understandable to basketball fans, analysts, and technical interviewers.

The engineering work must demonstrate judgment: reproducible data, honest evaluation, reliable operations, documented tradeoffs, and recovery from failures. Beating every baseline is an ambition, not a condition for publishing results. Poor performance must remain visible.

The owner must understand the purpose, data flow, major choices, and failure modes of each implemented component. Coding agents execute one issue at a time, with owner review of every diff.

## 2. Delivery boundaries

| Delivery | Required behavior | Release gate |
| --- | --- | --- |
| Phase 0 | Verify cloud live sources, a working local historical backfill, current roster access, and an injury source or explicit deferral. | Recorded evidence from the actual execution environments; reliable fallback selected. |
| Phase 1 | Automated collection, five player baseline targets, immutable ledger, result reconciliation, basic accuracy and coverage, source health, and recovery. | Live predictions before opening tip-off on October 20, 2026 at 19:00 UTC; publication target 17:00 UTC. |
| Team baseline increment | Win probability, margin, and total with target-specific baselines. | Same publication, ledger, and outcome correctness gates as player predictions; follows launch immediately. |
| Remaining v1 | Trained player and team models, evaluation harness, model monitoring, retraining and promotion, explanations, and six public dashboard views. | Requirements in this document pass; no deadline is invented for this scope. |
| v1.5 | Weekly awards ladders and insights; richer explanations of changes. | Historical awards validation, eligibility tests, and verified permitted source access. |
| Later | Era comparisons, in-game tracking, prediction intervals, Clash Royale deployment, and other modular analytics. | Separate scope decision; cannot delay Phases 0 and 1. |

Regular-season predictions are the v1 scope. Preseason is for rehearsal only and must be labeled separately. Play-in, playoffs, exhibitions, and other events require explicit support before entering the official record. A game must be classified by verified competition metadata rather than calendar date alone.

No betting features, odds, wagering advice, access-control evasion, user accounts, or model training from the dashboard are in scope. No implementation code is part of this planning deliverable.

## 3. Data requirements

### DATA-01: Source verification and provenance

Use nba_api for supported NBA interfaces. Historical stats.nba.com collection runs locally. Cloud collection uses verified cdn.nba.com sources; access is not assumed to work. The package documents both stats and live interfaces, but its live scoreboard example concerns today's games, not a complete future schedule. [nba_api documentation](https://github.com/swar/nba_api) and [scoreboard documentation](https://github.com/swar/nba_api/blob/master/docs/nba_api/live/endpoints/scoreboard.md).

Phase 0 must separately verify historical player and team records, future schedules, game status, final box scores, and current rosters. A source capability is accepted only when required fields and coverage are demonstrated. A successful HTTP response is insufficient.

Retain raw responses without overwriting them, with source, request parameters excluding secrets, collection time, content checksum, parser version, and run identifier. Document access terms and a conservative request policy. No guaranteed rate limit has been verified; do not present a guessed request frequency as an entitlement.

Acceptance: saved fixtures and run evidence cover a completed game, an upcoming game, a no-game day, roster identity joins, malformed payloads, and repeated requests. Backfill can resume without duplicate normalized records. Known historical gaps are reported.

### DATA-02: Information available at prediction time

Every prediction references the exact feature and source versions it used. Live inputs must have been collected and validated by the feature cutoff, which cannot follow prediction publication. Event time, source publication time when supplied, and our collection time have different meanings and must not be conflated.

Features exclude the target game's outcomes, eventual lineup, participation, and later injury reports. Aggregated season statistics are reconstructed from eligible prior records. Revised source values cannot overwrite what an earlier prediction saw.

Historical data collected now does not prove original publication timing or preserve all historical corrections. Backtests must declare availability assumptions and missing historical context. They must not be labeled as live ledger evidence. If a feature's historical availability cannot be defended, omit it from the primary backtest or report it only as a separate sensitivity analysis.

Acceptance: explicit leakage tests inject future games, late availability updates, corrected box scores, final-season totals, and future roster changes. None may change an earlier feature snapshot. Tests cover UTC date boundaries and daylight-saving transitions.

### DATA-03: Rosters and availability

The prediction population is the latest verified roster snapshot for each scheduled team, known at publication. Preserve source identity and collection time. Do not infer the forecast population from the final box score.

Missing injury information is unknown availability, not evidence that a player is healthy. Injury ingestion may be deferred at launch. If adopted, preserve successive report versions and use only reports available before publication.

The previous season's official injury-report page establishes a candidate source, but a usable 2026-27 page and automated ingestion have not been verified in this planning session. [Official 2025-26 injury reports](https://official.nba.com/nba-injury-report-2025-26-season/).

Acceptance: handle trades, missing roster feeds, conflicting identity records, rookies, and unknown availability. An incomplete or stale roster blocks affected publication according to the freshness policy. Missing roster coverage must not appear as a successful empty slate.

## 4. Player projections

### PLAYER-01: Launch baseline

For each rostered player and scheduled game, produce minutes, points, rebounds, assists, and three-pointers made, or record an explicit abstention.

Use up to the last 10 completed regular-season appearances available at the feature cutoff. The window crosses season and team boundaries and excludes preseason, playoffs, and nonappearances. Use fewer than 10 when necessary and show the history count. Launch history begins with 2025-26; subsequent 2026-27 appearances enter the rolling window.

Predicted minutes are average minutes across those appearances. Each production rate is the sum of that stat divided by the sum of minutes over the same appearances. The counting-stat projection is predicted minutes multiplied by that rate. With identical complete windows, this equals the average counting stat across appearances; the baseline does not claim an advantage from its decomposition.

An appearance without valid minutes cannot support rate computation. No usable history or a zero total-minute denominator produces an insufficient-history or invalid-data abstention. Missing values are not silently replaced with zero. Keep history-count and availability flags beside each prediction.

Acceptance: deterministic expected-value fixtures verify all five outputs, one appearance, fewer than 10, exactly 10, older excess history, season rollover, transfers, zero-minute denominators, missing fields, and future-game exclusion. Outputs are finite and nonnegative; precision rules are documented in design.

### PLAYER-02: Trained models and explanations

Use a dedicated minutes model and separate production-rate models. Their composed outputs are the public counting-stat projections. Point estimates are required; intervals are deferred until their empirical coverage is evaluated.

After launch, initially collect three completed seasons and compare one-season and three-season training windows through chronological backtests. Choose the production window based on evidence. Do not combine historical eras merely to maximize row count.

Zero-minute outcomes remain relevant to minutes and final stat evaluation, but cannot be divided into production rates. A rate model must handle its training population explicitly. If a rate model consumes minutes predictions, its training inputs must be generated without seeing the same row's outcome.

Compare against both the recent-appearance baseline and a current-season-average baseline where the latter has sufficient history. Report the benchmark's unavailable cases separately. Baseline results continue after trained models launch.

Show baseline inputs or model feature contributions as appropriate. Explain model behavior without claiming that contributions establish causality. Rich explanations of changes between successive predictions are v1.5.

Acceptance: reproduce a feature snapshot and its projection from versioned artifacts; test composition, zero-minute handling, and leakage. Publish MAE for each final target, baseline comparisons, group results, and data limitations even when the model loses.

## 5. Team predictions

### TEAM-01: Targets and baselines

Produce home-win probability, expected margin defined as home points minus away points, and expected total points. Final outcomes include overtime. Probabilities lie between zero and one; margin may be negative; total must be nonnegative. Report winner choice from probability with a documented tie convention.

Use Elo for win probability. Use recent team scoring and points allowed for margin and total; exact formulas and windows belong in design and must be fixed before evaluation. Elo initialization, offseason treatment, home advantage, and update timing must also be versioned. Update ratings only from outcomes available before the next forecast.

Team prediction coverage must not depend on complete player projections at the baseline stage. Later models may use player projections if those inputs meet the same information cutoff and their missing coverage is explicit.

Acceptance: test home/away reversal, outcome signs, total calculation, overtime, postponed games, Elo update order, missing team history, and probability bounds. Report Brier score and log loss for probability; MAE for margin and total; probability calibration diagnostics with sample counts.

## 6. Prediction ledger and lifecycle

### LEDGER-01: Required prediction information

The ledger must retain the following logical fields. Exact table and column definitions belong in design.

| Information | Required meaning |
| --- | --- |
| Identity | Domain, season, source game ID, game occurrence ID, subject type and ID, target, and prediction ID. |
| Value | Numeric estimate or probability, units, and model role: official, benchmark, shadow, or rehearsal. |
| Timing | Trusted database recording time, generation time, feature cutoff, scheduled tip-off as observed, and publication-policy version. |
| Model provenance | Model or component-bundle version, artifact reference, code version, and configuration version. |
| Data provenance | Immutable feature snapshot reference, source references, roster snapshot where relevant, and input freshness. |
| Operations | Run ID and idempotency identity linking retries without duplicating official predictions. |

Abstentions are separate auditable forecast decisions with the same game, subject, target, timing context, and a reason. They are not numeric predictions with a null value silently excluded from reporting.

### LEDGER-02: Publication and immutability

Publish one official prediction per game occurrence, subject, and target. Aim for two hours before scheduled tip-off; recovery attempts may publish only before the cutoff 15 minutes ahead of scheduled tip-off, and never after the game has started. Apply the policy to player and team predictions. Reject at the cutoff as well as after it.

Persist an official forecast before reporting publication success. A caller cannot supply an earlier trusted timestamp. Predictions generated before the cutoff but durably recorded too late do not count as valid forecasts. Concurrency between cloud and local runners cannot create two official values.

Prediction records cannot be updated or deleted by the runtime writer. Outcomes, errors, corrections, invalidations, and lifecycle statuses are separate append-only records. A correction never silently substitutes a more favorable official prediction. Record administrative repairs and export an auditable history; database controls are not a claim of cryptographic protection against the database owner.

Benchmark and shadow predictions are distinct from the single official value and cannot later be relabeled to improve the official track record. Historical replay records must never enter the live ledger namespace.

Acceptance: test concurrent writers, identical retries, conflicting retries, prohibited updates and deletes, untrusted timestamps, cutoff boundaries, delayed persistence, and games already underway. Reproducing a forecast preserves its original model and data references.

### LEDGER-03: Schedule changes and outcomes

A postponement appends a status, preserves predictions, and removes that occurrence from scored accuracy. Publish new forecasts for the rescheduled occurrence, even when the upstream game ID is reused. Preserve the relationship between occurrences and report exclusions.

A schedule correction or earlier actual start that makes an existing publication invalid produces an appended invalidation. Do not reopen a missed cutoff merely because a feed later reports a delayed start. Suspended or otherwise unresolved games remain pending until their treatment is verified.

Reconcile only validated final outcomes. Confirmed nonparticipants in completed games receive zero minutes and counting stats for evaluation. Absence from an incomplete payload is not sufficient evidence of nonparticipation. Missing outcomes remain unresolved and unscored.

Corrections to final statistics create new outcome and evaluation versions. Show the outcome revision used by a report and retain earlier reports or their reproducible inputs.

Acceptance: test postponement before and after publication, upstream ID reuse, earlier start, suspended games, confirmed DNP, missing player data, late finalization, corrected outcomes, and duplicate result collection.

## 7. Coverage and honest evaluation

### EVAL-01: Report populations and denominators

Publish overall player MAE including confirmed nonparticipants and a separate played-only MAE. Report errors by target, minutes band, role, team, and availability status when the required metadata exists. Distinguish groups defined by actual outcome, used for diagnosis, from features known at forecast time.

For every report, show period, model versions, scored count, unresolved outcomes, invalid forecasts, exclusions, and benchmark comparison count. Do not pool targets with different units into one unlabeled error score.

Report schedule coverage independently from player coverage. Player forecast coverage is valid official numeric forecasts divided by expected roster-player-target opportunities from verified snapshots. Abstentions remain in that denominator. Unknown rosters create an explicit unknown denominator and uncovered game count, not 100% coverage. Report coverage among actual participants as an additional retrospective diagnostic so missed roster additions are visible.

Compare models and baselines on identical subject-game-target rows. Also show unmatched cases and overall coverage so selective abstention cannot manufacture an apparent improvement.

Acceptance: fixed fixtures verify each denominator, DNP treatment, no-history cases, missing rosters, unresolved outcomes, and common-cohort comparisons. A zero denominator displays unavailable, never a misleading zero error or perfect score.

### EVAL-02: Chronological harness

Train only on data preceding each evaluation interval. Tune parameters and feature choices using earlier development intervals; reserve later data for evaluation. Random row splits are not acceptable for the primary time-dependent evaluation.

Backtests must reconstruct schedule, roster population, and availability where possible. If historical roster evidence is unavailable, a participants-only retrospective cohort may be published separately with that limitation, but cannot substantiate historical all-roster coverage or DNP accuracy.

Record date ranges, feature versions, source assumptions, model artifacts, baseline configurations, metrics, group definitions, and attempted challengers. Report failures and rejected candidates. Repeated comparisons on overlapping windows are correlated evidence, not independent confirmations.

Acceptance: train, tuning, and evaluation boundaries are testable; forward data perturbations cannot affect earlier predictions; a report can be reproduced from retained inputs. Aggregate performance cannot conceal losing targets or groups.

## 8. Source and model monitoring

### MON-01: Operational health, required at launch

For every source and run, record success or failure, latency, record counts, schema compatibility, required-field completeness, duplicate identity checks, timestamp validity, and freshness. Distinguish a verified no-game day from an empty or broken response.

Track expected runs and publication deadlines as well as failures of runs that actually started. A missing scheduler invocation must be detectable. Track outcome reconciliation backlog and storage failures.

Invalid or stale essential data blocks affected forecasts and model promotion. Preserve unaffected processing when safe. Preserve the last successful public snapshot with a visible stale status rather than presenting it as current. Notifications must reach the owner outside the dashboard; the transport and escalation timing are design decisions.

Acceptance: inject request failures, empty payloads, schema changes, nulls, stale schedules and rosters, missing runs, database failures, and late outcomes. Verify an actionable alert and the correct blocked or degraded state. Recovery clears active status without erasing incident history.

### MON-02: Accuracy and drift, remaining v1

Show 7-day and 30-day MAE for numeric targets and Brier score and log loss for win probability, with coverage and sample counts. Evaluate performance degradation relative to a baseline on the same observations.

Monitor important feature distributions, prediction distributions, missingness, and source behavior against versioned reference data. Drift scores require minimum samples and season-context annotations. Drift alone raises an investigation signal; it does not cause automatic retraining or promotion.

Performance-trigger thresholds, persistence duration, reference windows, calibration diagnostics, freshness limits, and notification timing must be specified and tested in design before these automations are enabled. Missing configuration means automation is disabled with an explicit reason, not a guessed default.

Acceptance: stable and shifted fixtures exercise signals, small samples show insufficient evidence, and data corruption cannot trigger training on invalid input. Public views distinguish measured drift from demonstrated accuracy degradation.

## 9. Retraining, promotion, and recovery

### MODEL-01: Retraining

Schedule retraining weekly when enough new validated data is available. Persistent performance degradation may trigger an extra run. Apply a seven-day cooldown to performance-triggered extra runs, deduplicate overlapping triggers, and avoid concurrent training for the same component. A scheduled run can satisfy a pending performance trigger.

A trigger records why training was requested; training does not imply deployment. Store runs, configurations, training cutoffs, artifacts, metrics, and failures. If data is invalid, training fails, or evidence is insufficient, retain the champion and record the reason.

Acceptance: test scheduled and performance triggers, no new data, invalid data, cooldown, overlapping requests, failed training, and successful completion without promotion.

### MODEL-02: Promotion gates

These are agreed starting operational policies, not evidence-backed optimal thresholds or statistical-significance guarantees. Changes require a versioned decision and apply prospectively.

| Gate | Requirement |
| --- | --- |
| Primary improvement | At least 2% relative reduction in MAE for numeric targets or Brier score for win probability versus the current champion. |
| Evaluation interval | Recent 30-day window, with the same chronological evaluation observations for both candidates. |
| Overall evidence | At least 100 distinct completed games represented in the paired evaluation cohort. Multiple player rows or targets from one game do not count as extra games. |
| Group evidence | At least 100 observations for each predefined blocking group; mandatory groups below the threshold yield insufficient evidence. Other groups remain visible diagnostics. |
| Regression limit | No more than 5% relative worsening in predefined supported groups and secondary metrics, including probability calibration checks. |
| Integrity | Valid data, leakage checks, artifacts, configuration, and reproducible evaluation all pass. |
| Coverage | The challenger cannot obtain promotion by dropping difficult rows; missing required predictions prevent passing the gate. |

For nonnegative loss measures, candidate loss must be at most 0.98 times champion loss for primary improvement and at most 1.05 times champion loss for regression guardrails. If champion primary loss is zero, a candidate cannot establish the required relative improvement and is retained as a challenger. A zero-loss guardrail permits no worsening.

Player rate components are judged on resulting counting-stat predictions, not only rate error. Minutes changes must pass minutes improvement and guardrails on all affected final stat outputs. Evaluate one component change against the current bundle; re-evaluate if another component changes before promotion. Team targets can promote separately with their own evidence.

No evaluation observation may have been used to fit or tune the evaluated artifact. Retraining on the evaluation interval creates a new artifact and invalidates a claim that the new artifact passed that held-out test. Design must specify how the evaluation schedule and training cutoffs satisfy this requirement; a fresh model cannot be assumed to have 30 days of live evidence.

Before sufficient eligible evidence exists, the baseline remains champion. Historical bootstrap evidence must be explicitly labeled, satisfy the same temporal rules, and disclose any narrower historical population. It must not masquerade as live all-roster evidence.

Acceptance: boundary fixtures cover exactly 2%, exactly 5%, zero reference losses, 99 versus 100 games, 99 versus 100 group observations, failed calibration checks, lost coverage, leaked training rows, and incompatible component combinations. Promotion and rejection both produce a decision record with all gate results.

### MODEL-03: Model history and rollback

Every activation, rejection, failed run, and rollback records time, reason, old and new versions, evaluation evidence, and policy version. A promotion changes future forecasts only. A failed deployment retains or restores the previous usable champion; it never edits earlier predictions.

Acceptance: activation is atomic from the predictor's perspective; an incompatible or unreadable artifact cannot replace a functioning model. A recovery drill restores the prior version and preserves all ledger and decision history.

## 10. Awards ladders, v1.5

### AWARD-01: Weekly output

Publish a weekly statistical ladder for MVP, ROY, DPOY, 6MOY, and MIP. Each shows up to five provisionally eligible candidates, rank, movement from the previous published week, eligibility status, main statistical drivers, snapshot cutoff, and model or scoring version. Never fill missing places with invented candidates.

Players absent from the previous published top five display new entrant rather than an invented numerical movement. Show unchanged ranks explicitly. A missed update stays visible with its actual date; do not imply it was published on time. Rankings are statistical estimates, not calibrated probabilities of winning or an official NBA ladder.

### AWARD-02: Eligibility

Rules are versioned by award and season. The CBA's standard 65-game requirement covers MVP, DPOY, and MIP among this project's awards, not ROY or 6MOY. A qualifying game normally requires 20 minutes; at most two appearances of at least 15 but fewer than 20 minutes can count. It also provides a 62-game season-ending-injury route with additional conditions and formal exception procedures. Do not infer medical qualification or an approved exception from statistics alone. [2023 CBA, Article XXIX, Section 6, printed pages 432-438](https://imgix.cosmicjs.com/25da5eb0-15eb-11ee-b5b3-fbd321202bdf-Final-2023-NBA-Collective-Bargaining-Agreement-6-28-23.pdf).

NBA award releases state that 6MOY requires more reserve appearances than starts. Reconfirm applicability for the target season before release. [NBA Sixth Man award release](https://pr.nba.com/tyler-herro-2021-22-kia-nba-sixth-man-of-the-year-award/).

Use verified rookie classification for ROY; draft year alone is insufficient as a product rule. Missing classification produces unknown eligibility. MIP scoring requires prior-season comparison; a missing prior-season baseline is a data limitation, not an invented official exclusion rule.

During the season, distinguish provisional eligibility, threshold achieved, risk, standard threshold unreachable, unknown evidence, and verified official exceptions. A player below 65 early in the season is not automatically ineligible. Show qualifying games accumulated and remaining opportunities; exact risk-label thresholds belong in design. Keep excluded candidates and reasons auditable.

Keep the main top-five ladder of provisionally eligible candidates. Add an eligibility watch for top-five statistical contenders before eligibility filtering who are at risk or cannot reach the standard games threshold, including contenders excluded from the main ladder. Show risk badges on affected main-ladder entries. For each watched contender, show award, statistical rank, snapshot date, qualifying games Q, required threshold T, games needed, verified remaining opportunities R, unknown schedule slots, standard-path reachability, required remaining qualification share where reliable, and any verified official exception status.

Games needed are max(0, T minus Q). The standard path is reachable when Q plus R is at least T; reaching T establishes only that part of eligibility. Unknown required schedule or qualifying-minute evidence produces an unknown assessment. Handle R=0 without division by zero. Do not assert unconditional ineligibility when a sourced official exception could apply.

For a pace diagnostic, use the latest 10 fully observed regular-season roster opportunities, including missed games. Let F count appearances meeting the standard full-minute threshold in that window; projected additional qualifying games are (F / 10) times R. Show a pace warning only when Q plus this projection is below T while the standard path remains reachable. Before 10 supported opportunities, show the required share without a pace warning. Include permitted historical lower-minute allowances in Q; show unused allowances separately and do not assume their future use. Label this conservative scenario as descriptive, with no probability of disqualification or injury forecast.

Acceptance: test award-specific application, minute boundaries, the two-game allowance, reserve/start ties, rookie uncertainty, season changes, early-season provisional status, unreachable thresholds, and sourced exception records. Historical snapshots cannot use later exception decisions or final-season participation to filter the earlier candidate population.

Additional acceptance: excluded leading contenders remain visible; statistical rank and eligibility filtering reproduce independently. Fixtures cover exact reachability and pace boundaries, missing evidence, missed games in the 10-opportunity denominator, fewer than 10 observations, trades, postponed or unscheduled games, no remaining opportunities, and used versus unused lower-minute allowances. Weekly snapshots preserve the evidence available then and cannot change after later participation or exception decisions.

### AWARD-03: Historical validation

Train on earlier seasons and evaluate a later season using snapshots from comparable points in that season. Do not train on future seasons through ordinary leave-one-season-out validation. Include eligible candidates beyond eventual vote recipients to avoid selecting candidates using outcomes.

Report NDCG at five using verified final voting points as relevance and the eventual winner's rank at each snapshot, with per-season results, candidate coverage, and a simple predefined award-specific benchmark. Historical voting results may be labels; displayed scores must not be mislabeled as vote share or winning probability. Compare equivalent points in each evaluation season and use only earlier seasons for any training, tuning, or benchmark selection.

Three recent seasons is the initial player/team collection scope, not a sufficient awards-history commitment. Verify the award-specific labels, historical candidate coverage, permitted access, and feature availability before choosing the awards training period. Basketball-Reference is a candidate from the proposal, not an approved or guaranteed source. If sufficient evidence cannot be collected, keep the affected ladder unreleased and document why.

Acceptance: replay at least three complete chronological evaluation seasons per released award, strictly after any seasons used for training, tuning, or benchmark selection, with multiple comparable within-season snapshots and an auditable candidate population. Publish results per award and disclose small-sample limitations. Three seasons is a minimum review policy, not proof of statistical reliability; weekly snapshots cannot substitute for additional annual evaluation outcomes. Insufficient seasons or required candidate/voting evidence blocks release of the affected award. Exact historical sources, evaluation checkpoints, benchmark and scoring formulas, and metric conventions must be resolved in the v1.5 data audit after launch, before dependent implementation.

## 11. Public dashboard

### UI-01: Views and acceptance

The dashboard is read-only, requires no user accounts, and deploys independently of collection and training. Refresh published data when batch outputs change. Do not advertise in-game tracking in v1.

| View | Required content | Acceptance |
| --- | --- | --- |
| Tonight | Upcoming games, player projections, team forecasts once released, forecast time, availability and history flags. | A numeric prediction is distinguishable from an abstention, pending publication, and stale data. Times identify their timezone. |
| Results | Official predictions versus validated outcomes and target-level errors. | DNP, unresolved outcomes, postponements, invalidations, and corrected outcomes are visibly distinct. |
| Track Record | Accuracy, calibration, baseline comparisons, coverage, periods, sample counts, and filters. | Displayed totals match the evaluation report; small samples and unavailable metrics are explicit. |
| Player | Projection and outcome history, minutes trends, roster context, and explanations appropriate to the model. | History remains attributable to the version that generated each forecast. |
| Model Health | Source health, last successful updates, missed runs, active incidents, accuracy trends, feature and prediction drift. | Stale or unavailable checks cannot display healthy status. No credentials or private operational data are exposed. |
| Model History | Model versions, active components, training events, promotions, rejections, and rollbacks. | Each decision links to its evaluation summary and policy version. |

v1.5 adds awards views and weekly written insights. Filters include date range, target, model version, player, and team where relevant. Charts need readable labels, units, and accompanying numeric summaries. Essential views must work on desktop and mobile, with keyboard navigation and indicators that do not rely only on color.

Acceptance: UI tests cover successful, empty, loading, failed, and stale states; public access cannot mutate records. The dashboard can remain available while a collector or trainer is stopped and can display the last valid snapshot honestly. Hosting, refresh mechanics, and whether an API is needed are design decisions.

## 12. Reuse and modularity

### PLATFORM-01: Domain boundary

Shared platform responsibilities are run tracking, source-adapter contracts, provenance, ledger lifecycle, evaluation interfaces, model artifacts, monitoring, retraining, and promotion records. NBA-specific source parsers, identities, schedules, features, targets, eligibility, and basketball views belong in domain code.

Prefer a small explicit interface over a general plugin framework. A second domain must not require NBA columns or NBA award logic inside platform components. Clash Royale is the later real-world validation of this boundary, not part of the launch implementation.

Acceptance: platform modules do not import NBA domain modules; a small non-NBA test fixture exercises shared prediction, outcome, and evaluation contracts without requiring basketball data.

## 13. Engineering, cost, and learning

### ENG-01: Definition of done

- Every feature includes relevant automated tests, including data validation and leakage tests where applicable.
- Every pull request runs lint, type checks, and tests, links one issue, and remains small enough for owner review.
- Schema changes are migration files; no manual production schema changes.
- Secrets come from environment variables. No secret-bearing fixtures, logs, commits, or browser bundles.
- Read-only public access and constrained runtime write permissions are tested.
- Important decisions are short ADRs in docs/decisions/ after owner review and lock.
- README changes accompany user-visible behavior, setup, commands, and operational changes.
- A task handoff explains the data flow, why the design was chosen, its tradeoff, validation evidence, and one failure scenario.
- Actual commands belong in AGENTS.md only after the toolchain is chosen; do not invent working commands during planning.

### OPS-01: Sustainable operation

Target ongoing operation at $0 using batch processing and free tiers. Any optional recurring spend must be explicitly chosen by the owner and remain within the stated ceiling of $20 per month. Student credits are optional accelerators with documented expiration and an exit path, not permanent funding assumptions.

Retain the season's forecasts, outcomes, model provenance, and decision history. Design must define durable raw-data retention, backup/restore, artifact storage, request budgets, and free-tier capacity checks. There is no requirement for an always-on training or inference server.

GitHub Actions schedules can be delayed or dropped; the system therefore requires deadline detection and the tested local fallback from the critical path. [GitHub Actions schedule behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Acceptance: exercise backup recovery and local publication fallback before declaring the platform operational. Document expected monthly usage, available quotas, and behavior when storage or compute budgets are exhausted. Do not delete the prediction record to hide a capacity failure.

### NOTEBOOK-01: Execute and understand the real workflow

Jupyter notebooks are the owner's main interactive route for running, inspecting, and understanding data engineering, EDA, training, evaluation, and model lifecycle work. They execute real operations and display their results. Shared processing logic lives in tested Python modules used by both notebooks and scheduled jobs. Short exploratory transformations and visualizations may remain in notebooks; reusable production logic belongs in the package.

Use local VS Code notebooks with the same project environment as command-line operations. Select the project kernel explicitly; execution must not depend on global Python or an unrelated Conda environment.

### NOTEBOOK-02: Planned notebooks

| Notebook | Purpose | Delivery |
| --- | --- | --- |
| 01_sources_and_backfill.ipynb | Verify sources, collect history, inspect schemas, validate records, and inspect persisted data. | Phase 0 |
| 02_baseline_and_ledger.ipynb | Follow schedule and roster selection, historical features, baseline projections, publication, and outcome reconciliation. | Phase 1 |
| 03_eda.ipynb | Explore missingness, minutes, production rates, roles, team trends, and season differences. | After launch |
| 04_training_and_evaluation.ipynb | Construct chronological splits, train, compare baselines, inspect errors, and explain projections. | Models v1 |
| 05_monitoring_and_promotion.ipynb | Inspect accuracy and drift, evaluate challengers, and understand promotion or rejection. | MLOps phase |
| 06_awards.ipynb | Explore award history, eligibility, historical ranking evaluation, and weekly movement. | v1.5 |

Keep the first two notebooks compact so they fit the opening-night critical path. Detailed EDA and trained-model notebooks follow after launch. The design may refine organization without removing this coverage.

### NOTEBOOK-03: Cell and output conventions

Use short, clearly labeled cells with one purpose at a time. Each section identifies its purpose and inputs, executes a step, inspects results, and gives a concise interpretation. Explain consequential choices and surprising results without large unfiltered outputs or verbose tutorial text.

Commit concise charts, summary tables, and interpretations. Keep large data and model artifacts outside notebooks, referenced by recorded versions or checksums. Do not commit credentials or sensitive operational output. Walkthroughs execute in order from a fresh kernel with declared inputs. Expensive steps may reuse explicitly identified artifacts only after verifying relevant input and configuration identities; label whether a step executed or reused output and why.

### NOTEBOOK-04: Execution boundaries and acceptance

Default to local or rehearsal data. Production publication is an explicit, clearly labeled operation, disabled in the normal walkthrough, using the same protected path as scheduled jobs. Opening a notebook or executing its default walkthrough cannot publish official forecasts or promote a production model. Development training runs locally; scheduled cloud training requires the representative resource rehearsal in the locked design. A smaller workload or alternative automated runner can address insufficient resources; manual notebook runs do not satisfy the autonomous training requirement.

Acceptance:

- A reader can trace raw input to validated data, features, predictions, evaluation, and lifecycle decisions through notebooks and linked modules.
- Walkthroughs run sequentially from a fresh kernel with explicit inputs and the project environment.
- Notebook and CLI executions match for the same fixture, configuration, and artifact versions, within documented numeric tolerances.
- Default execution uses rehearsal data and cannot create official predictions or change the active production model; explicit production operations retain the same database and lifecycle controls as automation.
- Cells have clear labels and concise output; large artifacts are linked by identity rather than embedded.
- Expensive operations identify execution versus validated reuse and the reason.
- CI verifies shared modules and a lightweight fixture notebook path without live NBA requests or full historical backfill on each PR.

## 14. Release acceptance checklist

### Phase 0 and Phase 1

- [ ] Actual cloud and local access evidence exists; each required source capability is checked separately.
- [ ] Historical seed is reproducible and resumable; missing data is disclosed.
- [ ] Compact source/backfill and baseline/ledger notebooks execute from a fresh kernel on fixtures, match shared CLI logic, and default to rehearsal.
- [ ] Current rosters and schedule are verified; injury integration is accepted or explicitly deferred.
- [ ] All five player targets or explicit abstentions are recorded against expected opportunities.
- [ ] Trusted timestamps and publication cutoff enforcement pass, including concurrent cloud/local execution.
- [ ] Predictions remain immutable while outcomes, statuses, and evaluations evolve separately.
- [ ] DNP, postponement, late outcomes, corrected results, and missing data tests pass.
- [ ] Accuracy and coverage reports reproduce from the stored evidence.
- [ ] Missing-run and source-failure detection, notifications, and fallback are rehearsed.
- [ ] CI, migrations, secret handling, README, and owner understanding meet the definition of done.
- [ ] First regular-season predictions are durably recorded before the opening-game cutoff.

### Remaining v1

- [ ] Team targets and baselines satisfy the same temporal and ledger contracts.
- [ ] Recent training windows are compared through chronological backtests.
- [ ] Monitoring distinguishes bad data, feature drift, and demonstrated performance degradation.
- [ ] Retraining can complete without promotion; every promotion gate and rejection reason is logged.
- [ ] Failed deployment recovery preserves a usable champion and the prediction history.
- [ ] Six public dashboard views reconcile with the underlying evidence and expose stale states.
- [ ] EDA, training/evaluation, and monitoring/promotion notebooks execute shared tested modules with concise labels and reproducible inputs.
- [ ] Domain boundaries and the standalone dashboard deployment are verified.

### v1.5

- [ ] Award-specific sources, historical coverage, and rules pass verification.
- [ ] Weekly top-five ladders, movement, and eligibility states pass fixture tests.
- [ ] Eligibility watch retains leading contenders at risk, applies the approved 10-opportunity pace calculation, and preserves unknowns and original snapshot evidence.
- [ ] Three complete chronological evaluation seasons per award, predefined benchmarks, NDCG at five, winner ranks, and limitations are published.
- [ ] The awards notebook reproduces candidate ranking, eligibility, and validation from recorded inputs.
- [ ] Insights and richer change explanations reference reproducible evidence.

## 15. Review notes and design handoff

The following clarifications were accepted by the owner when this document was locked:

1. All v1 game targets include overtime, and the regular-season record excludes other competition types unless explicitly supported.
2. Benchmarks, shadow predictions, abstentions, and rehearsal records remain distinguishable from the one official forecast. Unknown roster coverage is never counted as complete coverage.
3. Schedule invalidations and corrected outcomes append records; they do not replace original official predictions. Postponements use a new occurrence identity.
4. Awards movement uses new entrant for a player absent from the previous top five. Exceptions require sourced decisions, and fewer than five candidates is acceptable when evidence is incomplete.
5. A component promotion is assessed through the resulting outputs. A model refit using its evaluation data does not inherit the previous artifact's held-out validation.

The locked design supplies freshness limits, team baseline formulas, season-average cold start, backtest and artifact timing, group definitions and calibration guardrails, performance triggers, notification transport, storage and hosting, logical schemas, migrations, and recovery policies. Exact source adapters, pinned dependency compatibility, connectivity, resource capacity, backup delivery, and drift thresholds remain explicit measured verification gates. Awards-specific sources, formulas, and metric conventions are gated by the v1.5 audit and must not delay launch.

Runtime source reliability, a guaranteed request allowance, target-season injury ingestion, and awards-history completeness remain unverified. This PRD requires verification; it does not claim those tasks are complete.

Approval: the owner explicitly locked version 1.0 on October 12, 2026, then locked the design and both amendments on the same date. Version 1.1 incorporates those approved amendments; remaining verification gates are assigned to implementation.

## 16. Version history

| Version | Date | Approval and changes |
| --- | --- | --- |
| 1.0 | October 12, 2026 | Owner locked the original requirements, delivery boundaries, and design handoff. |
| 1.1 | October 12, 2026 | Owner locked the notebook and awards amendments with the technical design. Added NOTEBOOK-01 through NOTEBOOK-04, incorporated the eligibility watch and 10-opportunity pace scenario, strengthened AWARD-03 to three evaluation seasons with NDCG at five and winner ranks, and updated acceptance checklists and handoff references. |
