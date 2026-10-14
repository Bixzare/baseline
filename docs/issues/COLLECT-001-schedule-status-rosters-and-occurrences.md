# COLLECT-001: Collect schedules, status, rosters, and occurrence changes

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Phase: 1. Priority: launch blocker. Dependencies: SOURCE-001, DB-003, and LEDGER-002 implemented and owner-reviewed, with their source/artifact foundations. Owner acceptance must identify permitted adapters by capability/environment and accept or explicitly defer availability. Session estimate: 3 to 4 agent hours plus source measurements and owner review.

## Goal and scope

Provide shared commands for ongoing schedule/status/current-roster collection, immutable observations, and safe occurrence changes. Cloud and Windows use the same validation/persistence operations with their own accepted source routing. No scheduler, final-result ingestion, injury model, or forecast calculation in this task. Deadline: October 20, 2026 at 19:00 UTC; opening publication target 17:00 UTC.

Read AGENTS.md and skills `hoop-data-quality`, `hoop-postgres`, and `hoop-python-testing`. Contracts: [source decision](../decisions/0001-verify-nba-sources-by-environment.md), [ledger lifecycle](../decisions/0004-enforce-immutable-pregame-publication.md), and [design freshness](../design.md#82-freshness-and-missing-facts). Required tables already exist; any new constraints/helpers use migrations.

## Collection contract

- Use only SOURCE-001's accepted exact adapters/configuration. A package install or HTTP 200 does not establish a valid capability. Full future schedule evidence discovers games; a current scoreboard is a status resource, not the future-game inventory.
- Preserve stable string IDs, home/away/season/competition, scheduled UTC start when supported, actual start only when supplied, and unknown or unscheduled slots. Respect verified NBA source-day/timezone conventions; do not use the Windows calendar day as the league day or invent midnight starts.
- Fetch/store raw bodies through the existing artifact client, validate, then append source_checks and event_observations. Identical bytes may reuse objects, but each genuine observation retains actual receipt/validation metadata. Invalid responses remain quarantined with failure reasons, never healthy empty schedules.
- Current roster snapshots require team/season/identity checks and a membership artifact including every supported rostered player. Player names are labels. Missing history is legitimate; previous-game participants or final box-score lists cannot substitute for the current roster.
- Preserve source generation/publication times when supported. A newly fetched stale source body can remain unusable. Successful repeated validation is not permission to rewrite old collection times. Preparation/publication require schedule/status age at most 30 minutes and roster age at most 24 hours.
- Collect the verified season schedule at nightly refresh and when needed to restore freshness before publication; refresh current status for due games. Use a seven-day upcoming work list as an initial project setting, while keeping the accepted full-season inventory. Refresh rosters only for teams needing renewal, never all teams every dispatcher tick. Measure actual request count/runtime and retain a versioned budget.
- Use sequential requests per source with the accepted minimum three-second gap, 30-second timeout, at most two temporary retries, and bounded total work. Honor Retry-After within the budget. Denial/bot challenges stop that source; no cloud stats.nba.com requests, spoofing, proxy rotation, or access-control evasion.

## Cloud/local and lifecycle contract

If a required roster/schedule adapter works locally only, Windows collects it and uploads the same evidence to the shared database/storage. Cloud may consume that snapshot only while its original timestamp remains fresh. Record this as a hybrid dependency on the awake local machine, not a fully cloud source. If CDN works locally only, use that accepted path; if it fails everywhere, a different permitted adapter needs acceptance.

Lock an occurrence while applying its transition and preserve every observation. Ordinary schedule corrections keep the occurrence. A verified postponement closes/excludes the earlier occurrence; when a supported new schedule is established, create one linked successor even if the NBA ID is reused. Repeated observations or concurrent cloud/local attempts cannot create multiple successors. Never infer cancellation/postponement from an omitted game or merely delayed start. Preserve uncertain/suspended states with an explicit unresolved reason.

Call LEDGER-002's guarded lifecycle operation for existing forecasts affected by postponement, cancellation, an earlier actual start, or invalidating schedule correction. Preserve old values and reservations. Never extend an already closed deadline for the old occurrence or clear invalidation with a later feed. If source persistence succeeds but required lifecycle append fails, report incomplete collection, retain the source identity, and retry that append idempotently. Evaluation must not count a known excluded occurrence while an audit append is pending.

## Acceptance criteria

- [ ] Shared cloud/local commands persist valid upcoming schedule/status and current roster evidence with original times, identities, hashes, run IDs, and source health; failures/unknowns remain distinct.
- [ ] Freshness checks and measured request budgets support due-game preparation without unnecessary polling or silent cache timestamp renewal.
- [ ] Verified corrections, postponements/successors, cancellation, earlier starts, and unknown transitions preserve history and update ledger validity through guarded append operations.
- [ ] Cloud/local routing is rehearsed in actual accepted environments, including any required local-only roster upload. Failure blocks affected games, with no fabricated empty cohort.
- [ ] PR checks, validation/leakage/integration tests pass. README/AGENTS.md commands, source report, and Weaknesses.md reflect actual routing and remaining scheduling gates.

## Required tests

- Valid fixtures, no-game versus invalid-empty data, missing source generation/starts, stale generations, season mismatch, leading-zero IDs, roster trades/new players, duplicated or contradictory memberships, and UTC/source-day boundaries.
- Later roster/status/correction observations cannot alter an earlier feature cohort. Final participants never populate a pregame roster; unsupported historical times remain unknown.
- Temporary retry/Retry-After/budget exhaustion and immediate denial stop; raw/artifact/hash failure; database interruption; genuine repeated observations versus reused bytes.
- Two real Postgres connections applying the same postponement, upstream-ID reuse, timely normal correction, late delayed-start reopening, and lifecycle failure after source commit. Verify one successor and preserved original forecasts.
- Fixture CI uses no live source or production credential. Separate actual adapter rehearsals record exact scope and failures, rather than claiming fixture success proves source access.

## Dependencies, files, and handoff

Source absence blocks affected collection/publication. Escalate a missing capability or changed coverage; do not replace it silently. No paid source or increased rate allowance is assumed. Implement independent fixture work while an actual routing gate is unresolved.

Likely files: NBA `sources/`, schedule/roster/occurrence operations, shared evidence helpers and CLI; accepted source/work-budget configuration; SQL transition helper migrations if needed; unit/integration/leakage fixtures; source verification/setup notes, README.md, AGENTS.md, Weaknesses.md. Extend the fixture source walkthrough only where helpful; no orchestration workflow yet.

Return PR/check outcomes, real cloud/local collection evidence, IDs/hashes, measured requests/runtime, routing/freshness report, transition/race results, and unresolved gates. Explain one hybrid-source failure and how a postponed occurrence differs from a corrected start.

Approval: the owner's October 14 batch approval locks this specification. Execution begins only when assigned to the coding agent. No collector, source acceptance, or lifecycle transition has been executed by this document.
