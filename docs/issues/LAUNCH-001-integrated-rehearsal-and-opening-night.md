# LAUNCH-001: Verify integration and supervise opening-night publication

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Phase: 1. Priority: final launch gate. Dependencies: BOOT-001, SOURCE-001, DATA-001, DB-001/002/003, MODEL-001, LEDGER-001/002, COLLECT-001, OUTCOME-001, EVAL-001, OPS-001/002, and BACKUP-001 implemented and owner-reviewed. Session estimate: 2 to 3 agent hours of verification/report work, plus at least one actual unattended nightly/dispatcher cycle and opening-night supervision. This is not a promise that earlier setup gates will fit the calendar.

## Goal and scope

Verify the whole launch path, record actual evidence, and enable approved production schedules only when required gates pass. Then supervise the first official regular-season publication. Planning approval is not a passing launch checklist. Deadline: first game October 20, 2026 at 19:00 UTC (21:00 UTC+2); target initial publication 17:00 UTC (19:00 UTC+2), with the protected 15-minute cutoff still enforced.

Read AGENTS.md and skills `hoop-data-quality`, `hoop-postgres`, `hoop-python-testing`, and `hoop-notebooks`. Contracts: [critical path](../critical-path.md), [publication decision](../decisions/0004-enforce-immutable-pregame-publication.md), [scheduler decision](../decisions/0005-schedule-batch-jobs-with-local-recovery.md), and [storage/recovery](../decisions/0003-store-operational-records-and-versioned-artifacts.md). No team model, dashboard, training, awards, new source, or paid resource may enter this session.

## Readiness evidence

Maintain one dated readiness report with requirement, status (verified/failed/unverified), actual command/run/fixture, evidence IDs/links, and unresolved limitation. Do not tick a box from a locked issue or a configured service alone.

- [ ] Owner-owned repository/project identity, Free plan/actual allowances, restricted runtime versus setup credentials, TLS/connectivity from Windows and the actual cloud runner, applied migration checksums, and PR CI are verified.
- [ ] Accepted schedule/status/roster/final/history adapters are verified by capability/environment. Phase 0 explicitly accepts availability or records owner-approved deferral. Confirm the actual season opening schedule against accepted data; report any conflict with the assumed October 20, 19:00 UTC deadline rather than silently shifting it.
- [ ] Accepted local 2025-26 archive, compact hosted seed, source coverage/unknowns, portable artifact references, and both concise launch notebooks pass checks. Rehearsal/preseason evidence is separate from regular-season history/track record.
- [ ] Five-target preparation includes the whole saved roster, explicit abstentions, cutoff-eligible facts, verified snapshots, and immutable model/bundle identity. Unresolved recent history does not disappear.
- [ ] Protected whole-batch publication, separate-transaction receipts, exact/conflicting retries, transaction crossing cutoff, source/roster freshness, and mutation/forgery denial are verified on real Postgres with actual roles.
- [ ] Schedule corrections, postponement/upstream-ID reuse, earlier starts, cancellation, unknown suspension, final/DNP reconciliation, and corrected report versions preserve original predictions and show exclusions/unresolved coverage.
- [ ] Actual manual cloud runs and one unattended nightly/dispatcher cycle are observed, with source/run completion evidence and verified owner notification. Do not rely only on fixture or manually clicked runs.
- [ ] Independent Windows watchdog/local-only source production and fallback recovery are rehearsed in the intended session; machine awake/network/login availability is confirmed for opening day. Cloud/local races preserve one official decision.
- [ ] Complete off-device backup, actual remote readback, isolated restore, original IDs/times/hashes, represented cutoff under 24 hours, and age alerts are verified. No production fixture forecast was inserted to test restoration.
- [ ] Capacity measurements, configured limits/thresholds, redaction, exact operational commands, disable/recovery instructions, README/AGENTS.md, and known weaknesses are current.

## Unattended rehearsal and failure drill

Use the identical shared commands and workflow/task definitions with a separate disposable database for fixture or preseason forecast publication. Bind the rehearsal configuration to that target; production database identity must be refused. Actual production source collection/readback can be verified separately without fake forecasts.

