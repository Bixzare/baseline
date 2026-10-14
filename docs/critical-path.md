# Opening-night critical path

Status: Locked by the project owner on October 12, 2026; delivery-calendar revision approved under the owner's batch planning authorization on October 14, 2026.

Version: 1.1

This document records the approved plan. It does not claim that implementation, source verification, or deployment has been completed. Changes to the locked scope require an explicit owner decision.

## Objective and deadline

Deliver Phases 0 and 1 before the first regular-season game on Tuesday, October 20, 2026, at 19:00 UTC (21:00 Africa/Johannesburg, 3:00 p.m. ET).

The first publication target is 17:00 UTC (19:00 local), leaving two hours for recovery before tip-off. Confirm the schedule again during launch checks.

The destination remains an autonomous NBA ML service with a separately deployable public dashboard, team predictions, player projections, monitoring, automated retraining, governed model promotion, and modular analytics. The opening-night baseline is the first working component.

## Approved launch scope

- Verify NBA live data access from GitHub Actions and historical access locally.
- Backfill the 2025-26 regular season locally through nba_api. Retain raw inputs.
- Verify a current roster source and preserve the time each roster snapshot was collected.
- Accept a reliable injury source or explicitly defer injury ingestion. Unknown availability must remain explicit.
- Publish five player targets: minutes, points, rebounds, assists, and three-pointers made.
- Use recent average minutes and historical production rates. Detailed baseline semantics will be specified in the PRD and design.
- Record an explicit insufficient-history abstention for a rostered player without usable NBA history. Include abstentions in coverage reporting.
- Store predictions durably in Supabase Postgres, with schema migrations in the repository.
- Collect final results, reconcile them against predictions, and report basic errors, coverage, and source health.
- Use GitHub Actions as the primary runner and Windows Task Scheduler as the operational fallback.

Team predictions and Elo follow immediately after the launch scope. Trained models, the dashboard, MLflow, drift tooling, automated retraining and promotion, and awards are outside the opening-night critical path.

## Confirmed later scope

- In v1, tracking means results updated after games and a prediction record that develops throughout the season. In-game score refresh and in-game predictions are later components.
- Awards are v1.5: a weekly statistical ladder of the top five players for each supported award, with ranks and movement from the previous week. This is not a calibrated probability of winning.
- Supported awards remain MVP, ROY, DPOY, 6MOY, and MIP. Eligibility and historical validation must be specified before implementation.
- Modern training windows will be evaluated through chronological backtests. Era comparisons are a separate future analytics module; no specific era boundary or training-window length is locked here.
- Dashboard deployment must be independent of collection and training, using a stable interface for published results and model health.
- GitHub Student Developer Pack benefits may support later hosting or a domain, but the operating plan must survive benefit expiration.

## Capacity and feasibility

The planning allowance is approximately 28 focused hours across October 12-20, including reviews and deployment checks. Phases 0 and 1 take priority this week. Afterward, plan around approximately 3-10 hours per week.

This estimate assumes prompt planning decisions and leaves little slack. Access failures should trigger the fallback rather than several days of endpoint debugging.

## Updated execution plan, October 14-20

The original October 12 start has passed without implementation in this planning chat. The sixteen detailed launch issues now estimate approximately 44-51 hours of agent work, excluding owner review, live collection, setup delays, and the elapsed unattended cycle. These are planning estimates, not measured throughput. They are not the same unit as the original 28-hour owner-focused allowance, and that allowance must not be treated as proof the expanded detail fits.

The following dates are provisional execution targets, conditional on rapid setup and sequential owner review. Start BOOT-001 and SOURCE-001 immediately in the separate execution chat. Do not wait for post-launch issue planning. If the available execution/review time cannot cover this sequence, report the October 20 risk and seek an explicit revised scope/deadline; do not compress away mandatory tests or recovery gates.

