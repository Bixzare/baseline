# SOURCE-001: Verify NBA source capabilities from cloud and local runners

Status: LOCKED by the project owner on October 13, 2026.

Prepared: October 13, 2026

Execution: [GitHub issue #3](https://github.com/Bixzare/baseline/issues/3), assigned after BOOT-001 PR #2 merged. Evidence and unresolved capability gates are in [the source report](../source-verification.md). Local-machine source probes remain pending; cloud evidence does not substitute for them.

Phase: 0. Priority: launch blocker. Dependency: BOOT-001 implemented and owner-reviewed, with a working Python 3.12 environment, PR CI, and the intended GitHub repository.

Session estimate: about 2 hours plus owner review, assuming representative endpoints respond. The spike is bounded; an access failure produces evidence and a fallback decision, not repeated endpoint debugging. Broader backfill and production adapters are separate issues.

## Goal and context

Determine whether Baseline can obtain historical player/team statistics, future schedules, current status, final box scores, and current rosters using the planned cloud and local paths. Produce reusable probe operations, reviewed fixtures, and a capability report with observed evidence. Do not assume a successful HTTP response or an installed package establishes usable data.

Baseline must publish player minutes, points, rebounds, assists, and threes made before October 20, 2026 at 19:00 UTC, targeting publication by 17:00 UTC. Team forecasting, ML training, the dashboard, and awards follow later. Source verification is the immediate priority after bootstrap.

Required guidance: AGENTS.md and `.agents/skills/hoop-data-quality/SKILL.md`; use `.agents/skills/hoop-python-testing/SKILL.md` for failure fixtures. This issue restates the source contract so it can be implemented without prior chat. Locked reference: [ADR 0001](../decisions/0001-verify-nba-sources-by-environment.md).

## Capability contract

Candidates below come from the approved design, not from measured endpoint success. Inspect the pinned nba_api interface and current primary documentation during execution, then record exact requests and parser versions. Do not guess a working future-schedule URL or imply scoreboard coverage extends beyond its observed response.

| Capability | Candidate and intended environment | Evidence required |
| --- | --- | --- |
| Historical player and team logs | nba_api LeagueGameLog for the 2025-26 regular season, locally only. | Stable game/player/team IDs, competition and season, minutes precision, five target fields, team scoring, null meanings, and sample identity joins. Report season coverage without claiming full backfill validation. |
| Future schedule | Permitted NBA/CDN schedule resource or supported schedule interface; test cloud and local execution separately. | 2026-27 season coverage, opening-night games, UTC start times, home/away identities, game status, and unknown or unscheduled slots. Today's scoreboard cannot substitute for this evidence. |
| Current scoreboard/status | nba_api live ScoreBoard, from the actual GitHub Actions runner and locally. | Source day interpretation, IDs, starts and status, genuine no-game behavior, and empty/failure distinction. |
| Final box scores | nba_api live BoxScore using an observed stored game ID, from cloud and locally. | Final status, player participation versus absence, precise minutes, counting stats, team totals, and supplied source timestamps. If only preseason evidence is available, label it rehearsal and retain the unverified regular-season limitation. |
| Current rosters | A permitted NBA roster resource; CommonTeamRoster is a local stats candidate. | Current team membership, season, stable player IDs, collection timestamps, and joins across schedule/box-score/history samples. A static player directory or previous final box score is not a current roster. New players may legitimately have no seed history. |
| Availability | Official injury reports only if dependable automated access and timestamped evidence can be established within the spike. | A usable target-season source, publication timing, parseable player/team/status identities, and access conditions; otherwise recommend explicit launch deferral with unknown availability. |

Historical detailed box scores are optional local requests only when the log sample lacks a required field. Do not request one for every game or run a full-season backfill here. Award labels and rules are outside this issue.

## Scope and execution sequence

1. Add and lock the needed nba_api dependency; verify Windows/Linux imports. Implement a thin NBA probe operation callable locally and from a manually dispatched GitHub Actions workflow. No automatic live probes on PRs.
2. Version request/parser configuration separately by environment. Use sequential requests per source, a configurable minimum three-second gap, a 30-second timeout, and at most two retries for temporary network/server failures. Honor a longer Retry-After within a declared run budget, or stop and report that the budget prevents a retry. These are project settings, not guaranteed NBA rate allowances.
3. Access-denied or bot-challenge responses stop that source's run and record failure. Never spoof identity, rotate proxies, alter identity to evade blocking, or send historical stats.nba.com requests from cloud runners. Reaching a request/time budget also stops with an explicit incomplete assessment.
4. Preserve raw bodies before parsing in an ignored local artifact/archive directory; store credential-free manifests and reports. Cloud workflow artifacts must be downloaded into that archive and verified by checksum before they count as retained evidence. Temporary workflow retention is not the durable archive.
5. Run a representative pass from the actual GitHub Actions runner, recording run URL, runner environment, code/dependency/configuration identity, requests, outcomes, and UTC observation times. Run the supported local paths separately. Sample relevant opening-night teams rather than fetching every roster in this spike; report exactly which teams were observed.
6. Repeat the bounded successful probes and preserve both observations, including legitimate changed bodies. Do not infer guaranteed uptime, a request allowance, or correction behavior from two samples. When a required example cannot be observed, mark it unverified and use a labeled synthetic fixture only for parser tests.
7. Produce a capability matrix: verified for the observed sample, failed, or unverified, with coverage limitations and evidence references for each environment. Recommend exact accepted source configurations for owner review, including cloud versus local routing and availability acceptance or explicit deferral.

## Evidence format and validation

Each fetch report records run ID, source/capability, environment, credential-free request identity, adapter/parser version, requested/received/validated times in UTC, source publication time if actually supplied, HTTP status if available, raw-body checksum and location, record count if known, and validation/failure reasons. Preserve failure metadata even when no body is available; missing records are not a zero-game result. Never infer a publication timestamp from an HTTP fetch time.

Validate required fields, types, null semantics, identities and joins, season/competition, timestamp interpretation, duplicate/conflicting keys, and target units. Unknown participation stays unknown. Zero outcomes require explicit supported DNP evidence; omission from a returned box score alone is not proof. Current-season preseason samples cannot enter the regular-season history or track record.

Source versions collected now cannot establish their availability at a past prediction cutoff. Keep source publication, collection, validation, and event times distinct. Historical availability assumptions and unknown revision history remain explicit in the report.

## Acceptance criteria

- [ ] A manual cloud workflow and a local command call the same tested probe operations; their exact commands and configuration are documented.
- [ ] Observed cloud/local evidence covers the required capabilities or identifies a specific failed/unverified gate. Cloud statistics requests and access-control evasion are absent.
- [ ] The report identifies exact season/date/team/game coverage and verifies opening-night schedule interpretation. No future-schedule or current-roster claim rests only on a scoreboard, player directory, or final participant list.
- [ ] Raw evidence and manifests survive repeated runs without overwriting earlier observations. Cloud evidence is retained locally with verified hashes.
- [ ] Fixtures and tests cover valid upcoming/completed examples, genuine versus synthetic no-game data, malformed or incomplete bodies, repeat/revision handling, and identity joins. Evidence labels distinguish observed samples from synthetic test cases.
- [ ] Request policy, budgets, temporary retries, Retry-After, access denial, and health/failure reasons are reproducible and tested. HTTP 200 with invalid content cannot pass a capability gate.
- [ ] The owner receives an actionable recommendation for each capability and for injury ingestion or deferral. A failed cloud capability that works locally recommends the Windows collector path with its awake/connected-machine dependency; scheduler implementation and rehearsal remain later tasks.
- [ ] README and Weaknesses.md reflect actual evidence and limitations. CI passes on fixtures without network access or production credentials. No ledger, production collector, database schema, or full backfill is included.

## Required tests

- Validate representative fixtures plus malformed JSON, HTML/bot challenges returned with HTTP 200, missing fields, duplicates, inconsistent IDs, invalid minutes, and explicit versus unknown participation.
- Test timeout, temporary server failure then success, exhausted retries, rate limiting with Retry-After, request-budget exhaustion, and immediate stop after access denial. Use mocked transport and clocks without fixed sleeps or live-source dependence.
- Test UTC date boundaries and timezone-aware conversion, season/competition classification, and an empty response that lacks evidence for a genuine no-game day.
- Verify distinct observations are retained when a source body changes and checksum validation detects altered archived bytes. No repeated request may overwrite earlier evidence.
- Leakage fixture: fetch a corrected record after an earlier cutoff, even if the record's event or claimed source time is earlier. Verify it cannot be reported as an observed input collected and validated before that cutoff. A current final box score cannot become evidence for a prior forecast roster.
- Run the real cloud/local probes separately and save their outcomes. Fixture checks passing do not establish source access. Unknown or failed capability evidence must remain visible when tests pass.

## Dependencies, failure decision, and likely files

An implementation PR may satisfy this issue by delivering the tested probe and truthful failure report. Dependent production collection remains blocked for any missing required capability. If a source fails in both environments, moving the same request locally is not a remedy; request an owner source or coverage decision. Do not silently reduce the player population. A verified local-only path needs the later fallback rehearsal before operational acceptance.

Likely files: `pyproject.toml`, `uv.lock`; `src/hoop/domains/nba/sources/` for probe/configuration/validation; small shared provenance helpers under `src/hoop/platform/` if needed; `configs/sources/`; `.github/workflows/source-probe.yml`; `tests/unit/`, `tests/leakage/`, and reviewed `tests/fixtures/nba/`; `docs/source-verification.md`, README.md, AGENTS.md for verified commands, and Weaknesses.md. Raw bodies and large reports stay in ignored data/artifact paths. The executable source/backfill notebook is delivered with the later backfill issue using these same operations.

## Handoff

Return the PR and real workflow links, capability matrix, retained evidence manifests, exact commands/check outcomes, request budget used, unresolved gates, availability recommendation, and why the recommended cloud/local routing follows the observed evidence. Explain one failure case and the limit of historical timing evidence. Source acceptance and any scope revision require owner review; the implementation agent must not claim Phase 0 complete from this spike alone.

Approval: the owner explicitly said "lock" on October 13, 2026. This finalizes the specification; a separate assignment to the coding agent starts execution. No live probe or source acceptance has been performed by this planning record.
