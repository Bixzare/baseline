# SOURCE-001 capability assessment

Execution: [issue #3](https://github.com/Bixzare/baseline/issues/3), after merged
BOOT-001. No source configuration is accepted for production by this report.
Required source gates remain unresolved; fixture tests do not establish access.

Current owner steering: compare both Kaggle historical candidates after the
successful local nba_api diagnostic. The October 24 [dataset comparison draft](dataset-comparison.md)
inspects pinned files and supersedes the description-only comparison below.
Eoin version 525 is preferred pending acceptance checks; Wyatt version 238's
published contents do not establish the required recent player history.
No source is adopted by that assessment. API-SPORTS work remains on hold.

## October 25 resumed execution

The owner authorized incorporating the [historical-data strategy](PRD-data-source-amendment.md)
and resuming issues sequentially. SOURCE-001 remains in progress in PR #4.
The reusable `hoop.domains.nba.sources.bulk_history` assessor verifies pinned
CSV hashes, required schema, IDs, targets, participation distinctions, joins,
and score consistency without network access or edits to raw files. It reports
quarantine/repair items and refuses a completeness claim without a separately
collected expected-game inventory. It never accepts a source automatically.

The observed snapshot assessment is retained at
`artifacts/source-bulk/266d94cf4e094533ad650e53bcacab8a/assessment.json`:
1,230 valid game records, 2,460 valid team rows, 26,648 positive-minute player
rows, 5,528 outcome nonparticipation comments, 131 ambiguous zero-minute rows,
and two unknown-minute rows. It records 265 repair/quarantine items; these are
items, not necessarily 265 distinct people or missing appearances. Coverage
remains unknown because the separate expected-game inventory has not been
accepted. Collected times come from the October 24 download manifests; the
October 25 assessment does not backdate historical availability.

Offline fixture command from the repository root, with an unused output path:

```powershell
uv run --locked python -m hoop.domains.nba.sources.bulk_history --root tests/fixtures/nba/eoin-history --manifest tests/fixtures/nba/eoin-history/manifest.json --expected-inventory tests/fixtures/nba/eoin-history/inventory.json --report artifacts/bulk-fixture-report.json
```

Create the ignored `artifacts/` parent if absent. The output is created exclusively;
an existing report cannot be overwritten. Omitting `--expected-inventory` reports
unknown coverage and exits 1. A passing synthetic fixture is not source evidence.
The same assessor runs in the default offline path of `test.ipynb`.

The first release explicitly defers injury ingestion. Current schedule/status,
roster, final-result, production header-policy, and actual fallback/recovery
gates are still unresolved. The October 20 target is past; no missed prediction
is recreated as a live forecast. DATA-001 follows owner review of historical
interfaces and later seed acceptance, not the mere publication of its issue.

## Latest result: approved stock-client local notebook test

On October 15 the owner explicitly approved one bounded local test of the
installed package's unchanged defaults. This exception applies to diagnosis
only; it does not approve a production header policy or bypass other source gates.
The fresh project Jupyter kernel used Python 3.12.14 and nba_api 1.11.4.
`LeagueGameLog` used its normal session and headers, with no header/proxy
arguments, session replacement, hooks, copied cookies, or configured retries.
`get_request=False` retained the object before its normal `get_request()` call,
so a native parser failure could still be inspected. The earlier honest-header
probe was disabled, and no CDN request was repeated.

| Historical sample | Started UTC | HTTP | Validated rows | Elapsed |
| --- | --- | --- | --- | --- |
| 2025-26 Regular Season, April 10-12, players | 2026-10-15 21:09:47 | 200 | 636 | 2.093 seconds |
| Same season and window, teams | 2026-10-15 21:09:52 | 200 | 60 | 2.579 seconds |

Both passed the existing nonempty/schema, requested season/date, identity,
duplicate, minutes, and counting-stat validation. Nullable targets remain
unknown. This demonstrates **working local historical access with stock defaults**.
The earlier failures do not justify rejecting nba_api as technically unusable.
The changed header configuration is a plausible explanation, but these sequential
tests do not isolate the responsible header or rule out a time-dependent change.

Evidence: `artifacts/notebook-history-stock/ecb4ebeb757f4e459465e0d71c47d170/`
contains identity, exact URLs/contexts, result timestamps, decoded response text,
the tested notebook snapshot, and execution script. The notebook snapshot and
both response SHA-256 hashes were verified. Responses exposed by the native
client are decoded text re-encoded as UTF-8, not original wire bytes. This is
diagnostic evidence rather than an approved production ingestion archive.
The executed notebook is retained at
`artifacts/notebook-revisions/20261015T210943Z-stock-executed.ipynb`.
The editable `test.ipynb` remains clean and offline by default.

Next gate: owner review of whether unchanged package defaults are acceptable for
ongoing collection, then full-season completeness and production archive checks.
No collection-policy change, full backfill, or source acceptance has been made.
Cloud schedule access, current rosters, and live result capabilities remain
separate unresolved gates. Alternatives remain paused.

Offline validation now includes 131 passing tests, with 15 notebook checks.
The new boundary tests verify unchanged defaults, valid samples, timeout,
HTTP 403/HTML, malformed data, and stop-on-failure behavior without live requests.

## Earlier nba_api fit audit under the retained rules

The audit below predates the explicitly approved stock-client test above.
Its exclusion of stock defaults is historical, not the current test status.

The owner requested assurance that nba_api had been properly tested before
considering replacement. The final comparison removed Baseline's diagnostic
wrapper entirely: a fresh project Python process called the documented
`LeagueGameLog(...)` constructor directly with season 2025-26, Regular Season,
player mode P, and April 10-12 date bounds. Only the supported timeout and honest
header arguments differed from the interface defaults. No project modules were
imported, no response hook ran, no session was injected/replaced, and package
debug/cache modes were disabled. The native client created its normal session.

Run `511c029ed4fd4ed48d1910c8301166fb` began at October 15, 2026, 20:35:26.565374
UTC and failed after 20.578 seconds with `requests.exceptions.ReadTimeout`,
caused by urllib3 ReadTimeoutError and a socket TimeoutError. No HTTP response
was available, and the native response parser was not reached. The result
records zero response hooks and a previously uninitialized session. Evidence
and the exact standalone diagnostic script are retained under
`artifacts/source-minimal-native/511c029ed4fd4ed48d1910c8301166fb/` with script
and dependency-lock hashes. This deliberately uninstrumented test is diagnostic,
not an ingestion path; any successful response would require separate raw-byte
retention and validation before source acceptance.

| Fit question | Evidence / status |
| --- | --- |
| Is this merely a Jupyter or Baseline wrapper failure? | The direct native call without project imports/hooks/session replacement also times out. |
| Is the client missing or the interpreter wrong? | Pinned nba_api 1.11.4 imports in the project Python 3.12.14 environment. |
| Is basic HTTPS broken? | Local DNS, TCP, verified TLS, and an independent Python HTTPS control succeed. |
| Is only one HTTP implementation or address family affected? | urllib, native Requests, and standard Windows curl fail; curl fails over both IPv4 and IPv6. This does not test every protocol/client combination. |
| Are the original query parameters the only explanation? | The exact browser-observed LeagueGameLog query also timed out with honest identification. |
| Is only bulk LeagueGameLog affected? | The documented per-player and per-team native queries also timed out. |
| Does the historical data exist for website viewing? | Owner confirmed 2025-26 regular-season player rows load in the browser. This is not backfill acceptance or completeness evidence. |
| Does the live CDN work from this local client? | The observed browser scoreboard URL returned a recorded local HTTP 403. Stop further denied CDN requests. |
| Have package-default browser headers been tested? | No. The owner explicitly retained the rule excluding them. Native-client tests use honest overrides; unchanged package defaults have not been ruled out technically. |
| Are required schemas, full coverage, joins, freshness, and repeatability proven? | No accepted programmatic samples. These downstream acceptance checks are blocked by access, not silently passed. |

Conclusion: **nba_api has not demonstrated an acceptable operational route under
Baseline's current rules and environment.** That is sufficient to keep source
acceptance blocked. It is not proof that nba_api cannot work in any configuration
or that every NBA endpoint is inaccessible. It would be inaccurate to call the
stock header configuration tested. The owner's retained no-spoofing rule remains
in force; a general instruction to finish assessment does not reverse it.

No further blind request is queued. The remaining non-technical path is reviewed
provider/maintainer guidance about supported programmatic identification and
access. A sanitized draft is included below and has not been sent. Reassess only
if that guidance or another concrete relevant change supplies a new hypothesis.
Provider or Kaggle testing waits for the owner's source-direction decision.

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

## Local native client retest, October 15

The revised `test.ipynb` uses the documented native `LeagueGameLog(...)`
constructor and `league_game_log.get_data_frame()` interface in nba_api 1.11.4.
Its supported `headers` option keeps Baseline's identity; no browser identity or
proxy was added. A response hook preserves payloads before native parsing, and the
shared policy still limits retries, request count, and spacing. The package's
normal response buffering remains a diagnostic limitation, not a production
download guarantee. Existing urllib probe evidence was preserved separately.

Actual local Windows run `e47b08bdc1f4461cb2e61c2698a13594` started at
2026-10-15T19:33:41.134516 UTC, using Python 3.12.14. Both the player and team
2025-26 April 10-12 regular-season requests failed with `ReadTimeout`. Each had a
30 second timeout, no retries, and no HTTP response. Two requests were sent;
neither sample was accepted. The archive verifier confirmed both immutable
failure observations. No response body exists to checksum, and missing row counts
do not mean zero games. The notebook/helper hashes, dependency lock hash, headers,
and exact parameters are in the run's `identity.json`; these notebook/helper
changes were uncommitted when executed, so the recorded Git commit alone is not
their complete identity.

Local retained evidence:
`artifacts/notebook-history-native/e47b08bdc1f4461cb2e61c2698a13594/`.
The owner's executed notebook before revision is preserved under
`artifacts/notebook-revisions/`. These ignored files are local evidence, not
committed artifacts or a verified independent backup. The 123 offline tests pass,
including native client success/failure fixtures and fresh-kernel notebook
execution. Those tests do not establish live access.

This rules out treating the original urllib transport as the sole demonstrated
failure. It does not identify a timeout's cause, prove a server denial, or test
the library's browser identity. Check local DNS, TLS, and intended network/proxy
configuration before proposing further requests or a permitted source change.
Historical collection remains blocked. Cloud schedule access is a separate gate.

## Layered local diagnosis, October 15

The owner requested further diagnosis before rejecting `nba_api`. A separate
diagnostic began at 2026-10-15T19:42:03.300914 UTC on the same Windows computer and
project Python 3.12.14 environment. It retained the existing source configuration;
no dependency, certificate, firewall, DNS, proxy, or adapter setting was changed.

| Check | Observed result | Interpretation |
| --- | --- | --- |
| Installed client | nba_api 1.11.4, Requests 2.34.2, urllib3 2.8.0; project interpreter | Not a missing package or wrong interpreter in this diagnostic. PyPI also lists 1.11.4 as the current release when checked. |
| Request contract | LeagueGameLog, regular season 2025-26, player/team selector P/T, April 10-12, league 00 | Parameters match the documented interface. The endpoint document's last validation is August 2020, so it cannot prove today's service behavior. |
| Proxy configuration | No effective Requests proxy for stats.nba.com or pypi.org; Windows proxy/PAC flags absent | Owner subsequently confirmed a home/personal connection with no VPN. A transparent network filter or security product is not excluded. |
| DNS | stats.nba.com and cdn.nba.com resolve to IPv4 and IPv6 addresses | Name resolution works. No alternate DNS service or pinned IP was used. |
| TCP | Ordinary port 443 connections to stats.nba.com, cdn.nba.com, and pypi.org succeed | These hosts are reachable at the connection layer. This does not prove HTTP access or exclude filtering after the connection. |
| TLS | All three handshakes succeed with certificate verification and TLS 1.3; NBA certificate issuer is GeoTrust/DigiCert | No certificate or initial TLS negotiation error was observed. No verification was disabled. |
| Control HTTPS | Python Requests HEAD to pypi.org returns HTTP 200 in about 0.61 seconds | Python HTTPS works for a separate known service. The returned UTC date agrees with the diagnostic time. |
| Independent HTTP client | Standard Windows curl 8.21.0 / Schannel, same NBA history URL and Baseline identity | A different client also fails, so the notebook, nba_api response parser, and Python HTTP implementation are not sufficient explanations for all failures. |
| Default address family | curl connects over IPv6, completes TLS in 1.00 second, sends its request, then times out at 15.01 seconds with no HTTP status or response bytes | Failure is after connection/TLS, before an HTTP response is observed. |
| IPv4 comparison | One curl request to the same hostname with IPv4 selected completes TLS in 0.48 second, then times out at 15.02 seconds with no HTTP status or response bytes | The observed failure is not confined to IPv6. No IP rotation or system IPv6 change was used. |

This diagnostic made **two NBA data requests total**, with the same honest
identity and query as the earlier probe, no retries or redirects, and a 15 second
limit each. Its other NBA operations were DNS/TCP/TLS checks without HTTP data
requests. No CDN HTTP request or cloud request was made. The curl traces show the
requests were sent and also record TLS renegotiation; the latter alone does not
identify the cause. No response body was received to classify as JSON or a
challenge. Increasing timeouts, reinstalling Jupyter, changing parsers, or
disabling certificate verification has no supporting evidence as a remedy.

The observed boundary is **HTTP response delivery**. A silent upstream access
policy, a temporary service/edge failure, or filtering on the local network path
remain hypotheses. There is no HTTP 403, 429, or server message establishing
which one applies, and no evidence proving a global NBA outage. This is not a
permanent rejection of nba_api, nor proof that all endpoints/configurations fail.
Native requests retain Baseline's honest headers; the package's browser identity
has intentionally not been tested under the owner's no-spoofing rule.

Evidence and checksummed diagnostic scripts:
`artifacts/nba-connectivity/6bd6c675ac204246b45cd136366af0fd/`.
`connectivity.json` contains version, sanitized configuration, DNS, TCP, TLS, and
control results. `curl-result.json` and `curl-ipv4-result.json` contain timings;
the corresponding header/verbose files preserve request traces. `manifest.json`
records file checksums. These are ignored local artifacts, not an off-device
backup. Diagnostic scripts make live connections and are not routine CI tests.

Owner follow-up: the computer uses a **home/personal connection with no VPN**,
and **actual NBA stats rows load in the normal browser** on that connection.
These are owner-reported observations, not an independently captured browser
trace. They make a general website outage or basic connectivity fault less
likely, while leaving endpoint-specific behavior and request/session handling
unresolved. A working browser aggregate stats page does not prove access to the
historical LeagueGameLog endpoint. No new HTTP request was made from these
observations alone.

### Browser scoreboard comparison

The owner supplied browser metadata for
`https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json`:
GET, HTTP 200, Content-Type `text/plain`, response date October 15 at 19:52:04 UTC,
and Last-Modified 19:51:56 UTC. This is the live ScoreBoard URL defined by the
installed nba_api client, not the historical LeagueGameLog endpoint on
stats.nba.com. The selected metadata identifies the current score strip; it does
not identify the request supplying historical player rows. A response body was
not supplied, so JSON structure, game records, and freshness semantics were not
independently validated from the browser evidence. Browser session values and
browser identity headers were excluded from files and were not replayed.

Based on this fresh browser observation, one bounded local comparison requested
the exact URL using Baseline's honest identity, no browser session, and the
existing shared transport. Run `d2cca44d173c43bbb8cc66ef4170c918` requested at
2026-10-15T19:54:18.473591 UTC and received **HTTP 403** at 19:54:18.792599 UTC.
The assessment stopped after one request, with no retries, accepted records, or
further CDN requests. The archive verifier confirmed its immutable observation
and denied-body checksum. Evidence:
`artifacts/source-local-cdn/d2cca44d173c43bbb8cc66ef4170c918/`.
Its `identity.json` retains only the safe browser metadata, comparison reason,
request identity, and dependency lock hash.

The observed browser 200 versus local programmatic 403 on the same URL establishes
different access outcomes for those clients, not the exact decision mechanism.
It does not establish that copying a cookie or headers would be permitted, and
it does not diagnose stats.nba.com's historical timeouts. Stop further CDN
requests under this assessment. The cloud schedule gate remains separate.

### Browser LeagueGameLog query comparison

The next browser observation identifies the same historical API host and path as
our history probe: `stats.nba.com/stats/leaguegamelog`. The reported response was
HTTP 200 with Content-Type `application/json; charset=utf-8`, dated October 15 at
19:57:24 UTC. Its query is **2026-27 Pre Season**, player mode P, with empty date
bounds. It does not establish 2025-26 regular-season access or accepted seed
coverage. Browser payload rows were not retained or independently validated.
Only public URL/response metadata was saved; session values were excluded.

| Parameter | Original historical probe | Owner-observed browser request |
| --- | --- | --- |
| Season | 2025-26 | 2026-27 |
| SeasonType | Regular Season | Pre Season |
| DateFrom / DateTo | April 10-12, 2026 | Both blank |
| Counter | 0 | 1000 |
| Direction | ASC | DESC |
| ISTRound | Absent | Blank |

The pinned LeagueGameLog wrapper and its endpoint documentation expose Counter
and Direction but do not expose ISTRound. Its appearance in this browser request
is an observation, not proof that the parameter is required or a reason to
silently change the production source contract.

One comparison sent the exact observed URL, including all query parameters and
their order, through the shared HTTP transport with Baseline's honest identity.
Run `dc60fbaa8a5f4b61bb12d4e0cbe1f39d` made one request with a 20 second timeout,
zero retries, and no browser cookies, browser identity, or Origin/Referer copied.
It failed with `TimeoutError`, no HTTP response, and no accepted records. The
archive verifier confirmed the single failure observation. Retained evidence:
`artifacts/source-browser-query-comparison/dc60fbaa8a5f4b61bb12d4e0cbe1f39d/`.
The identity file contains the exact URL, safe browser metadata, and comparison
limitations; the preseason diagnostic cannot satisfy regular-season acceptance.

Owner subsequently confirmed that the **2025-26 Regular Season player table
loads in the browser**. This establishes owner-observed historical viewing
access on the home connection, not independently validated rows, full-season
completeness, or a working programmatic backfill. No further header export or
live request was needed to record that distinction.

Matching the browser's query did not resolve programmatic access. This weakens
the hypothesis that the original parameter differences alone explain all
failures and strengthens request-context handling as a hypothesis. It still
does not identify the responsible server/network rule. No header, cookie, TLS
identity, or network rotation experiment is authorized by this finding. No
additional history request is justified merely by increasing retries or timeout.

### Online debugging review requested by the owner

The owner requested an online search for further nba_api debugging options before
assessing another service or a historical Kaggle dataset. Findings were checked
against primary project documentation, release notes, and current PR/issue pages.
Reported successes by contributors are not verified fixes for this computer.

| Option / primary reference | Finding | Baseline action |
| --- | --- | --- |
| [Release notes](https://github.com/swar/nba_api/blob/master/CHANGELOG.MD), [merged PR 636](https://github.com/swar/nba_api/pull/636) | Version 1.11.4 includes a default header update intended to repair broken requests; 1.10.2 also changed browser identity headers for timeout problems. | Version 1.11.4 is already installed. The native probes override its headers to keep Baseline's identity, so the stock header configuration remains untested. Installing the same version again would not exercise that fix. |
| [Live CDN PR 671](https://github.com/swar/nba_api/pull/671) | The contributor reports that adding an nba.com Referer restores live CDN access. The PR page is still Open when checked; it is not treated as a shipped fix. | Relevant to the local scoreboard 403, not proof of a historical fix. Applying a fabricated NBA Referer needs resolution against the owner's no-spoofing rule; it was not applied. |
| [Issue 678](https://github.com/swar/nba_api/issues/678), [open PR 679](https://github.com/swar/nba_api/pull/679) | Non-JSON denial pages can surface as misleading JSONDecodeError; the PR proposes explicit HTTP errors and includes the live Referer change. | Our probe already preserves status/body before validation and reports the 403 explicitly. Better error reporting does not itself grant access. Do not install the open PR as a verified repair. |
| [PlayerGameLog](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/playergamelog.md), [TeamGameLog](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/teamgamelog.md) | Documented per-player/per-team alternatives permit a smaller-query diagnostic than a league-wide log. | Tested once each locally during this review; both timed out without HTTP responses. Details below. |
| [PlayerGameLogs PR 629](https://github.com/swar/nba_api/pull/629) | Open proposal adds parameters to PlayerGameLogs, a different endpoint from LeagueGameLog. | Not a demonstrated fix for our failure. The exact browser LeagueGameLog query, including blank ISTRound, was already tested without success. |
| [Timeout discussion 652](https://github.com/swar/nba_api/issues/652) | Contributors describe browser-header and browser-session/TLS impersonation workarounds, with mixed subsequent results. | Anecdotal outcomes, not a supported access guarantee. Cookie/session replay, TLS impersonation, and proxy rotation remain excluded. |

The distinction between **native package calls with honest header overrides**
and **unmodified package defaults** is material. The former failed; the latter
has not been tested. It would be inaccurate to say we have exhausted every
nba_api configuration. The installed stats defaults claim a Chrome browser and
an NBA Referer. The owner was asked whether the existing rule should continue
to exclude these defaults or permit one bounded unchanged-default diagnostic.
This clarification comes from the owner's original instruction, not an approval
requirement invented by a skill. The owner chose **Keep current rule** after
reviewing these findings. Stock browser headers remain untested and excluded;
no additional NBA access experiments follow from the clarification.
Even a successful diagnostic would not establish source permission, completeness,
or operational acceptance.

The remaining honest-header endpoint diagnostic used native PlayerGameLog for
player 203999 and TeamGameLog for team 1610612743, both for the 2025-26 regular
season. Run `49116cd9fd9140938d06e00c2c5415d1` made two requests, no retries,
20 second timeouts, and at least three seconds between completed requests. Both
failed with ReadTimeout and no HTTP status or accepted data. No further endpoint
request followed. The archive verifier confirmed two observations. Evidence,
the exact diagnostic script/hash, query parameters, and identity are retained in
`artifacts/source-entity-comparison/49116cd9fd9140938d06e00c2c5415d1/`.
These operations do not change the collector, approved source, or notebook defaults.

With the current rule retained, the next assessment can compare another service
and a historical Kaggle dataset without adopting either. A historical dataset could
potentially cover the seed/backtests; it cannot by itself supply future schedules,
fresh rosters, or recurring 2026-27 outcomes. No dataset or provider was adopted.

### Preliminary alternative-source comparison after the policy decision

Status: assessment only. No source change, dataset acceptance, or DATA-001 start.
No further NBA endpoint request was made. The owner's retained no-spoofing rule
continues to exclude stock browser headers, cookie replay, TLS impersonation,
and proxy/network rotation.

Public Kaggle metadata and one file listing were retrieved without credentials
or dataset downloads. Raw responses, collection times, and checksums are retained
under `artifacts/kaggle-source-assessment/99c691e722dc48cc95cc8f1f8a8ec889/`.
The metadata API returned HTTP 200 JSON for both candidates. The rendered data
cards were empty in the research tool; the following facts come from the actual
retained publisher metadata, not search snippets or other projects' data copies.

| Candidate | Verified metadata | Assessment |
| --- | --- | --- |
| [Eoin Moore NBA box scores](https://www.kaggle.com/datasets/eoinamoore/historical-nba-data-and-player-box-scores) | Version 515, last updated June 15, 2026; publisher license label CC0: Public Domain; total dataset about 1.86 GB. The file listing includes PlayerStatistics.csv, TeamStatistics.csv, Games.csv, TeamHistories.csv, and 2025-26 schedule data. | First historical candidate to inspect. A June snapshot may cover the regular-season seed, but row coverage, target fields, identifiers, provenance, and license scope remain acceptance checks. No content/schema was downloaded or validated. |
| [Wyatt Walsh NBA Database](https://www.kaggle.com/datasets/wyattowalsh/basketball) | Version 238, last updated June 29, 2026; publisher license label CC BY-SA 4.0; total dataset about 4.66 GB. | Secondary candidate. Its broader database and different license terms add assessment work; the exact player-game table and seed coverage remain unverified. |
| [API-SPORTS API-NBA](https://www.api-football.com/news/post/how-to-get-started-with-api-nba-the-complete-beginners-guide) | Current provider guide advertises 100 requests/day and 10/min on Free, including schedules/results and player/team game statistics. | First operational-service candidate to probe. Exact season/field coverage, current-roster semantics, quota fit, and public-use conditions must be verified. No key is available in this process and no authenticated assessment ran. |

Both Kaggle descriptions claim daily updates, but the observed latest versions
are from June. Do not present them as fresh 2026-27 operational feeds. Publisher
license labels are recorded facts, not an independent finding about every
upstream right or permission. These are candidate sources until reviewed.

Proposed next evidence, not a locked routing decision:

1. Inspect only Eoin Moore's basic player/team/game/identity files from a pinned
   version, rather than downloading play-by-play and advanced tables. The listed
   basic player file is about 390 MB; no full download has been made here.
2. Validate actual five-target columns, minute units/precision, IDs and joins,
   regular-season coverage, null/duplicate behavior, and legitimate revisions.
   Participant-only archives do not reconstruct pregame rosters or justify
   turning missing rows into confirmed DNPs. Preserve collection/version identity
   and disclose historical availability assumptions.
3. Once the owner's APISPORTS_API_KEY is configured privately, run the bounded
   provider capability assessment already outlined in the alternative-source
   research. Check schedules, status, real current membership, and final player
   outcomes independently. Keep keys/account details out of evidence and logs.
4. Measure the daily quota against essential freshness before selecting Free.
   Fifteen-minute polling alone would consume 96 of 100 daily calls. Historical
   files may reduce backfill cost but add a provider identity-crosswalk gate;
   never assume Kaggle/NBA Stats IDs equal API-NBA IDs or join on names alone.
5. Bring a concrete source-routing ADR draft to the owner only after evidence
   supports the proposal. A historical snapshot plus a service is a candidate
   design, not yet an accepted replacement for the approved routes.

### Current diagnosis and next gate

The owner-input checks are complete: home/personal connection, no VPN, current
and historical browser tables load, and browser metadata identifies the same
LeagueGameLog endpoint. Local DNS, TCP, verified TLS, and control HTTPS pass.
Native nba_api, urllib, and Windows curl have failed to obtain history; curl
failed over both IPv4 and IPv6. Matching the browser query also timed out. The
local CDN comparison returned an explicit 403, while browser metadata reported
200. These observations support request-specific handling as a hypothesis, but
do not identify its mechanism or establish that every nba_api configuration fails.

No local repair has been verified. The online review identifies relevant upstream
header fixes, but the owner explicitly retained the rule excluding the stock
browser identity. More retries, another client reinstall, a longer timeout,
or parser edits are not currently justified. Browser session replay and network
rotation remain outside the owner's approved scope. Keep nba_api as an
investigated but blocked candidate, without declaring permanent unavailability
or accepting source access.

An official export was checked as a potential fallback. NBA's
[FAQ](https://www.nba.com/stats/help/faq) states downloads/CSV are unavailable,
including academic/personal use. No export fallback is accepted.

The stock-header choice is resolved: the existing rule remains. Source guidance
or the previously authorized evaluation of a permitted provider is preferable
to further blind endpoint experiments. A Kaggle snapshot may be assessed for
historical seed/backtests separately from operational capabilities. The
API-SPORTS/API-NBA evaluation remains contingent on privately configured account
credentials and actual coverage/permission evidence. No source change or accepted
collection adapter follows from this report. The cloud schedule problem still
requires its own resolution even if a historical source is accepted.

Sanitized draft for upstream guidance, not sent:

> On October 15, 2026, NBA player box-score rows for the 2025-26 regular season
> load in a normal browser on a personal Windows connection without a VPN.
> The browser also reports HTTP 200/application-json for LeagueGameLog on a
> 2026-27 preseason query. Local Python 3.12.14, nba_api 1.11.4, Requests 2.34.2,
> and urllib3 2.8.0 time out on history requests using a self-identifying client.
> The native endpoint interface, an exact browser-query comparison without
> browser credentials/identity, and standard Windows curl were tested. DNS, TCP,
> and verified TLS succeed; curl sends the request and receives no HTTP bytes
> over either IPv4 or IPv6. Separate control HTTPS succeeds; no proxy is
> configured. No browser-cookie, browser-identity, or protection-bypass experiment
> was performed. Is there a supported programmatic route for this use case that
> does not rely on browser impersonation or session replay?

Sending this draft or contacting a provider requires the owner's instruction.

The following diagnostic branches are retained as reference, not queued work:

1. Owner confirmed that the official Players Box Scores table loads for 2025-26
   Regular Season. Browser viewing access is established by that report; source
   acceptance remains unverified.
2. The same-host/endpoint question is resolved for the observed preseason request.
   Matching that query once also timed out programmatically. Preserve this
   distinction before proposing another adapter, query, or collection contract.
3. If the same endpoint works in the browser but the honest client still fails,
   request/session handling becomes a stronger hypothesis. Do not infer the exact
   rule from a timeout, copy browser identity or session credentials into Python,
   rotate networks/proxies, or disable security tools. Confirm that the notebook
   process has the same relevant configuration as the fresh diagnostic process.
4. If browser access works but honest programmatic requests still fail, seek
   provider/maintainer guidance on a permitted programmatic route. Drafting a
   sanitized report is possible; sending one requires the owner's instruction.
   Historical collection remains gated until a real sample validates.

Primary references checked during diagnosis:

- [Maintainers' endpoint and request options](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/examples.md).
- [LeagueGameLog parameter contract](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguegamelog.md).
- [PyPI release listing](https://pypi.org/project/nba_api/).
- [Requests timeout semantics](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts): a read timeout concerns receiving response bytes, not proof of DNS failure or an explicit access denial.
- [Project issue 696](https://github.com/swar/nba_api/issues/696): a reporter using 1.11.4 observed HTML errors October 8 and reported recovery October 10. That is evidence of a past incident, not a diagnosis of this computer's October 15 timeouts.

## Capability matrix and recommendations

| Capability | GitHub Actions / cloud development | Actual local machine | Recommendation / gate |
| --- | --- | --- | --- |
| Historical player/team logs | Unverified; cloud stats requests are prohibited and absent. | Both native client samples timed out October 15; no accepted data. | Diagnose local connectivity before any further request. MIN precision, null meanings, coverage, and joins remain unverified. No full-season backfill claim. |
| Future schedule | Candidate CDN resource failed with HTTP 403 on both cloud runners. | Supported local ScheduleLeagueV2 interface is configured but not run. | No opening-night/season acceptance. Obtain local evidence or review a different permitted source; do not assume the same denied CDN request works locally. |
| Current scoreboard/status | Unverified; source stopped after schedule denial. | Exact scoreboard URL returned HTTP 403 in the October 15 local comparison despite owner-supplied browser HTTP 200 metadata. | No accepted programmatic route. Stop denied requests; browser metadata is not validated status data or future-schedule evidence. |
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
