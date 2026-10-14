# SOURCE-001 capability assessment

Execution: [issue #3](https://github.com/Bixzare/baseline/issues/3), after merged
BOOT-001. No source configuration is accepted for production by this report.
Required source gates remain unresolved; fixture tests do not establish access.

## Observed evidence

The [manual GitHub Actions run](https://github.com/Bixzare/baseline/actions/runs/38640987630)
used commit `d17c75bbad83c25a5093e46febd7fa7326c236b7`, nba_api **1.11.4**,
and cloud configuration `source-config-v1-cloud`. It received **HTTP 403 / Access
Denied** on the candidate schedule request on October 14, 2026, at
21:32:10.569842 UTC. The cloud-development runner separately received HTTP 403
at 21:32:04.457456 UTC. Each assessment used **1 of 16 requests**, no retries,
and less than one second of its 180-second budget. Access denial stopped the CDN
source for the rest of that assessment. No successful observations could be
repeated. Scoreboard and box-score access were not tested after denial; they did
not themselves return an observed 403. No game IDs, teams, opening-night games,
season coverage, genuine no-game day, or current roster were verified live.

The manually dispatched run's Linux and Windows offline CI jobs passed their
then-current 98 tests and kernel/import checks. The live probe job correctly
failed with exit 1 and still uploaded failure evidence. Subsequent snapshot,
budget, and local-routing fixes are covered by the final PR's 106-test suite;
the evidence retains the exact original code/configuration identity. The blocked
source was not retried merely because code changed.

Retained archive locations in the current cloud workspace:

- GitHub: `artifacts/source-cloud-38640987630/7957f5772c3b494a84fe42e98038a6c0/`.
- Cloud development: `artifacts/source-development/855fd40ad1e64bf2ae05a7b33b926103/`.
- Each contains `identity.json`, `assessment.json`, three immutable observation
  manifests, and the raw denied response. Skipped observations have no HTTP
  status, body, received time, or record count; they are not zero-game responses.
- GitHub ZIP SHA-256:
  `a0ffb083ecd8a41ca584293ac9d1424396f6d802d9ae9beef12bc029bef58da0`.
- GitHub raw denied-body SHA-256:
  `92c9be194139c893fe57e0f58e7d10c0061152a3e2dbc4483eca2547dd69bd47`.
- Cloud-development raw SHA-256:
  `b3cad5f4b3aeb5c339eef6471c01e4f5df4348723ab134246a4b5a27fd25bd5a`.

The GitHub artifact was downloaded through the supported artifact REST API; its
ZIP digest and all raw-body hashes were verified before counting it as retained
evidence. These files are ignored and are not in Git. Preserve/export this archive
before discarding the workspace. A workspace copy is not an independently
verified off-device backup; 14-day Actions retention is not the local archive.

## Capability matrix and recommendations

| Capability | GitHub Actions / cloud development | Actual local machine | Recommendation / gate |
| --- | --- | --- | --- |
| Historical player/team logs | Unverified; cloud stats requests are prohibited and absent. | Not run. | Verify bounded 2025-26 regular-season LeagueGameLog samples for P and T locally; inspect MIN precision, null meanings, coverage, and joins. No full-season backfill claim. |
| Future schedule | Candidate CDN resource failed with HTTP 403 on both cloud runners. | Supported local ScheduleLeagueV2 interface is configured but not run. | No opening-night/season acceptance. Obtain local evidence or review a different permitted source; do not assume the same denied CDN request works locally. |
| Current scoreboard/status | Unverified; source stopped after schedule denial. | Not run. | nba_api live ScoreBoard is a documented candidate, not an accepted adapter. Verify current NBA Eastern day and independent evidence before declaring zero games. |
| Final box scores | Unverified; no completed game ID from a retained valid source. | Not run. | Probe only a discovered, retained final game ID. Preseason evidence is rehearsal and cannot establish regular-season behavior or a forecast roster. |
| Current rosters | Unverified; no validated CDN roster adapter selected. | CommonTeamRoster configured but not run. | Sample the first two team IDs from verified opening-night evidence. Do not substitute a player directory or final participants; no team population is silently reduced. |
| Availability | Unverified; no dependable target-season automated adapter selected. | Not run. | Recommend explicit launch injury deferral, subject to owner review. Availability remains unknown, never healthy by default. |

No player/team identity joins were demonstrated live. All seven JSON fixtures are
explicitly synthetic. No supported local path has been observed to work, so the
Windows collector cannot yet be recommended as an accepted fallback. If local
probes work while cloud access remains denied, propose that route with its awake,
connected-machine requirement and the later scheduler/fallback rehearsal. If
required capabilities remain unavailable, an owner source/coverage decision is
required before dependent collection or launch. This spike does not complete
Phase 0 and does not start DATA-001.

## Interfaces and request contracts

The pinned [nba_api v1.11.4 source](https://github.com/swar/nba_api/tree/e0295f8333c3496b5754dbffbdf4c1c1dee3c2f4)
was inspected. ScoreBoard and BoxScore URLs come from its live endpoint constants.
Local LeagueGameLog, CommonTeamRoster, and ScheduleLeagueV2 requests are generated
from its parameter interfaces with `get_request=False`; the shared transport
preserves bytes and status before parsing. Package imports and request generation
are tested on Linux and hosted Windows; actual local Windows source access and
interactive kernel selection remain pending.

The CDN schedule resource is a candidate identified in
[nba_api issue 296](https://github.com/swar/nba_api/issues/296); its historical
example is not current source acceptance. Current primary NBA schedule-page
inspection was denied, and the candidate resource itself was denied in both
cloud contexts. Browser-impersonating headers from examples were not copied.
The transport identifies itself as `Baseline-source-probe/0.1`, uses normal TLS
verification, follows no redirects, and never rotates proxies or changes identity.

Requests are sequential per assessment, with at least three seconds between
completed requests, a 30-second timeout capped by remaining time, at most two
temporary retries, 16 total requests, a 180-second run budget, and an 8 MiB body
limit. A truncated prefix is retained but cannot validate. Retry-After seconds
or HTTP dates are honored; malformed values or a delay beyond budget stop the
retry. Denial or HTML challenges stop that hostname's assessment. These settings
are project limits, not a guaranteed NBA allowance. No stats.nba.com request is
permitted in cloud environments.

Manifests keep request, received, validation, and completion times separate.
Publication time stays null unless verified source semantics establish it.
Supplied naive `meta.time` values remain uninterpreted. Minutes preserve reported
precision; omission from final participants never creates a zero outcome. Only
explicit supported DNP evidence can yield a zero, and a final participant list
cannot establish the roster known before a forecast. A later-collected correction
cannot become an observed input before an earlier cutoff even if its event or
claimed source time is earlier.

## Commands

From the repository root, the tested manual entry point for this review branch is:

```bash
gh workflow run ci.yml --repo Bixzare/baseline --ref source-001-capability-probes -f source_probe=true
```

It explicitly invokes the reusable source workflow. After owner merge,
`gh workflow run source-probe.yml --repo Bixzare/baseline` is the dedicated manual
entry point. Live probes do not run on PRs or on ordinary CI dispatches without
the opt-in input. Both paths call the same Python operation. Do not repeat the
known-denied source without a meaningful access/source change.

On an **actual local machine**, after `uv sync --locked`:

```powershell
uv run --locked python -m hoop.domains.nba.sources.probe --environment local --confirm-local-machine --config configs/sources/local.json --archive artifacts/source-local
```

This local command is documented and fixture-tested, not observed to succeed
against live local sources. It requests a supported 2026-27 schedule, current
scoreboard, a discovered final game, a 2025-26 April 10-12 player/team log sample,
and at most two roster teams derived from verified opening-night games. No roster
is requested if the opening-night team sample is unverified. Each invocation
creates a new run directory, preserves earlier versions, and repeats successful
requests within the shared budget. Cloud/local source configurations remain
candidates for owner review.

The source archive verifier was exercised on both retained cloud archives:

```bash
uv run --locked python -m hoop.domains.nba.sources.probe --verify-archive --archive artifacts/source-cloud-38640987630/7957f5772c3b494a84fe42e98038a6c0
uv run --locked python -m hoop.domains.nba.sources.probe --verify-archive --archive artifacts/source-development/855fd40ad1e64bf2ae05a7b33b926103
```

Each verified three observations and its raw-body checksum. Routine PR checks
remain the commands in AGENTS.md. The final suite has 106 tests, including five
cutoff/leakage tests, with no live network. An autouse test guard rejects socket
connections. Retry, timeout, denial, invalid HTTP 200 content, malformed/duplicate
records, joins, UTC boundaries, unknown participation, repeat/revision retention,
checksum tampering, budget exhaustion, and source routing have deterministic
coverage. Database and production scheduler tests belong to later issues.

Failure scenario: a CDN response is HTTP 200 with a challenge page. Raw bytes are
retained, the source is stopped, no data is accepted, and the assessment fails.
Changing headers or retrying another path to evade the challenge is not a remedy.
