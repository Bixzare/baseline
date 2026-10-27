# Ongoing collection

COLLECT-001 provides shared schedule/status/roster operations, not a running
scheduler. `configs/collection.json` deliberately contains no accepted routes.
The existing cloud denial is unresolved; no new NBA requests were made here.
Fixture success does not authorize a route or establish hosted readiness.

## Acceptance and request budget

Each route records capability, credential-free URL, request context, parser
version, execution environment, observed verification identity and owner
acceptance ID. Its SHA-256 covers those exact request/parser/environment fields.
Changing a field requires review. Synthetic evidence is allowed only in rehearsal.
The context may declare verified source-time semantics and exact supported status
labels. Unknown generation semantics are not silently interpreted as timestamps.
Absent generation remains absent; receipt time does not prove source generation.

The shared SOURCE-001 runner enforces sequential requests, a three-second minimum
gap, 30-second timeout, two temporary retries and a default 16-request/180-second
budget. Denial stops the source immediately. Every real attempt preserves raw
bytes, receipt/validation time, source check, run and failure state. Repeated
bytes may reuse an object without reusing the observation timestamp. Storage
failure cannot become accepted evidence. Invalid empty responses remain failures;
an empty current scoreboard needs independently verified no-game evidence.

The seven-day work list comes from saved full-schedule occurrences, never only
today's scoreboard. Teams with roster evidence under 23 hours old need no renewal;
the one-hour headroom supports the 24-hour publication limit. The dispatcher must
use this renewal list when selecting reviewed routes. No all-team polling loop or
unattended workflow is installed here. Actual request/runtime/source freshness
measurements remain pending in each accepted local/cloud environment.

## Occurrences and lifecycle recovery

An upstream-game advisory lock serializes occurrence choice; observation insertion
also shares the publication occurrence lock. Ordinary corrections retain the
occurrence. A verified postponed occurrence followed by a later accepted full
schedule entry can create one linked successor, including reused NBA game IDs.
A unique predecessor index and stable IDs prevent duplicate successors. Missing
games, delayed starts and unknown/suspended labels do not establish postponement.
Old observations cannot be assigned to a newer occurrence; exact saved-check
replay returns to its original occurrence. Unsupported starts stay unknown.

Source observations commit before lifecycle append. If append fails, collection
reports incomplete and `batch_status` already sees exclusions. Retry
`append_pending_lifecycle` with the saved event/observation IDs without refetching
or rewriting forecasts. Lifecycle retries are idempotent. Later observations
cannot clear earlier invalidation or reopen a closed deadline.

## Commands

```powershell
uv run --locked python -m hoop.domains.nba.collection work --environment local --output artifacts/collection-work
uv run --locked python -m hoop.domains.nba.collection collect --environment local --output artifacts/collection --confirm-source-gates
```

Both use the existing restricted runtime database configuration; collection also
uses the separate private Storage identity. `collect` refuses the default empty
routes before opening a connection or request. Use `--config` only for reviewed
capability/environment routes. Local-only evidence can be uploaded for cloud
consumption while its original timestamps remain fresh; this is a dependency on
an awake local machine, not proof of fully cloud operation. Source failures never
authorize cloud stats access or a replacement roster from final participants.

Unit/real Postgres checks cover route identity, unknown/stale generation handling,
duplicate JSON, retained repeated bodies, denial, actual runtime roster writes,
Storage failure, concurrent successors and lifecycle recovery. The fixture clock
measures two requests with a three-second enforced gap; this is not a measured
live-source budget. Actual accepted-adapter rehearsal remains a release gate.
