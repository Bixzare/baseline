# Private artifacts and source evidence

DB-002 adds evidence persistence, a private artifact client and a SOURCE-001 report
bridge. The dedicated Free project now has reviewed migrations through 0008,
restricted identities and two private buckets. Windows sign-in/refresh and
create/read passed; three mutation checks remain inconclusive, and actual cloud
permission checks and capacity acceptance remain unverified. See the current
[hosted setup evidence](supabase-setup-status.md). Local fixture tests do not
establish hosted readiness or authorize production activation.

## Data flow and guarantees

1. Start a rehearsal or production run with code/config identity. The database
   supplies its start time. Append run events; terminal events include counts,
   duration and failure/incomplete reason when applicable.
2. Hash raw bytes, choose a content address under `raw`, `history`, `features`,
   `models` or `reports`, upload with overwrite disabled, then download and verify
   exact bytes/hash/size. The initial per-object bound is 16 MiB. Full historical
   CSV archives stay local; exceeding the bound fails explicitly.
3. Only after verified readback, register the canonical artifact descriptor in a
   short database transaction. No Storage or Auth request runs inside that
   transaction. Existing keys are read and verified before reuse. A lost upload
   response can recover through readback; replacement is never a recovery path.
4. Register each completed source attempt separately, including invalid responses
   or failures. Identical bytes can share one artifact while observations retain
   distinct IDs/times. Preserve the original requested/received/validated times.

`platform.runs`, `run_events`, `artifacts` and `source_checks` accept restricted
inserts and reads. Runtime cannot update/delete/truncate, own tables, change grants
or supply database creation/event times. Exact retries preserve contents; a
conflicting ID/URI fails. PostgreSQL enforces keys, foreign keys, accepted-input
ordering, raw-artifact kind, finite timestamps and nonnegative sizes/counts.
JSON summaries are objects bounded to 16 KiB, with credential markers rejected by
both Python and SQL. Write allowlisted operational metadata, never arbitrary
upstream headers/errors or environment dumps. Pattern checks cannot identify
every possible secret string.

The database validates artifact metadata; the client attests verified Storage
bytes. SQL alone cannot prove an external object's existence. Administrators and
a deliberately dishonest privileged writer remain outside that proof. Runtime
hash readback, restricted storage writes and independent backup provide the
approved operational protection, without a claim of external attestation.

An upload can survive a subsequent database failure. That object is unregistered
and cannot serve as accepted evidence. Retry the same bytes, verify the existing
object and finish registration. There is no automatic orphan deletion. If Storage
fails, source persistence records `storage_failure` without a fictional artifact.
If the database also fails, it returns failure and saves only a sanitized local
report with `durable_recording_confirmed: false`.

## Source states and timing

| State | Meaning |
| --- | --- |
| `accepted` | Known receipt and validation, verified raw artifact, known nonnegative count. A validated empty response has count 0. |
| `invalid` | Response arrived but failed validation. Retain raw bytes when possible; successful validation stays null. |
| `transport_failure` | No response. Receipt, HTTP status, count and artifact stay null. |
| `storage_failure` | Required raw retention failed. Receipt/status/count retain only what was actually known. |
| `unverified` | An attempt has no accepted validation; it cannot supply features. |

`hoop.platform.evidence.known_by` requires accepted evidence with request,
receipt and validation in order by the cutoff, and no known later publication.
An older event/publication timestamp cannot make a late correction available
earlier. Unknown publication does not waive receipt/validation. Consumers must
also select the correct run environment and approved source capability; a
rehearsal fixture is not current production health.

`hoop.domains.nba.sources.persist.persist_observation` imports one saved probe
observation and its checksummed raw body without fetching NBA data. It preserves
original timing and labels archived rehearsal provenance. A skipped request has
no request time and must be an incomplete run event, not an invented attempt.
The domain bridge depends on shared platform contracts; the platform imports no
NBA parser or columns. Generic tests use a synthetic card-game source.

## Authentication and controlled setup

The client uses Python 3.12.14's HTTP library with a typed transport boundary.
This keeps dependencies small and supports deterministic fault tests. Compatibility
with the provider's REST API is consequently an explicit hosted check. Requests
use HTTPS, a verified Supabase project host, no redirects, bounded body/timeout,
and at most two Auth attempts on temporary refusal. Each job owns its own memory
session and refresh token. Renewal failure stops the operation. There is no
administrator fallback, shared session file or global sign-out.

Configure variables privately. `Settings` hides key/email/password in its repr.

| Variable | Purpose |
| --- | --- |
| `BASELINE_SUPABASE_URL` | Actual HTTPS project URL. |
| `BASELINE_SUPABASE_PUBLISHABLE_KEY` | Public publishable key, never a secret/service key. Legacy key forms are not enabled without verification. |
| `BASELINE_ARTIFACT_EMAIL`, `BASELINE_ARTIFACT_PASSWORD` | Dedicated backend Auth credentials. |
| `BASELINE_ARTIFACT_USER_ID`, `BASELINE_ARTIFACT_BUCKET` | Verified UUID and private bucket; default bucket is `baseline-artifacts`. |
| `BASELINE_MIGRATION_DSN`, `BASELINE_SUPABASE_ADMIN_KEY` | Controlled setup only; remove from ordinary jobs. |
| `BASELINE_RUNTIME_DSN` | Separate restricted evidence database writer. |

