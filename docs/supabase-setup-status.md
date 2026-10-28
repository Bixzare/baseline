# Supabase setup evidence

Updated October 28, 2026. This records actual hosted observations, separate from
local Postgres fixtures and production readiness.

| Item | Evidence |
| --- | --- |
| Organization | Bixzare's Org, `bfrxowczextqqjkyftsy`; Free plan verified through MCP. |
| Project | `baseline`, `lkwfzdfaqempnwffocmm`, eu-west-1; ACTIVE_HEALTHY. |
| Creation cost | Provider quoted $0 monthly, matching the owner's Free-only choice. |
| Database | Actual SQL and project metadata report Postgres 17.11. |
| Application schema | Migrations 0001 through 0008 committed with repository byte hashes. |
| Migration 0003 | Initial attempt rolled back; owner-approved claims correction applied successfully. |
| Approved correction | [ADR 0014](decisions/0014-read-request-claims-without-managed-auth-grants.md), locked by the owner; both local tests and hosted dry run passed before deployment. |
| Migration 0006 | Initial attempt rolled back; owner-approved SET-role correction applied successfully. ADR 0015 is locked. |
| Verified roles | Runtime has no owner/publisher membership or direct prediction INSERT. Publisher owns protected functions and has no schema CREATE. |
| Initial usage | Database 12,416,691 bytes; zero Storage objects/buckets and zero forecast batches at readback. This is initial usage, not a season estimate. |
| Security advisor | No findings after reviewed schema deployment through 0008; not a replacement for role/API tests. |
| Public HTTPS checks | Auth settings HTTP 200; private platform Data API refused with HTTP 406/PGRST106. |
| Signup setting | disable_signup=false at readback; owner must disable public signup before backend readiness. |
| Runtime login / TLS | Windows session pooler verified as baseline_runtime with client TLS and verify-full. Owner membership, publisher membership and direct prediction INSERT are absent. Actions and direct mode remain untested. |
| Pooler backend | pg_stat_ssl reports false for the pooler-to-Postgres leg; this differs from verified client TLS. No claim of backend TLS is made. |
| Auth / private Storage | Dedicated backend and unbound negative-test identities created; independent sign-in/refresh passed. Two private buckets exist. Actual create/read and explicit write denials passed; delete, move and bucket administration remain inconclusive under the required verification contract. |
| Current fixture usage | 12,785,331 database bytes, two private buckets, two 59-byte objects; zero registered artifacts and zero predictions. These measurements do not establish season capacity. |
| Account quotas / usage | Actual included allowances and provider object usage remain unverified. |
| Production | Disabled; no seed import, fake fixture forecasts or official predictions. |

The MCP deployment applied each approved file under a transaction advisory lock,
using its required role and recording its exact ID/name/SHA-256 in the same
transaction. RESET ROLE precedes the provider's migration bookkeeping. Both the
provider history and application history must be read back. The Windows runtime path is now verified with the corrected client TLS health
report. The actual Actions runtime check remains unverified.

Next: owner review of the remaining evaluation/alert migration PRs, then continuation,
privately configured setup/runtime credentials, supported Auth/Storage setup and
permission verification. Credentials belong in the environment or ignored local
configuration loaded into it. Never paste database passwords, service keys or
backend passwords into chat. Keep administrative credentials out of jobs.

OneDrive is the owner's selected independent backup provider. Remote download/hash
verification, folder configuration and isolated restore are still pending.

The checkout moved from Hoop to Baseline. The broken environment was preserved
under an ignored .venv-before-rename directory and rebuilt from the existing
lockfile. The project Jupyter kernel now points to the Baseline environment.
The existing Postgres 17.11 fixture container was restarted with a loopback-only
port. None of this proves hosted runtime connectivity or backup delivery.

## October 28 private setup and provider compatibility

The certificate was saved inside a directory named supabase-ca.crt. The ignored
local environment now points to the actual prod-ca-2021.crt file. Database
credentials never entered reports, source control or shell arguments. The
migration check matched repository hashes through 0008 and reported pending
0009/0010; neither pending migration was deployed.

The health check now distinguishes libpq client TLS from the backend's
pg_stat_ssl value. The actual restricted login used verify-full with client TLS
true and backend TLS false. It was refused migration-history reads, owner role
assumption and schema creation, and has no direct prediction INSERT permission.

Hosted Storage wraps canonical errors in HTTP 400 responses. Setup and upload
recognize only explicit NoSuchBucket/NoSuchKey with statusCode 404. Permission
checks recognize AccessDenied with statusCode 403; malformed or unrelated errors
remain failures. This changes response interpretation, not provider grants.

The hosted permission rehearsal remains verified=false: delete returned HTTP
200 with an empty list; move returned a concealed NoSuchKey; bucket administration
returned a concealed NoSuchBucket. Neither 404 mutation alone nor a nominal
success counts as authorization denial. Original fixture bytes remained intact.
Replacement, upsert, unrelated-bucket create, private Data API access, anonymous
read/create and other-identity read/create passed their required checks.

Sanitized local reports are under artifacts/setup-verification/. Two small
rehearsal objects remain unregistered and were not automatically deleted. Signup
still reports disable_signup=false at the latest readback. Production remains off.

The current security advisor reports one Auth warning: leaked password protection
is disabled. Supabase documents that protection as Pro-only. No paid feature was
enabled; dedicated setup identities use independently generated random passwords.
See [password security](https://supabase.com/docs/guides/auth/password-security).
The warning and pending public-signup setting remain visible in the setup record.
