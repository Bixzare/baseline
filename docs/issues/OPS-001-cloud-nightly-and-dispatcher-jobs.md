# OPS-001: Schedule nightly and dispatcher cloud jobs

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Phase: 1. Priority: launch blocker. Dependencies: COLLECT-001, OUTCOME-001, EVAL-001, and LEDGER-002 implemented and owner-reviewed. SOURCE-001 must establish accepted cloud capabilities; missing local-only capabilities remain explicit dependencies on OPS-002. Session estimate: about 2.5 agent hours plus manual workflow rehearsal and owner review.

## Goal and scope

Run shared collection/reconciliation/report/publication commands unattended on GitHub Actions, without embedding logic in workflow YAML. Configure workflows and exercise manual rehearsals; enable production schedules only at the final launch gate after local fallback/backup readiness. No ML training, dashboard deployment, new sources, or privileged database credential in jobs.

Read AGENTS.md and skills `hoop-data-quality`, `hoop-python-testing`, and `hoop-postgres`. Contracts: [ADR 0005](../decisions/0005-schedule-batch-jobs-with-local-recovery.md), [design cadence](../design.md#81-scheduled-work), and the four dependency issues. Deadline: October 20, 2026 at 19:00 UTC, target publication 17:00 UTC.

## Orchestration contract

| Operation | UTC schedule and stages |
| --- | --- |
| Nightly | Daily 07:17: reconcile persisted pending finals/recent corrections, refresh needed accepted rosters, and produce accuracy/coverage reports. |
| Dispatcher | Every 15 minutes at 7, 22, 37, 52: discover due upcoming occurrences, refresh essential evidence when needed, reconcile missing relevant prior finals, prepare and publish eligible missing batches, or confirm the original unverified batch while permitted. |

Use a separate production-enable repository setting defaulting off. While disabled, manual read/preparation or separate-database fixture rehearsals may run, but skipped production stages are reported disabled, not healthy production heartbeats. Merging a workflow must not inadvertently publish rehearsal forecasts into the real ledger. Activation is part of LAUNCH-001.

The dispatcher aims at two hours before tip-off and may attempt recovery only while strictly before the 15-minute cutoff and before actual start. Database guards remain authoritative. Delayed jobs re-evaluate eligibility, never backfill official predictions. Completed receipts are read back unchanged; an existing batch is never regenerated because its first response was lost.

Use the verified season schedule/persisted pending IDs, not just today's scoreboard. Successful no-game runs retain an explicit validated empty-work result. Skip unnecessary NBA requests; measure actual job time, request volume, installed environment cost, memory, and free account allowances. No paid runner or automatic upgrade. Student benefits are optional.

Use Python 3.12 and locked uv dependencies, with only tested package commands and pinned/reviewed workflow actions. Supply restricted database and backend Storage credentials from GitHub secrets. No migration/admin/service key, secrets in artifacts, production connection on PR CI, or trusted access from unreviewed forks. Keep workflow permissions minimal and unrelated workflows unchanged.

## Coordination and failure contract

- Give each operation an immutable run ID, actual start/finish events, source checks, stage counts/durations, and success/partial/failure/no-work reasons. A start heartbeat is not proof that publication or reconciliation completed.
- Use bounded database coordination for overlapping operation/source work across cloud and Windows, with a stable lock key and release on failure/disconnect. Session leases, if used, live outside transactions containing network requests. Do not hold a publication transaction while polling/training. Ledger occurrence locks/uniqueness still protect correctness independently.
- GitHub concurrency is an additional load guard, with no cancellation of an in-flight official transaction. Avoid treating a queued/canceled/overlapping workflow as completed. Process unaffected games where safe; return failure after recording affected failures so notification and recovery can act.
- Honor accepted source routing and budgets. Cloud never probes historical stats or substitutes previous participants for a locally sourced roster. A local-only required snapshot keeps its original timestamps; stale/missing evidence blocks that game.
- Retry transient stages within declared limits and remaining deadline. Conflicts, invalid data, denied access, and a closed cutoff are not retry-until-success conditions. Persist sanitized reasons outside failed ledger transactions. If the database is down, retain a local runner report without claiming a durable heartbeat.
- Verify actual GitHub failure notification delivery to the owner during execution, including notification preferences. A failing exit code or configured workflow alone does not prove delivery. OPS-002 is the independent deadline checker.

GitHub documents that scheduled runs may be delayed/dropped and public-repository schedules may be disabled after inactivity. Confirm workflow/default-branch behavior and available allowances in the actual account; [GitHub scheduling documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). Do not assume a cron expression establishes reliability.

## Acceptance criteria

- [ ] Shared commands run from actual manual GitHub Actions rehearsals using the intended locked environment and restricted credentials; exact run URLs/outcomes are retained.
- [ ] Nightly/dispatcher schedules, stage order, no-work states, deadline behavior, and default-off production activation are tested and documented.
- [ ] Overlap/cloud-local coordination prevents unnecessary duplicated work without becoming the sole ledger integrity mechanism. Failures retain stage/source evidence and leave accepted forecasts unchanged.
- [ ] Actual notification delivery is verified or explicitly blocked; production remains gated until fallback/backup/readiness pass.
- [ ] Fixture CI passes without live endpoints/secrets. README/AGENTS.md describe enable/disable, manual execution, recovery, runtime/resource measurements, and source routing.

## Required tests

- Injected-clock cadence/due-work selection around UTC midnight, early games, two-hour target, 90-minute recovery boundary, 15-minute equality, later corrections, and delayed/catch-up runs.
- No-game versus unknown schedule, stale/local-only roster, pending previous-day final, source partial failure, invalid prepared batch, existing receipt/unverified batch, and lost commit response.
- Actual database lease/lock overlap and release on exception/disconnect with cloud/local callers; compare ledger identity after identical/conflicting attempts.
- Workflow configuration/command contract checks, environment validation/redaction, production-enable default off, rehearsal rejection of the production database, and no privileged key path.
- Actual manually invoked workflow read/collection rehearsal and verified owner notification, separate from deterministic tests. Final unattended schedule proof belongs to LAUNCH-001.

## Files and handoff

Likely files: `.github/workflows/nightly.yml`, `dispatcher.yml`, existing CI checks; shared orchestration/run/lock helpers and thin CLI; NBA due-work selectors; nonsecret workflow policy; unit/integration/leakage fixtures; orchestration/runbook notes, README.md, AGENTS.md, Weaknesses.md. Add migrations only for necessary permission/helper changes, not an orchestration framework.

Return PR/check results, actual workflow links, measured resources/request counts, credential/permission mapping without values, notification evidence, stage/overlap failures, and production-enable state. Explain why cron and GitHub concurrency do not replace database cutoff/uniqueness enforcement.

Approval: the owner's October 14 batch approval locks this specification. A separate assignment starts execution. No workflow, schedule activation, notification, or cloud publication has been executed by this document.