After owner review and project setup, apply repository migrations using DB-001
tooling. Migration 0003 uses the privileged connection only to install Storage
policies, preserving provider table structures. It refuses missing/disabled
provider row security and preexisting object/bucket policies that could broaden access.
It never applies `tests/fixtures/postgres/provider.sql` to a hosted project.
That file is disposable test scaffolding for provider tables and `auth.uid()`.

Then, in the project environment:

```powershell
uv run --locked python -m hoop.platform.artifacts setup
uv run --locked python -m hoop.platform.artifacts verify
```

Controlled setup uses supported administrator APIs to find/create the dedicated
identity and private bucket, verifies backend sign-in, and appends a nonsecret
database binding. Omit `BASELINE_ARTIFACT_USER_ID` only for the first setup; the
operation returns the UUID to configure afterward. Repeat setup preserves that
identity and matching binding. Public/mismatched buckets or identities fail.
It also verifies a separate private negative-test bucket, default
`baseline-denied-rehearsal`, configurable as `BASELINE_OTHER_ARTIFACT_BUCKET`.

Before `verify`, configure a different, verified Auth test identity privately as
`BASELINE_OTHER_ARTIFACT_EMAIL`, `BASELINE_OTHER_ARTIFACT_PASSWORD` and
`BASELINE_OTHER_ARTIFACT_USER_ID`, through controlled provider administration.
This is a test identity with no artifact binding or dashboard login. Both
identities must authenticate. A missing/invalid prerequisite fails verification.
The command uses small unique fixture objects and attempts read/create plus
replacement, upsert, delete, move, bucket administration, unrelated-bucket access,
private Data API access, anonymous access and access as the other identity.
Unexpected success fails the report; original-byte readback is checked afterward.
Generic 404 mutation failures do not count as demonstrated authorization denial.

The manual `artifact-check.yml` workflow uses only backend/negative-test credentials
in protected `artifact-rehearsal`, never migration or admin credentials. Run the
same command from Windows and actual Actions after reviewed setup. Save both
reports. No automatic cleanup is authorized for the runtime writer. Administrator
maintenance of rehearsal objects is a separate reviewed operation.

Rotate a backend password through supported controlled Auth administration, update
job secrets, then verify fresh sign-in and independent session renewal. For
identity replacement, configure its verified UUID and rerun controlled setup to
append the new binding. Do not assume password rotation immediately revokes every
issued token; verify provider behavior and revoke old access through the binding
and supported administration. No change to an existing ledger is involved.

## Local evidence and remaining gates

Real Postgres tests execute the actual migrations and policies against isolated
provider relation/claim fixtures. HTTP tests cover expiry/renewal, refused sign-in,
bounded retries, independent sessions, existing/concurrent keys, lost responses,
corrupt readback, upload refusal and database failure after upload. A real API
could differ from these fixtures; that remains a hosted release gate.

The October 25 synthetic rehearsal used run
`5dcf3cd8-f4d2-49f1-b595-09ef8c8912fc`, with accepted empty, invalid and transport
failure checks. The two mock objects totaled 22 bytes; hashes were
`44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`
and `e2a6b4391317750fc468f45154b2e702393013beaaae1cc7704ded2cc2dc94b5`.
The disposable database grew from 8,238,771 to 8,345,267 bytes. Evidence table
totals/index sizes were: runs 32,768/16,384; events 49,152/32,768; artifacts
65,536/49,152; checks 65,536/49,152 bytes. Fixed page/index allocation dominates
this tiny fixture; it is not a season capacity estimate. The database was removed
after readback. Its report is retained locally under `.cache/db002-rehearsal.json`.

Local Windows verification passed 219 tests, Ruff lint/format, mypy, platform
boundaries, package build and fresh-kernel imports. All required Postgres tests
ran against the isolated service. Calling the hosted verification CLI without
configured credentials returned a sanitized failure and exit 1; no hosted API
request or permission success is implied. Hosted CI is separate evidence.

After stacking all three batch PRs and regenerating the combined dependency lock,
the complete local suite passed 236 tests. Lint, format, types and boundaries
passed too. Review order is PR #19, then #20, then #21; retarget later PRs after
their bases merge. No branch has been merged by this execution.

Still required: actual project plan/limits, hosted role and Storage API denials,
Windows/Actions session behavior, object/database usage against allowances,
representative season growth, source acceptance, backup synchronization and an
isolated full recovery rehearsal. No forecast, seed import, scheduler or public
read surface is delivered by this task.

Provider references checked October 25: [Storage access control](https://supabase.com/docs/guides/storage/security/access-control),
[REST API](https://supabase.com/docs/reference/self-hosting-storage/introduction),
[Storage errors](https://supabase.com/docs/guides/storage/debugging/error-codes).

Modern controlled-setup keys use the `apikey` header, without treating the key as a JWT. Legacy service JWTs retain their Bearer header only for compatibility. Ordinary jobs continue to use a publishable key plus their own backend Auth JWT. Actual hosted Auth/Storage verification remains required.

## Observed hosted Storage response format

The October 28 checks observed HTTP 400 wrapping canonical statusCode 404 and
NoSuchBucket/NoSuchKey. Controlled setup and immutable upload recognize those
exact conditions. Generic bad requests and authorization failures do not become
missing resources. The permission rehearsal also recognizes explicit wrapped
AccessDenied/statusCode 403. It still fails for generic concealed mutation errors
or a successful empty delete response, even when original bytes survive. The
current hosted rehearsal is incomplete; no permissions were broadened to pass it.
