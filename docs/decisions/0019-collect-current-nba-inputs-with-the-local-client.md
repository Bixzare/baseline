# ADR 0019: Collect current NBA inputs with the local released client

Status: DRAFT, awaiting owner lock. Diagnostic permission does not approve ongoing collection.

## Evidence

The October 30 owner-approved local diagnostic made exactly six calls using
nba_api 1.11.4 unchanged defaults, no retries, 30-second timeouts and three-second
spacing. All returned usable JSON in 37.766 seconds. Retained checks identify
1,200 regular-season schedule records with resolved identities, a matching
ten-game scoreboard, two 18-player roster samples and matching final traditional
and summary box scores. See [the measured source report](../reports/2026-10-30-local-operational-sources.json).

Six additional NBA Cup quarterfinal/semifinal slots have team ID 0. Retain them
as pending, unforecastable slots. Their reported times do not establish a usable
matchup. Full eventual season coverage, upstream roster update lag, final
participation semantics and cloud NBA access remain unverified.

The protected cloud seed-lineage check on reviewed main passed in Actions run
41023497749. Historical seed acceptance and manual independent recovery are
separate evidence. Hosted seed import still requires its explicit approval.

## Proposed decision

1. Permit unchanged released nba_api defaults for bounded local operational
   collection and initial current-season catch-up, after implementation review
   and capability acceptance. Keep cloud stats.nba.com requests disabled.
2. Use ScheduleLeagueV2 for season discovery and backlog planning. Use verified
   daily ScoreboardV3 evidence for current start/status confirmation, so a full
   season response is not fetched at every publication check. Preserve unknown
   slots and date-range coverage; never infer an empty slate from failed retrieval.
3. Use CommonTeamRoster for observed team membership, preserving stable IDs and
   actual receipt times. Qualify roster completeness before accepting a route;
   availability and injuries remain unknown/deferred. Final participants cannot
   replace the saved pregame roster.
4. Use traditional/summary box scores together for final statistics and explicit
   inactive evidence. Zero minutes or missing rows alone never establish DNP.
   Preserve reported precision, unresolved outcomes and later corrections.
5. Before the first future-slate release, catch up verified completed 2026-27
   games since opening night. Bounded LeagueGameLog player/team inventories may
   seed that work; verify supporting event/team identities and missing targets.
   The accepted 2025-26 seed cannot hide missing current-season appearances.
6. Initially allow at most 16 endpoint calls and 180 seconds per local invocation,
   at least three-second spacing, timeouts at most 30 seconds and no immediate
   retries. Persist a denial stop until later owner-reviewed verification.
   Requests, bytes and runtime must be measured before enabling schedules.
   These are project budgets; no guaranteed provider rate limit is established.
7. Retain source bytes, checksums, request/receipt/validation times and parser
   identity through existing restricted artifact/database identities. Use shared
   locks/checkpoints and tested normalization. No copied browser cookies, custom
   browser identities, TLS impersonation, proxy rotation or access-control bypass.

## Tradeoff and release boundaries

This avoids another provider and ID mapping layer while retaining the free budget.
Collection depends on an awake, connected local machine. Cloud platform workers
consume verified uploaded facts; stale/missing essential sources block affected
publication. Show missed coverage rather than filling old forecasts afterward.
Schedule/status evidence must meet the 30-minute limit and roster evidence the
24-hour limit. The independent Windows delivery check currently failed; source
success does not pass recovery/notification readiness.

Owner lock would approve implementation and bounded manual source verification,
including current-season catch-up. Production route acceptance, hosted current
fact ingestion, persistent schedules, model activation and official publication
still require their reviewed contracts and activation gates. This ADR changes no
configuration or permissions by itself.

Required evidence: sanitized source fixtures; malformed/unknown/revised payloads;
Cup placeholders; UTC/league-date boundaries; roster/final membership separation;
late revisions/cutoffs; no traffic on defaults; denial persistence; complete
current-history windows; actual intended-environment upload/readback and measured
free-tier capacity. Keep production switches off until those checks and reviews pass.
