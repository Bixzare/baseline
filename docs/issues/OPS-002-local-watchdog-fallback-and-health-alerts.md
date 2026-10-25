# OPS-002: Establish independent local recovery and operational health

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Phase: 1. Priority: launch blocker. Dependencies: OPS-001, COLLECT-001, EVAL-001, and LEDGER-002 implemented and owner-reviewed. Required setup: the owner's awake Windows machine, intended login/session, local accepted adapters, secure environment credentials, and GitHub notification delivery. Session estimate: about 3 agent hours plus intended-session and failure drills.


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

Independently detect missed cloud work and execute the same protected recovery commands locally. Monitor source freshness, reconciliation, publication, capacity, and backup evidence. No new always-on hosting, messaging provider, training trigger, or global Windows power/security changes. Deadline: October 20, 2026 at 19:00 UTC, target publication 17:00 UTC.

Read AGENTS.md and skills `hoop-data-quality`, `hoop-postgres`, `hoop-python-testing`. Contracts: [ADR 0005](../decisions/0005-schedule-batch-jobs-with-local-recovery.md), [design alerts](../design.md#83-alerts-and-idempotency), and [capacity/backup policy](../design.md#16-retention-backup-and-capacity). A sleeping/offline machine cannot provide an always-on checker; record this boundary.

## Health and persistence contract

Add `platform.alert_events` by migration: alert_event_id UUID; alert_key, severity, state; observed_at UTC; optional run_id and report_id FKs; sanitized details JSONB. Append open/acknowledgment/resolution events with stable keys; no evidence mutation. Grant runtime only required read/append, with no anonymous private access. Link backup freshness through BACKUP-001's run-event/manifest contract, without claiming backup delivery before that task exists.

Produce structured health results for each source/capability/environment, schedule/roster age, last started and last successful stage, pending/late finals, expected versus valid coverage, and backup verification. Missing data is unknown/unverified, not healthy. Keep original observation times and explain partial/unavailable measurements.

| Condition | Required action |
| --- | --- |
| Missing dispatcher heartbeat for 45 minutes within an upcoming publication window | Append warning and notify; distinguish a missing start from an unfinished/failed publication. |
| Nightly reconciliation not successful by 09:17 UTC | Append alert and attempt supported reconciliation without claiming stale history is current. |
| Missing valid forecast at 90 minutes before tip-off | Alert and attempt the shared local recovery command with fresh accepted inputs, if fallback is enabled. |
| At/after 15-minute cutoff or game already started | Stop new publication/confirmation; record missed/unverified coverage. Never regenerate/backdate an existing batch. |
| Essential invalid/stale source or missing required artifact | Block affected work and notify; preserve unaffected safe processing. |
| Latest verified off-device backup cutoff older than 24 hours, or no verified backup | Alert with age/unverified reason. Uploading an old snapshot again does not reset age. |
| Database/object allowance reaches 60%, or projected season overflow | Warn using verified limits and documented measurement/estimate. |
| 80% allowance | Pause optional shadow/additional reports, preserve official evidence; required operations continue only with sufficient capacity. No paid upgrade or pruning official rows. |

Measure database/index and object usage through supported least-privilege methods, compared with actual account limits from DB-001. Distinguish provider/account usage from registered-artifact estimates and orphan-object uncertainty. Check on each daily health pass and record unavailable measurements explicitly; do not supply an administrator key to ordinary jobs merely to obtain usage metrics.

## Windows recovery and notification contract

- Install/configure versioned Task Scheduler definitions for a 15-minute watchdog and accepted local-only collection/fallback tasks. Use shared package commands, the project environment, UTC-aware policy, and bounded logs. Document actual task names, principal/session, executable/environment, enabled state, and prerequisites. Do not add Docker/WSL/VMs or change global sleep settings.
- A catch-up run after sleep rechecks current eligibility; it never publishes a missed pregame forecast retroactively. Local-only rosters must be refreshed/uploaded before their 24-hour expiry; cloud consumes original timestamps. If cloud collection fails, the accepted local route must be available, not merely written in a runbook.
- Use database time when connected. If unavailable, show cached schedule age and a local UTC incident log/desktop notification; do not claim server-side recording or attempt blind publication. A cached deadline can guide an alert, never bypass the protected operation.
- Verify local desktop notification delivery in the actual intended login/session and GitHub failure delivery outside the dashboard. Stable app alert keys avoid repeated open events; standard GitHub notifications may still repeat. No unsolicited messages to other recipients.
- Configure minimal task recovery without launching visible helper windows or embedding credentials in arguments/XML/logs. Credentials come from configured environment secrets. Explicit owner setup supplies the machine availability/login commitment for opening day.
- Preserve original batch/receipt identities when local and cloud race. Production remains gated until the independent check, recovery, delivery, and BACKUP-001 status have been rehearsed.

## Acceptance criteria

- [ ] Migration, health states, stable alert lifecycle, and real-role append/read restrictions pass fixture/integration checks.
- [ ] The actual independent Windows tasks detect simulated missing/failed cloud work and invoke the shared protected recovery path before deadline.
- [ ] Intended-session desktop and actual GitHub notifications reach the owner, with documented offline/sleep limits and no false durable-recording claim.
- [ ] Cloud/local races, resume after sleep, invalid sources, cutoff stopping, and lost commit response preserve immutable ledger evidence.
- [ ] Capacity/backup checks use verified measurements or visible unknowns, apply the fixed thresholds, and never delete official evidence or enable paid infrastructure.
- [ ] README/AGENTS.md/runbook and Weaknesses.md describe actual setup, availability, enable/disable/recovery, and unverified gates. Fixture CI has no production credentials or live notification dependency.

## Required tests

- Fixed-clock equality/below/above tests for 45-minute heartbeat, 09:17 nightly, 90-minute recovery, 15-minute stop, 24-hour backup, and 60%/80% capacity boundaries; UTC/local offset and wake-after-deadline.
- Missing started/completed events, partial source failure, unknown roster, stale cache, unresolved prior final, existing unverified batch/receipt, database failure, local log redaction, and stable alert open/resolve/idempotency.
- Two real Postgres callers for local/cloud recovery, lease release, exact/conflicting retry, and timely versus late receipts. No runtime alert operation may mutate forecasts or grants.
- Actual Task Scheduler run in the intended session, checked process exit/log/events, local-only collection upload, and notification delivery. A registered task or queued notification alone is not acceptance.
- Fixture source/leakage checks ensure newer rosters/results cannot rewrite saved cohorts during recovery. Separate live failure drills from PR CI.

## Files and handoff

Likely files: alert/helper migrations; shared monitoring/health/locks/run operations; NBA deadline/recovery adapters; Windows task definitions/setup helpers; unit/integration/leakage fixtures; monitoring/runbook notes, README.md, AGENTS.md, Weaknesses.md. BACKUP-001 owns export/sync/restore; this issue consumes its evidence contract.

Return PR/checks, actual task definitions/run evidence, notification receipts confirmed by the owner, failure/race drill reports, measured thresholds, machine availability, and missing gates. If session delivery or independent execution cannot be verified, report the launch reliability gate failed rather than add unsupported assurances.

Approval: the owner's October 14 batch approval locks this specification. A separate assignment starts execution. No task, alert, notification, local recovery, or capacity check has been executed by this document.