Exercise at least one unattended nightly cycle and a due-game dispatcher window, including no-work runs, a valid receipt, unknown/abstained player, final/DNP outcome, corrected result/report, source failure, stale roster, duplicate cloud/local attempt, and lost commit response. Use recorded or labeled fixtures when a real event cannot be observed; distinguish observed endpoint access from simulated event behavior. Record what the final-source sample does and does not establish for regular-season operation.

Stop/disable cloud work deliberately in the rehearsal and observe independent watchdog alert/recovery before cutoff. Rehearse wake/offline/database failure, exact cutoff refusal, and failed backup upload. Production clock/permission checks cannot be replaced by a test override or an owner-only successful insert. Do not repeat the whole suite when passing results already cover unchanged behavior; investigate failures and rerun affected plus required checks after fixes.

## Production activation and opening day

The assigned execution task includes controlled activation of the already approved production schedules after required evidence and owner diff review. Verify the intended repository/project and production-enable setting. Keep a clear disable command and never relax a failed gate to make the switch possible. If readiness fails, leave production disabled and report the missing decision/resource/evidence.

On October 19, freeze launch scope and review readiness, fallback availability, backup age, and opening-game deadlines. Only correctness/readiness fixes proceed. On October 20, refresh accepted schedule/status and rosters in time for a supervised 17:00 UTC attempt. Call the same protected operation as automation, not manual SQL. Query the committed batch, all expected target slots, source/feature/model IDs, and timely different-transaction receipt. Record actual IDs/times and known abstentions.

If cloud fails, invoke the verified local path; if a batch exists, confirm that same identity only while allowed. At the effective cutoff stop and record missed/unverified coverage. A later source correction or actual start can append invalidation; preserve original evidence. At 19:00 UTC do not create a replacement/backdated batch. Reconciliation and live reports begin after validated finals, with no artificial launch accuracy number.

## Acceptance and required tests

- [ ] Every mandatory readiness item has actual supporting evidence or a failed/unverified status that blocks activation. The report explicitly distinguishes fixture, manual, unattended, and official evidence.
- [ ] The unattended cycle and failure drill demonstrate the configured primary/local paths, real notification delivery, backup recovery, and immutable ledger behavior.
- [ ] First official regular-season forecasts are acknowledged only with protected timely receipts and full cohort/target evidence; otherwise report a visible missed launch, never a fabricated successful checkpoint.
- [ ] PR checks and notebook executions pass, production credentials/data stay outside CI fixtures/Git, and README/runbook/Weaknesses.md record actual results.

Required checks: run the established lint/type/test suite and both fixture notebooks; real-role publication/concurrency/time boundary checks; manual and unattended cloud/local traces; actual off-device restore and notification evidence; final SQL readback of target/model/cohort/receipt completeness. Add a regression test only for a newly found defect, not a test that simply repeats a checklist statement.

## Failure decision, files, and handoff

If a required adapter or safe database/backup route is not ready, explicitly state the October 20 risk and the remaining work. Cut optional injury integration, extra report detail, older history, and all later modules first. Do not waive CI, leakage, migrations, roster honesty, source health, protected timing, recovery, or coverage. Any reduced required launch scope or changed deadline needs a separate owner decision; listing a blocker in Weaknesses.md is not approval to defer it.

Likely files: readiness/operating report and existing runbooks; reviewed fixes/configuration only where necessary; README.md, AGENTS.md, critical-path status, Weaknesses.md. No speculative feature work. Actual private evidence stays in controlled artifacts with sanitized report references.

Return the evidence checklist, exact commands/results, actual run URLs/task states, notification and restore verification, capacity/backup age, production-enable/disable state, supervised publication IDs/times or missed-coverage report, and outstanding limitations. Explain the pipeline from raw observation to official receipt to revised outcome/report.

Approval: the owner's October 14 batch approval locks this specification. A separate assignment starts execution. No rehearsal, activation, launch, publication, or readiness verification has occurred by writing this document.
