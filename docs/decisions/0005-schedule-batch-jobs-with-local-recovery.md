# ADR 0005: Schedule batch jobs with independent local recovery

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [locked critical path](../critical-path.md), [PRD operational monitoring](../PRD.md#mon-01-operational-health-required-at-launch), and [design Section 8](../design.md#8-scheduling-freshness-and-recovery). This record documents approved operating policies; scheduling, notifications, and recovery remain unverified.

## Context

Baseline is a batch prediction platform with deadlines before games. A job that fails can report an error, but a job that never starts needs independent detection. Source access, incomplete results, stale schedules, and a sleeping fallback machine can each prevent timely publication.

The launch needs a small operating setup within the free budget. It does not need an always-running API, message broker, or a separate orchestration service.

## Decision

- Use GitHub Actions as the primary scheduler and Windows Task Scheduler for local deadline monitoring and fallback. Both call the same tested CLI operations, with the accepted source configuration for their environment.
- Reconcile nightly at 07:17 UTC: fetch pending game IDs, validate final outcomes and corrections, refresh supported roster observations, and rebuild accuracy and coverage summaries.
- Run the dispatcher at UTC minutes 7, 22, 37, and 52. Refresh schedule evidence when due, find unpublished games at or within two hours of tip-off, and attempt publication before the cutoff. Avoid NBA requests when current evidence and workload make them unnecessary.
- Reconcile due pending finals during dispatch when needed for a new forecast. Use stored game IDs; today's scoreboard is not sufficient to rediscover earlier unfinished games.
- Require a successful schedule/status check no older than 30 minutes and team roster checks no older than 24 hours at publication. A fresh download does not make stale source contents fresh. Preserve observation and source timestamps separately.
- Attempt reconciliation of unresolved records within the required recent-history window before forecasting. If necessary participation or outcomes remain unknown, block affected player forecasts rather than silently skipping them. Confirmed DNP is resolved data; unrelated older gaps need not stop unaffected forecasts.
- Run an independent local watchdog every 15 minutes. During an upcoming publication window, alert when dispatcher heartbeat has been absent for 45 minutes. Alert if nightly reconciliation has not succeeded by 09:17 UTC.
- If a forecast is missing 90 minutes before tip-off, alert and attempt the same publication operation locally when fallback is enabled. Stop at the 15-minute cutoff and record missed coverage, under [ADR 0004](0004-enforce-immutable-pregame-publication.md).
- Use GitHub workflow failure emails and Windows desktop alerts. Required source, data, and publication failures return a failing job status. Verify delivery in the owner's intended session; use stable alert keys and preserve incident history when resolved.
- If the database is unreachable, write a timestamped local incident log and desktop alert. Do not claim a database record was saved. Verified no-game days are successful checks, not outages.
- Coordinate cloud and local attempts with database uniqueness and short transaction locks. Workflow concurrency alone is insufficient to coordinate the two runners. Retrying cannot replace an accepted forecast.

Training and awards use their approved later schedules after their release gates pass. A training failure leaves a healthy champion available to forecast. Injury data may be deferred at launch; adopting it later requires a tested freshness policy.

## Reason and alternatives

This setup reuses the repository's job commands and keeps deadline detection separate from the primary scheduler. Off-hour dispatcher minutes and early publication targets provide time for recovery, but do not guarantee that a provider starts every scheduled job on time.

Relying only on workflow failure notifications would miss jobs that never started. Putting prediction, reconciliation, and training into one inseparable run would allow a training failure to interrupt forecasts. Adding Prefect or an always-running service before launch would introduce another service to configure and maintain. Those alternatives are not selected.

## Consequences

The fallback and watchdog require an awake, connected machine and a working notification session. Opening night therefore uses owner supervision and an intended publication attempt by 17:00 UTC. Always-on external monitoring is a later reliability improvement; this design does not claim uninterrupted monitoring while the machine is unavailable.

Schedule alignment and provider delays can move publication later than the two-hour target. Freshness and cutoff checks still apply on every attempt. A source or runner outage remains visible in coverage and health rather than being filled by late forecasts.

## Verification required during implementation

- Verify installed schedules and the shared CLI path in the actual cloud runner and intended Windows session. Test UTC boundaries, no-game days, pending finals, and games that cross reporting dates.
- Inject missing dispatch, failed nightly reconciliation, database outage, malformed responses, stale source contents, and unresolved history; verify the correct affected forecasts are blocked and notifications arrive.
- Test the 30-minute schedule and 24-hour roster freshness boundaries, 45-minute heartbeat alert, 09:17 UTC nightly alert, and 90-minute recovery trigger against a controlled clock.
- Rehearse local recovery, simultaneous runner attempts, preserved forecast identity, and missed-cutoff reporting. Verify incident resolution does not erase earlier failures.
- Record the machine availability requirement and rehearse the supervised opening-night publication path before declaring launch readiness.

Approval: the owner explicitly said "lock" on October 12, 2026. No workflow, local schedule, notification, or recovery drill has been executed by this planning record.
