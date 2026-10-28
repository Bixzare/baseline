# Supabase setup evidence

Updated October 27, 2026. This records actual hosted observations, separate from
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
| Runtime login / TLS | Unverified; no local runtime or migration credentials configured. |
| Auth / private Storage | Not provisioned. No backend identity or bucket has been created. |
| Account quotas / usage | Actual included allowances and provider object usage remain unverified. |
| Production | Disabled; no seed import, fake fixture forecasts or official predictions. |

The MCP deployment applied each approved file under a transaction advisory lock,
using its required role and recording its exact ID/name/SHA-256 in the same
transaction. RESET ROLE precedes the provider's migration bookkeeping. Both the
provider history and application history must be read back. The direct CLI path
still needs a verified TLS setup and runtime role test from Windows and Actions.

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