| Date | Ordered task targets | Verification / decision |
| --- | --- | --- |
| Wed Oct 14 | BOOT-001, SOURCE-001, approximately 3.5-4 agent hours. | Establish actual PR CI and permitted source routing. Accept availability or explicitly defer. A failed cloud probe selects a verified local route immediately; no days of access-denial debugging. |
| Thu Oct 15 | DATA-001, DB-001, DB-002, DB-003, approximately 11.5-13.5 agent hours. | Accepted archive/coverage, Free project/connectivity, migrations/roles, private evidence access, and compact seed. If sources or database remain blocked, reassess deadline now; do not assume later integration will recover the time. |
| Fri Oct 16 | MODEL-001, LEDGER-001, LEDGER-002, COLLECT-001, approximately 13-15 agent hours. | Whole-roster prepared outputs, protected schema/registration, separate-transaction receipts, and actual fresh collection. Interfaces may complete on fixtures while real-input gates remain visibly unverified; no official readiness claim. |
| Sat Oct 17 | OUTCOME-001, EVAL-001, OPS-001, approximately 8 agent hours. | Final/DNP revisions, honest metrics/coverage, and actual manual cloud workflow. Production schedules remain disabled pending recovery/readiness. |
| Sun Oct 18 | OPS-002, BACKUP-001, and begin LAUNCH-001, approximately 6-7 agent hours plus drill/rehearsal time. | Verify Windows recovery/notification, off-device backup and isolated restore; start an actual unattended cycle soon enough to observe the 07:17 UTC nightly run on Oct 19. |
| Mon Oct 19 | Complete unattended evidence and readiness review; reserve LAUNCH-001's remaining verification effort. | Freeze features. Resolve correctness/readiness blockers only. Verify actual task availability, backup age, capacity, and enable production only after gates pass. |
| Tue Oct 20 | Supervise the 17:00 UTC / 19:00 UTC+2 publication target. | Read back actual batch/receipt/cohort/model IDs. Recover locally if allowed; stop at the effective 15-minute cutoff. First stated tip-off is 19:00 UTC / 21:00 UTC+2. |

These long agent days are a schedule risk, not an expectation of equivalent owner work. Review every diff and record actual duration after each task; revise remaining forecasts as evidence arrives. If starting later, shift unfinished work honestly and report which gates no longer fit. Endpoint/account failures may still prevent launch.

## Original daily execution plan, superseded calendar

All dates are in October 2026. Work is performed by a separate coding agent, one task at a time, with owner review of every diff.

| Date | Work and approximate time | Verification gate |
| --- | --- | --- |
| Mon Oct 12 | 4 h: Establish minimal repository conventions and PR CI. Probe live sources from GitHub Actions and historical access locally. | Lint, type checks, and initial tests pass. Save timestamped evidence of valid payloads, not just HTTP success. Check schedule, completed box scores, and roster access separately. |
| Tue Oct 13 | 4 h: Repeat access tests. Verify upcoming-game coverage and time interpretation. Build and test a resumable local backfill sample. Decide injury-source readiness. | Historical player and team records parse correctly. A repeated run avoids duplicate records. Cloud or local collection path chosen. Injury source accepted or explicitly deferred. |
| Wed Oct 14 | 3 h: Complete the 2025-26 regular-season seed. Capture current rosters. Establish Supabase through migrations and preserve raw inputs. | Reconcile expected games and collected records; report gaps. Recreate schema from migrations. Confirm player IDs join across sources and roster membership is timestamped. |
| Thu Oct 15 | 4 h: Implement the recent-history baseline and prediction ledger. Define missing-history handling and prediction coverage. | Test all five targets, zero minutes, rookies, transfers, missing history, and exclusion of future games. Verify retries do not duplicate predictions and the runtime writer cannot update or delete them. |
| Fri Oct 16 | 4 h: Automate collection, prediction publication, and result reconciliation as separate steps. Add source health records and failure notifications. | Run the complete workflow. Test empty responses, schema changes, stale inputs, and interrupted runs. Outcomes join to predictions without modifying prediction records. |
| Sat Oct 17 | 3 h: Rehearse failures and the Windows Task Scheduler fallback. | Cloud and local runs cannot create conflicting official predictions. Test missing runs, late execution, postponements, and recovery. Predictions after the cutoff are rejected. |
| Sun Oct 18 | 3 h: Run an unattended rehearsal. Reconcile available final outcomes and calculate baseline errors and coverage. | Verify timestamps, feature references, model versions, outcome matching, and health alerts. Any preseason rehearsal data stays separate from the regular-season track record. |
| Mon Oct 19 | 2 h: Freeze scope. Review opening-day schedule and rosters, README, recovery instructions, and outstanding defects. | No unresolved defect affecting correctness, durable storage, or scheduling. Confirm fallback machine, credentials, and notifications work. |
| Tue Oct 20 | 1 h reserved: Supervise the first regular-season publication and verify database records. | Target publication by 17:00 UTC / 19:00 local. Confirm committed timestamps and coverage; invoke fallback if necessary. |

