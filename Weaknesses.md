# Baseline: known weaknesses and improvement register

Status: LOCKED by the project owner on October 12, 2026. This approves the register and its maintenance process, not the unapproved design proposals it references.

Version: 1.0

Prepared: October 12, 2026. Last reviewed: October 12, 2026. Last updated: October 14, 2026.

## Purpose and evidence

Track limitations identified during planning and development, their effect on users, and what would justify addressing them in a later version. This register supports honest reporting and prioritization; it does not authorize new scope or excuse a failed acceptance criterion.

The project is currently in planning. The entries below describe documented design limitations or risks to verify, not observed production incidents or measured model failures. Mitigations are planned unless an entry links to implementation evidence. The design and both PRD amendments were locked on October 12, 2026; their verification gates remain outstanding.

Sources: [locked PRD](docs/PRD.md), [critical path](docs/critical-path.md), [locked design](docs/design.md), [notebook amendment](docs/PRD-notebook-amendment.md), and [awards amendment](docs/PRD-awards-eligibility-amendment.md).

## Rules for maintaining this register

- Use stable IDs. Each entry records evidence, impact, current mitigation, an improvement direction, review timing, and closure evidence.
- Add measured findings with the affected version, date, issue/PR, and reproducible report or fixture. Label hypotheses as hypotheses.
- Update affected entries during PR review; do not create a new document for each discovery. The owner prioritizes future work through issues.
- Existing required work stays in its delivery phase. A release blocker cannot be reclassified as future improvement to meet a deadline.
- Future improvements below are candidates, not promises or new approved dependencies. Material scope or policy changes need an ADR and owner approval.
- Close an entry only with verification evidence. Retain its history and distinguish resolved, mitigated, and accepted limitations.

All initial entries are open. Local launch issue specifications now exist; GitHub issue/PR numbers remain unassigned until execution creates the repository and publishes the tasks.

## Required gates that cannot be deferred

| Gate | Required before |
| --- | --- |
| Verified schedule, status, roster, and historical data capabilities through an accepted cloud or local path. Injury integration is either accepted or explicitly deferred. | Phase 0 completion. |
| Reproducible prior-only features and roster cohorts, explicit abstentions, validated outcomes, and honest coverage. | Official player baseline launch. |
| Immutable ledger, restricted permissions, duplicate-run protection, timely publication receipts, and no backdating. | Official forecast publication. |
| Source health, missed-run detection, working notifications, fallback rehearsal, and verified independent backup/restore under the approved policy. | Phase 1 launch. |
| Migration files, PR lint/type/test checks, relevant validation and leakage tests, and current README instructions. | Each affected implementation PR. |
| Adequate evaluation populations, valid artifacts, measured runner feasibility, and tested activation/rollback. | Automated model promotion and retraining release. |
| Verified historical labels, candidate coverage, eligibility rules, and chronological validation. | Each awards ladder release. |

## W-01: Baselines respond slowly to changing player roles

- **Evidence:** The approved launch model averages up to 10 previous appearances; it has no explicit participation or role-change model. Team baselines use fixed Elo settings and recent scoring/conceding averages.
- **Impact:** A bench player may receive a positive forecast despite a likely DNP. Trades, rotation changes, rest, and returning players may produce persistent errors. Their size is not yet measured.
- **Current mitigation:** Show history and availability flags, retain the full roster cohort, score confirmed DNP as zero, and report errors and coverage honestly.
- **Improvement / timing:** During models v1, evaluate minutes and rate models with justified context; consider participation modeling if measured errors warrant it. Tune team settings only on earlier development data.
- **Future experiment recorded October 14, 2026:** The owner approved retaining a team availability experiment for after launch, once the approved Elo and recent-scoring benchmarks are operational. Hypothesis: known pregame absences, plausible replacement roles, reallocated expected minutes, and opponent context can improve team score/margin/total forecasts. Count replacements' additional contribution rather than adding their full existing projection again. Unknown availability remains unknown; scoring contributions are not causal player-impact estimates. Require timestamped availability/roster evidence, leakage tests, a concise EDA/training notebook using shared operations, and chronological comparison against the unchanged benchmarks. If historical evidence is insufficient, collect prospective snapshots and run in shadow mode. A higher expected score gives a winner lean, not a calibrated probability. This approval records a candidate, not implementation, promotion, or a Phase 0/1 dependency; any production change needs a reviewed design and the existing promotion gates.
- **Closure evidence:** Chronological comparisons and live slices demonstrate improvement, including DNP and low-minute players, without reduced coverage or leakage. Keep the original baselines for comparison.

## W-02: Players without usable NBA history receive no numeric forecast

