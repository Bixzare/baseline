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

- **Evidence:** [SOURCE-001's report](docs/source-verification.md) records HTTP 403 on the CDN schedule candidate from GitHub Actions and the cloud-development runner on October 14, 2026. Each stopped after one request. October 15 local history tests with Baseline's honest headers timed out. A later owner-approved stock-client notebook diagnostic returned HTTP 200 and validated 636 player rows and 60 team rows. This establishes sample access, not production source acceptance; the owner approved bounded unchanged defaults for local inventory/repairs on October 25. Exact 2025-26 game IDs matched a separate NBA inventory, but 135 records remain quarantined. Seed acceptance and status/final/roster gates remain unresolved. Local fallback requires an awake, connected machine and observed working access.
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

- **Evidence:** LEDGER-001 tests real runtime/anonymous write denials and a nonlogin insert-only publication owner. Deferred foreign keys enforce one matching child per official slot under concurrent writers. Privileged migration/administrative access still exists; design Section 7 states this boundary. Actual deadline/visibility publication functions arrive in LEDGER-002.
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

- **Evidence:** BOOT-001 enforces static platform imports. DB-003 tests generic second-domain events; MODEL-001 tests generic prepared entries; LEDGER-001 commits a synthetic card-game signed target through the same model/bundle/slot tables. A real second-domain deployment and shared outcome/evaluation lifecycle remain unimplemented.
- **Impact:** NBA-specific assumptions may remain undiscovered until a real second domain is integrated.
- **Current mitigation:** Prevent platform imports from NBA modules and exercise shared contracts with a small synthetic non-NBA fixture.
- **Improvement / timing:** Test the boundary with the separately approved Clash Royale deployment, after the NBA platform is stable.
- **Closure evidence:** The second domain reuses ledger, artifacts, evaluation, and operations without NBA-only fields or a broad platform rewrite. A synthetic fixture alone does not prove full reuse.

## W-14: Automatic final-result correction checks have a bounded horizon

- **Evidence:** [OUTCOME-001](docs/issues/OUTCOME-001-final-results-and-versioned-reconciliation.md) initially rechecks seven days of completed games plus unresolved IDs under a measured request budget. The fixture-tested reconciliation implements this workload policy; actual NBA correction behavior and coverage remain unverified.
- **Impact:** Corrections to older resolved games may remain undiscovered until an explicit ID/range reconciliation run. Displayed actuals and errors reflect the saved source revision, not a guarantee that no later correction exists.
- **Current mitigation:** Preserve every source/outcome/report version, show observation/revision times, provide explicit older-game reconciliation, and never alter forecasts when labels change.
- **Improvement / timing:** After launch, measure actual correction timing and request cost before extending automated sweeps or adding another permitted source.
- **Closure evidence:** Recorded correction coverage and a tested revised workload policy address the measured gap. Increasing a horizon without source evidence does not prove completeness.

## W-15: Bulk historical data contains unresolved source gaps

- **Evidence:** The [pinned comparison](docs/dataset-comparison.md) found Eoin 525 team ID 0 rows, blank player-team IDs, missing minutes/nonparticipation ambiguity, varying minute precision, and older-season coverage gaps. Internal row counts cannot prove exact game completeness. Wyatt 238 does not establish a recent player seed.
- **Impact:** Silent filtering or guessed repairs could bias coverage, rates, historical evaluation, and later model promotion.
- **Current mitigation:** October 29 inventory still matches all 1,230 game IDs. Locked ADR 0018 supports 129 source-confirmed inactive repairs, three positive zero-minute appearances and two invalid extra-team exclusions. The new candidate retains 32,308 player and 2,460 team rows, with one orphan player record still unresolved. Exact compact-window review and seed acceptance remain pending; no historical pregame cohorts are invented. See the [candidate review](docs/approvals/2026-10-29-compact-seed-review.json).
- **Improvement / timing:** DATA-001 normalizes the reviewed 2025-26 seed and records unresolved cases. Repair earlier seasons only before they enter later training. Injury reconstruction and all-time comparison remain deferred.
- **Closure evidence:** Exact coverage and source mapping checks, defensible DNP/unknown handling, replay/leakage tests, and reviewed seed acceptance. A weakness entry cannot waive a release gate.

## W-16: Hosted persistence verification remains incomplete

- **Evidence:** Through October 28, reviewed migrations 0001 through 0010 are applied to the Free eu-west-1 project on Postgres 17.11. Windows runtime client TLS/verify-full, denied owner/DDL access and backend Auth sign-in/refresh pass. Actual Storage create/read and explicit write denials pass, and owner-locked ADR 0016 policy/byte evidence verifies delete/move/bucket protection on Windows. Strict status-only results remain inconclusive; the corroborated checks also passed in actual Actions. Public signup was disabled and verified on October 28; existing identities still authenticate and refresh. Backend pg_stat_ssl is false behind the pooler; Initial Free allowances/usage and an independently downloaded local restore are verified; source acceptance, season growth and full recovery/provider setup remain gates. See [setup evidence](docs/supabase-setup-status.md).
- **Impact:** Local success cannot establish production database or private-artifact readiness.
- **Current mitigation:** Separate migration/runtime credentials, restricted application schemas, real Postgres CI and explicit hosted gates. DB-002 tests actual policies against provider relation/claim fixtures and mocks HTTP faults; this does not verify real Auth/Storage APIs. No administrative credential enters ordinary jobs. See [artifact verification](docs/artifact-storage.md).
- **Improvement / timing:** Create and verify the Free project before hosted activation or dependent import. Align CI major version to observed settings.
- **Closure evidence:** Owner-reviewed hosted migrations, Windows and Actions restricted/TLS checks, real permission denials and an isolated supported recovery test. This remains a release gate.

## W-17: Original raw upload limit resolved; complete seed lineage still gated

- **Evidence:** Owner-locked ADR 0017 preserves 438,321,084 original bytes as seven immutable compressed parts totaling 60,615,087 bytes. Actual Windows, independent OneDrive restoration and main-branch Actions run 40920359705 reconstructed the original hashes. The raw size obstacle is resolved.
- **Impact:** Raw reconstruction alone does not verify the new candidate's repair overlays, complete backup or accepted facts.
- **Current mitigation:** Keep exact source/physical identities and owner acceptance separate. The October 29 compact plan selects 5,447 player rows, 1,696 team sides and 848 games; it remains blocked pending exact candidate review.
- **Improvement / timing:** Verify all candidate/repair lineage independently from cloud, then complete the accepted seed backup and daily execution before activation.
- **Closure evidence:** Raw archival is verified. Broader DB-003 and backup gates remain explicit; no seed acceptance or fact import is implied.

## W-18: Production publication has not been rehearsed against hosted inputs

- **Evidence:** LEDGER-002 uses real Postgres with fixture sources and mock Storage; the two-transaction protocol and guarded roles are tested. Supabase schemas and restricted Windows identities are configured; accepted live input routing and a complete hosted publication rehearsal remain absent.
- **Impact:** This does not prove a real complete roster fits the payload/transaction limits or that hosted roles/functions behave identically. No production forecasts exist from this rehearsal.
- **Current mitigation:** Refuse readiness claims; keep explicit source/hosted/backup gates, bounded payloads, exact-byte hashes, immutable reservations and separate receipts.
- **Improvement / timing:** Verify the actual project major, source generations, cohort size, latency, permission denials and operational recovery before activation.
- **Closure evidence:** Reviewed hosted readback/denials and a later approved future-slate run with a timely receipt. This is a release gate.

## W-19: Ongoing source routing is not yet accepted

- **Evidence:** COLLECT-001 has no accepted default routes. Fixture tests prove policy, validation, persistence and transitions; they do not resolve the prior CDN denial or establish current roster coverage.
- **Impact:** Nightly collection and real publication cannot run until capability/environment routes are reviewed and measured. Local-only routes require an awake machine and fresh uploaded evidence.
- **Current mitigation:** Empty routing fails closed, no cloud stats requests, exact request/parser/environment identities, source health and bounded work. Suspended/unsupported states remain pending.
- **Improvement / timing:** Accept actual permitted schedule, status, roster and final capabilities with generation semantics, coverage and request/runtime evidence before operations activation.
- **Closure evidence:** Actual accepted cloud/local rehearsals, fresh complete roster readback and measured budgets. This is a release gate.

## W-20: Final participation semantics and correction coverage need live verification

- **Evidence:** OUTCOME-001 tests source-confirmed DNP, missing rows, partial targets, repeated/corrected facts and parser/config revisions on fixtures. No final adapter is enabled or rehearsed against an accepted real source.
- **Impact:** Actual player/DNP completeness and later correction timing remain unknown; no fixture result can support a season accuracy claim.
- **Current mitigation:** Unknown outcomes stay unscored, original cohorts/forecasts persist, source bytes and semantic versions remain linked, and default routes refuse execution. Recheck seven days plus unresolved live IDs; use explicit IDs/ranges for older corrections.
- **Improvement / timing:** Accept real final-source identities, precision, participation and calendar semantics, then record regular-season completeness, cost and correction evidence before trusted reconciliation.
- **Closure evidence:** Reviewed live-source rehearsal, verified role/artifact readback and honest outcome coverage. This is a release gate.

## W-21: Scheduled operations are not production reliability evidence

- **Evidence:** OPS-001 cloud fixture run 40496627455 passed both jobs and failure drill 40498186657 failed the dispatcher as intended. The owner confirmed GitHub failure notification receipt. OPS-002 ran an actual disposable Windows task with exit 0 and queued notice, but the owner saw no desktop notification, so that delivery drill failed. Accepted local uploads and unattended production recovery remain unverified. See [local recovery](docs/local-recovery.md).
- **Impact:** Merged YAML or cron timing cannot guarantee a timely forecast. GitHub can delay/drop work and an asleep local machine cannot recover it.
- **Current mitigation:** Explicit activation/readiness gates, no false disabled heartbeat, per-stage/operation audit, stable alerts, offline logs, source denial stop, session coordination and protected ledger deadlines. Persistent Windows tasks and production remain disabled. Provider object usage and actual account limits stay visibly unverified; registered objects are only an estimate.
- **Improvement / timing:** Observe manual/unattended runs, verify owner notification and independent Windows recovery, then backup readiness before activation.
- **Closure evidence:** Actual intended-environment failure/recovery traces and timely committed receipts on an approved future slate. This is a release gate.

## W-22: Independent backup delivery is not verified

- **Evidence:** BACKUP-001 preserves a real Postgres fixture snapshot, original ledger/receipt rows and checksummed objects through isolated restoration. Its remote boundary is synthetic. OneDrive OAuth/folder mapping, native hosted export and actual remote readback are not configured.
- **Impact:** Local complete sets and passing restore tests do not provide a verified off-device recovery point. BACKUP-001 and launch readiness remain open.
- **Current mitigation:** Default-off CLI/task, independent readback location, real OneDrive backend check, exact file/hash inventory, conservative capacity checks, bounded operations and no automatic deletion. OPS-002 continues to report backup unverified.
- **Improvement / timing:** Configure the selected OneDrive account/folder and supported private export route, then download and restore a real set before activation.
- **Closure evidence:** Actual remote hash readback, isolated restore and daily execution with a represented cutoff under 24 hours. This is a release gate. See [backup operations](docs/backups.md).

On October 28 the matching personal OneDrive was authenticated read-only and a
current-state application export was independently downloaded/restored: 27 tables
and one registered artifact matched, runtime mutation was refused and the test
target was removed. This closes the current-state delivery uncertainty only;
W-22 remains open for full historical inventory and daily execution. No partial
rehearsal was logged as a complete launch backup or production heartbeat.

## Adding a development finding

Use the next unused W-ID and record: title; first observed date and affected version; evidence/issue link; user impact; current mitigation; proposed action and review trigger; release-blocking status; and closure evidence. Keep the explanation concise. Do not put secrets, personal backup paths, or raw private logs here.

Review affected entries during each related PR and review the open list before a release. Routine evidence/status updates follow normal owner diff review; changes to product requirements still follow the ADR and lock process.

### October 28 seed follow-up

The verified quarantine contains 135 rows in 20 games. Zero counts, blank team
identities, and empty participation comments cannot establish DNP or a historical
pregame roster. One successful stock nba_api box-score response still leaves its
target player's participation unknown. Keep the seed import blocked pending
explicit resolution; the read-only audit in docs/seed-backfill.md identifies the
records and does not repair them. A local historical CDN sample was denied and
was not retried; that result does not establish current cloud access.

Raw-file capacity remains a release gate. Lossless gzip measured 61 MB versus
438 MB original input; locked ADR 0017 now implements bounded verified parts. Actual Windows
readback verified all originals after a failed rehearsal. Independent OneDrive
readback and isolated restoration now verify all four raw originals. Cloud
Actions verification subsequently passed from the owner-selected main branch on
October 29 (run 40920359705), with the environment allowlist unchanged. Daily
independent backup of the complete historical archive remains unverified. MODEL-001 and LEDGER-001 depend on an
accepted seed plus prospective source evidence, not their successful fixtures.


### October 29 adjudication follow-up

Locked ADR 0018 keeps the single remaining orphan unknown, rather than inferring
DNP. Sixteen strictly later played appearances exist; the compact seed selects
ten after that date. This may support exact compact acceptance only, not full
historical completeness or historical full-roster evaluation. The draft owner
review remains non-authorizing. Repair evidence retention creates no NBA facts.

DB-001 and DB-002 hosted acceptance checks now pass on Windows and actual main
Actions, and their issues are closed. This narrows W-16's remaining work to source,
season capacity and complete recovery gates; it does not activate production.


### October 29 Windows notice follow-up

The replacement helper now processes Windows UI messages within a ten-second
bound and reports shell acknowledgment separately from visibility. An actual
disposable task exited 0 and reported a shown event, then was removed. Owner
confirmation is pending. W-21 remains open for that confirmation, unattended
recovery and accepted sources; no persistent task or production flag was enabled.