## Scheduling and fallback

GitHub Actions scheduled workflows can be delayed or dropped. A configured schedule alone does not establish publication reliability.

- Collect final results separately from the job publishing upcoming predictions.
- Use the verified schedule to establish publication deadlines, including early games.
- Run an independent local deadline check during the initial launch period.
- The original October 13 fallback decision point has passed. At the first bounded SOURCE-001 spike, select the verified Windows route immediately for cloud-failed capabilities; use the same Supabase ledger and protected commands.
- Reserve an awake, connected Windows machine for opening day.
- If a CDN endpoint fails everywhere, moving the collector locally does not solve that. Evaluate a permitted local nba_api stats alternative.
- If no valid source is available, record missing coverage and alert. Never manufacture historical prediction timestamps or silently use stale schedules.
- Do not spoof or bypass access controls. Request allowances and source reliability remain unverified until the access spike records evidence.

## Scope cuts and failure conditions

Cut history beyond the required seed, optional features, injury integration, and polished reporting first if the plan slips. Keep the two concise fixture walkthroughs and basic per-target errors/coverage; richer charts and report detail can wait.

Keep migrations, CI, leakage tests, ledger integrity, coverage reporting, and recovery checks. If verified roster coverage remains unavailable, explicitly reduce player coverage or revise the launch target with the owner.

A missed publication is a visible coverage failure. It must never be repaired by inserting a prediction that appears to have existed before tip-off.

## Engineering and learning gates

- Tests for every feature, including data validation and explicit leakage tests.
- Lint, type checks, and tests on every pull request.
- Database changes through versioned migrations, never manual schema edits.
- No secrets in code; credentials supplied through environment variables.
- Source health monitoring for every source.
- Small pull requests, each linked to one issue, with owner review of every diff.
- Important decisions documented as short ADRs in docs/decisions/ after review and lock.
- README updates included in the definition of done.
- Each task handoff explains the data flow, the decision and its tradeoff, the tests, and one failure scenario. The owner should be able to explain why the change exists before accepting it.

Prediction records remain immutable. Outcomes and evaluation results are stored separately. Historical backfill timestamps must not be presented as proof of original historical availability; historical availability assumptions must be documented separately from live evidence.

## Planning handoff

The PRD, design, twelve ADRs, AGENTS.md, skills, and sixteen local launch issue specifications are finalized. On October 14 the owner approved launch-first planning and then authorized batch locking of the remaining launch backlog, replacing individual draft/lock pauses for that batch. Implementation still runs one assigned issue at a time with every diff reviewed; later major decisions still need explicit review.

Use [README execution order](../README.md#execution-order-and-handoff) and assign BOOT-001 first. Repository/project creation, source access, compatible dependencies, notifications, backup provider/path/remote verification, isolated restore, and readiness are execution gates, not completed planning results. Later model/MLOps/dashboard/awards issues are detailed before their implementation without delaying launch.

## References

- [NBA 2026-27 schedule announcement](https://pr.nba.com/2026-27-nba-regular-season-schedule)
- [nba_api documentation](https://github.com/swar/nba_api)
- [GitHub Actions scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub Education partner offer terms](https://docs.github.com/en/education/about-github-education/github-terms-and-conditions-for-the-student-developer-pack)