- **Evidence:** The locked baseline abstains when history is absent or the rate denominator is invalid; fewer than 10 usable appearances are allowed with a flag.
- **Impact:** Rookies and other new players reduce coverage. Estimates based on very little history may be unstable.
- **Current mitigation:** Publish explicit abstentions and history counts; retain these players in coverage denominators.
- **Improvement / timing:** After launch, test population/role priors or other defensible fallback estimates. Extra data sources require separate access and provenance checks.
- **Closure evidence:** A cold-start evaluation shows useful error and coverage behavior on players with genuinely limited prior evidence. No future career statistics enter the fallback.

## W-03: Availability coverage may be incomplete or too early

- **Evidence:** [SOURCE-001, issue #3](https://github.com/Bixzare/baseline/issues/3) has no verified target-season automated injury adapter and recommends explicit deferral for owner review; that decision is not yet accepted. The publication target precedes tip-off by two hours.
- **Impact:** Forecasts may miss late injury news or lineup changes even when publication is correct.
- **Current mitigation:** Unknown availability remains visible. Preserve all report versions if ingestion is adopted; official forecasts remain immutable.
- **Improvement / timing:** Evaluate injury ingestion after launch if deferred. Later forecasts would require a separate, explicitly approved forecast-horizon policy and separate evaluation records.
- **Closure evidence:** Source availability, collection timing, parser accuracy, and replay tests support the feature; measured benefit justifies its operational cost. Never replace an earlier official prediction.

## W-04: Historical inputs cannot fully establish what was known then

- **Evidence:** Historical backfill collected now may contain later corrections. Participant-only records may omit roster members who did not play. See PRD DATA-02 and design Sections 9-10.
- **Impact:** Historical performance can differ from live all-roster performance. Complete historical injury, roster, or revision evidence may be unavailable.
- **Current mitigation:** Label availability assumptions, exclude indefensible features, preserve live snapshots, and prevent participant-only results from establishing all-roster promotion evidence. On October 12, 2026, the owner approved retaining the official baseline while collecting prospective evidence and running candidates in shadow mode when historical reconstruction is insufficient; implementation remains pending.
- **Improvement / timing:** Investigate defensible cohort reconstruction during model development and accumulate prospective evidence from launch onward.
- **Closure evidence:** Documented cohort and timestamp coverage supports the claimed evaluation. Irrecoverable historical gaps stay disclosed as accepted limitations rather than being filled with invented evidence.

## W-05: Separate predictions do not describe a joint game outcome

- **Evidence:** The plan composes minutes and rates, fits team targets separately, and initially publishes point estimates. Elo and the scoring baseline can favor different winners.
- **Impact:** Player totals need not add up to team totals; separate minutes/rate expectations can introduce composition error. Point estimates do not express uncertainty.
- **Current mitigation:** Evaluate final composed outputs, retain model identities, check valid value ranges, and explain disagreements. Do not silently adjust stored outputs for presentation.
- **Improvement / timing:** After models v1, assess coherent team/player reconciliation and calibrated prediction intervals when error analysis supports them.
- **Closure evidence:** Held-out final-output errors and interval coverage/width improve under a versioned evaluation. Any reconciliation preserves the original forecast identity and is evaluated as a new model.

## W-06: The evaluated model artifact has a training-data lag

- **Evidence:** The confirmed design fits before a recent 30-day holdout and deploys that exact artifact without refitting.
- **Impact:** Fitted parameters omit the latest evaluation month, although features can still use prior games available at each forecast cutoff. Adaptation to new roles or season conditions may be slower.
- **Current mitigation:** Expose training cutoffs and evaluate on recent snapshots; retain the champion when evidence is insufficient.
- **Improvement / timing:** After the initial promotion loop works, assess prospective shadow evaluation for newer artifacts.
- **Closure evidence:** A reviewed policy establishes adequate unseen evidence for the exact deployed artifact. Training on the holdout and deploying a refit is not a valid resolution.

## W-07: Promotion thresholds are operational policies, not statistical certainty

- **Evidence:** The locked 2% improvement, 5% regression, and minimum-sample gates are starting policies. Five fixed calibration bins were approved October 12, 2026; rolling evaluation windows overlap.
- **Impact:** Small effects may be noisy, sparse groups can delay promotion, coarse bins can hide probability errors, and repeated comparisons can overstate evidence if treated as independent.
- **Current mitigation:** Report counts, groups, coverage, and every decision; freeze evaluation inputs and policy; do not tune against promotion results or waive missing-group gates.
- **Improvement / timing:** During evaluation development, assess sensitivity to thresholds and report uncertainty accounting for observations from the same game. Review policy prospectively as evidence grows.
- **Closure evidence:** Reproducible historical and prospective analysis supports the revised policy, with separate development/test use and retained prior decisions. No claim of certainty from passing a numerical threshold alone.

## W-08: Collection and publication depend on fallible sources and runners

- **Evidence:** [SOURCE-001's report](docs/source-verification.md) records HTTP 403 on the CDN schedule candidate from GitHub Actions and the cloud-development runner on October 14, 2026. Each stopped after one request. October 15 local history tests with Baseline's honest headers timed out. A later owner-approved stock-client notebook diagnostic returned HTTP 200 and validated 636 player rows and 60 team rows. This establishes sample access, not production source acceptance; ongoing header policy, full history coverage, and status/final/roster gates remain unresolved. Local fallback requires an awake, connected machine and observed working access.
- **Impact:** Source or runner failures can leave missing forecasts and stale public data. Moving to another cloud does not establish source accessibility.
- **Current mitigation:** Bounded probes retain immutable raw bytes/manifests and fail on denial or invalid content. Cloud evidence was downloaded and checksummed locally; synthetic fixture tests do not establish source access. Obtain local evidence or an owner-approved permitted-source decision before dependent collection; do not reroute the same failed request as if it were verified. Scheduling, fallback rehearsal, and public coverage remain later implementation gates.
- **Improvement / timing:** After launch, use observed incidents to decide whether a permitted alternative source or more reliable runner is worth its cost.
- **Closure evidence:** Recorded failure/recovery drills and operating history meet the agreed reliability target. Essential source access and working fallback remain launch gates, not future fixes.

## W-09: Backups and recovery still depend on the owner's machine

- **Evidence:** The backup policy approved October 12, 2026 uses daily local exports into an existing cloud-synced folder, with an alert when the latest verified off-device backup is more than 24 hours old. Backup and restore behavior remain unimplemented and unverified.
- **Impact:** Sleep, disconnection, or failed synchronization can delay backup. A database loss may remove recent records absent from the last completed independent backup.
- **Current mitigation:** Verify remote upload, artifact checksums, backup age alerts, and restoration into an isolated database. Report unrecoverable gaps without reconstructing pregame timestamps.
- **Improvement / timing:** After launch, reassess direct cloud backup delivery or a shorter backup interval if measured operation cannot sustain the agreed target.
- **Closure evidence:** A recovery drill using the off-device copy demonstrates the required recovery point and documents restoration time. An existing local export alone is insufficient.

## W-10: Capacity and automated training feasibility are not yet measured

- **Evidence:** The architecture targets free services, with historical archives partly local. Representative database growth, artifact volume, runner memory, and training time have not been measured.
- **Impact:** Growing evidence or training workloads may exceed the available resources, and local-only execution may depend on machine availability.
- **Current mitigation:** Measure before activation, retain only necessary cloud partitions, deduplicate identical raw bodies, and preserve official evidence. Student benefits remain optional.
- **Improvement / timing:** Revisit storage and compute at measured capacity thresholds and before each substantial model/domain expansion.
- **Closure evidence:** Representative workloads fit the documented budget and retention policy, and retraining runs unattended on the selected runner. Extra credits require an expiry and replacement plan; manual notebook clicks do not satisfy autonomous training.

## W-11: Ledger immutability does not protect against the database owner

- **Evidence:** The approved approach restricts runtime roles, while privileged migration/administrative access remains necessary. Design Section 7 states this boundary.
- **Impact:** The system can demonstrate protected application behavior but cannot claim independent, tamper-proof proof against its own administrator.
- **Current mitigation:** Separate credentials, test runtime mutation denial, preserve publication receipts, version migrations, and keep independent backups.
- **Improvement / timing:** If independent public auditability becomes a requirement, evaluate externally stored attestations or immutable exports under a separate design.
- **Closure evidence:** A defined threat model and tests demonstrate the stronger guarantee. Database runtime controls alone do not establish it.

## W-12: Awards rankings have limited evidence and uncertain eligibility context

- **Evidence:** Awards provide annual labels; historical candidate coverage and exact release datasets still require verification. The eligibility pace diagnostic approved October 12, 2026 extrapolates participation from 10 observed roster opportunities; it is not yet implemented or validated.
- **Impact:** Rankings may be unstable across seasons, and statistical standing does not establish voter intent. A pace warning cannot predict injury recovery or an official exception.
- **Current mitigation:** Keep statistical rank, eligibility, and pace separate; show qualifying games and remaining opportunities; retain at-risk leading contenders; require chronological validation before release.
- **Improvement / timing:** During v1.5 and later revisions, expand verified seasons, compare award-specific benchmarks, and evaluate the diagnostic against later observed participation.
- **Closure evidence:** Published validation includes season counts, candidate coverage, eligibility fixtures, and limitations. Weekly snapshots do not count as independent annual award outcomes, and ladder scores are not winning probabilities.

## W-13: Reuse outside NBA is designed but not yet demonstrated

- **Evidence:** [BOOT-001](https://github.com/Bixzare/baseline/issues/1) enforces static platform imports recursively, with permitted shared/synthetic imports and rejected NBA imports in temporary fixtures. Shared prediction/outcome/evaluation contracts do not exist yet; Clash Royale is a later deployment.
- **Impact:** NBA-specific assumptions may remain undiscovered until a real second domain is integrated.
- **Current mitigation:** Prevent platform imports from NBA modules and exercise shared contracts with a small synthetic non-NBA fixture.
- **Improvement / timing:** Test the boundary with the separately approved Clash Royale deployment, after the NBA platform is stable.
- **Closure evidence:** The second domain reuses ledger, artifacts, evaluation, and operations without NBA-only fields or a broad platform rewrite. A synthetic fixture alone does not prove full reuse.

## W-14: Automatic final-result correction checks have a bounded horizon

- **Evidence:** [OUTCOME-001](docs/issues/OUTCOME-001-final-results-and-versioned-reconciliation.md) initially rechecks seven days of completed games plus unresolved IDs under a measured request budget. This is an approved workload policy, not observed NBA correction behavior or an implemented collector.
- **Impact:** Corrections to older resolved games may remain undiscovered until an explicit ID/range reconciliation run. Displayed actuals and errors reflect the saved source revision, not a guarantee that no later correction exists.
- **Current mitigation:** Preserve every source/outcome/report version, show observation/revision times, provide explicit older-game reconciliation, and never alter forecasts when labels change.
- **Improvement / timing:** After launch, measure actual correction timing and request cost before extending automated sweeps or adding another permitted source.
- **Closure evidence:** Recorded correction coverage and a tested revised workload policy address the measured gap. Increasing a horizon without source evidence does not prove completeness.

## W-15: Bulk historical data contains unresolved source gaps

- **Evidence:** The [pinned comparison](docs/dataset-comparison.md) found Eoin 525 team ID 0 rows, blank player-team IDs, missing minutes/nonparticipation ambiguity, varying minute precision, and older-season coverage gaps. Internal row counts cannot prove exact game completeness. Wyatt 238 does not establish a recent player seed.
- **Impact:** Silent filtering or guessed repairs could bias coverage, rates, historical evaluation, and later model promotion.
- **Current mitigation:** SOURCE-001 is merged. DATA-001's local inventory matches all 1,230 game IDs; normalization retains 32,176 player and 2,460 team rows, quarantines 133 player and two team records, and preserves raw bytes. See the [seed report](docs/seed-backfill.md). Seed acceptance remains gated; no repairs or historical pregame cohorts are invented.
- **Improvement / timing:** DATA-001 normalizes the reviewed 2025-26 seed and records unresolved cases. Repair earlier seasons only before they enter later training. Injury reconstruction and all-time comparison remain deferred.
- **Closure evidence:** Exact coverage and source mapping checks, defensible DNP/unknown handling, replay/leakage tests, and reviewed seed acceptance. A weakness entry cannot waive a release gate.

## W-16: Hosted persistence has not been provisioned or verified

- **Evidence:** On October 25 the owner confirmed that the dedicated Supabase project is not created. DB-001's real Postgres 17.11 fixture tests and isolated export/restore passed locally. Hosted major version, plan/region/limits, direct/session access, actual API roles and TLS remain unverified.
- **Impact:** Local success cannot establish production database or private-artifact readiness.
- **Current mitigation:** Separate migration/runtime credentials, restricted application schemas, required real Postgres CI, explicit hosted review/check gates. No administrative credential enters ordinary jobs.
- **Improvement / timing:** Create and verify the Free project before hosted activation or dependent import. Align CI major version to observed settings.
- **Closure evidence:** Owner-reviewed hosted migrations, Windows and Actions restricted/TLS checks, real permission denials and an isolated supported recovery test. This remains a release gate.

## Adding a development finding

Use the next unused W-ID and record: title; first observed date and affected version; evidence/issue link; user impact; current mitigation; proposed action and review trigger; release-blocking status; and closure evidence. Keep the explanation concise. Do not put secrets, personal backup paths, or raw private logs here.

Review affected entries during each related PR and review the open list before a release. Routine evidence/status updates follow normal owner diff review; changes to product requirements still follow the ADR and lock process.
