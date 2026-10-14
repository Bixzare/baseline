# ADR 0012: Restrict runtime artifact storage access

Status: LOCKED by the project owner on October 13, 2026.

Date: October 13, 2026

Decision basis: the owner approved a dedicated restricted backend identity and locked this record on October 13, 2026. This specifies that choice under [ADR 0003](0003-store-operational-records-and-versioned-artifacts.md) and [design storage requirements](../design.md#5-storage-and-identifiers). Authentication and hosted enforcement remain unverified.

## Context

Cloud and local jobs need to create and read private evidence without replacing accepted artifacts. Supabase service keys bypass Storage row policies, so giving one to a routine collector would undermine the approved runtime restrictions. [Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control).

## Decision

- Use one dedicated Supabase Auth identity for backend artifact access. Bind permissions to its verified identity ID and the configured private artifact bucket, not to all authenticated users. It adds no dashboard login, public signup, or customer accounts.
- Permit only reading and creating objects in that bucket. Deny object replacement, overwrite/upsert, deletion, and moving existing objects, plus bucket administration and access to unrelated buckets. Keep the bucket private. The dashboard receives no backend credentials or private artifact links.
- Keep database operations on their separate restricted psycopg role. Storage authentication grants no private application-table access or privileged database-function access through the Data API. Neither runtime credential may mutate Storage metadata directly through SQL.
- Provision the identity and bucket through a controlled, repeatable setup operation using supported provider APIs. Any required administrator credential is used only for reviewed setup and recovery, outside ordinary jobs and PR CI. Record nonsecret identity/bucket configuration; never commit passwords or tokens. Apply application grants and Storage policies through repository migrations without altering provider-managed table structures.
- Proposed session policy: each job signs in using backend credentials supplied through environment secrets, keeps its session in memory, and refreshes that session when necessary. Do not share a persisted refresh token between concurrent cloud/local jobs. Verify the pinned Python client, token propagation, renewal, and bounded authentication retries before enabling schedules. Password sign-in is supported by the [Python API](https://supabase.com/docs/reference/python/auth-signinwithpassword); the [session documentation](https://supabase.com/docs/guides/auth/sessions) explains access and refresh tokens. Project settings and actual runner behavior still require testing.
- Use content-addressed object keys and disable overwrite in the client as an additional guard. On an existing key, read and verify bytes against the expected hash and size before reuse. A mismatch fails the operation; never repair it by overwriting. Preserve separate source observations even when bytes are deduplicated.
- Authentication, permission, upload, or checksum failure blocks operations requiring that evidence. Record sanitized failure status and preserve existing forecasts. No privileged-key fallback or publication without required artifacts is permitted.

## Reason and tradeoff

This uses the existing provider's authentication and row policies without introducing another server. A service key is simpler to operate but bypasses the required restrictions; a separate upload broker adds hosting and maintenance.

The chosen approach adds an Auth dependency, credential rotation, and session handling. One identity gives cloud and local jobs the same storage scope rather than separate audit identities. Accepted artifacts remain protected from runtime replacement, but a compromised writer could still create unwanted objects or exhaust capacity. Existing usage alerts and independent backups remain required.

## Verification required during implementation

- From Windows and the actual GitHub Actions runner, authenticate as the configured identity, upload an isolated fixture, download it, and verify its hash. Record identity, permissions, measured requests, and failures without secrets.
- Test overwrite/upsert, replacement, deletion, move, bucket changes, unrelated-bucket access, anonymous access, and a different authenticated identity. Verify rejection through actual Storage APIs; plain Postgres tests alone do not prove hosted Storage enforcement.
- Verify private application data and privileged functions remain inaccessible with the Storage session. Check both runtime credential paths for unintended Storage SQL permissions.
- Exercise expired access tokens, renewal failure, invalid credentials, simultaneous cloud/local sessions, and bounded retries. One job must not invalidate another job's session through global sign-out or shared refresh-token handling.
- Test successful upload followed by a lost response, duplicate uploads, corrupt content, and hash-checked reuse. Required artifacts must exist and verify before any dependent ledger transaction starts.
- Document credential rotation, identity replacement, and permission revocation. Do not assume sign-out or password rotation immediately invalidates every issued access token; verify the actual boundary. Routine workflows and notebook outputs must contain no administrator keys, passwords, or session tokens.

## Consequences and scope

The runtime immutability guarantee excludes administrators, who can change permissions or object contents. Hash verification detects disagreement with recorded evidence; it does not create a tamper-proof archive. Full backup delivery and restoration remain separate launch gates.

The next storage issue must include these contracts and an explicit hosted verification operation. Deterministic PR checks cover policy logic and client failures without production secrets; hosted checks supplement them. If the permitted mechanism cannot be verified, report the storage gate as failed and request a reviewed alternative. Paid infrastructure is not authorized.

Approval: the owner explicitly said "LOCK" on October 13, 2026. This finalizes the decision; a separate implementation assignment starts execution. No identity, bucket, policy, authentication flow, or hosted permission test has been implemented by this planning record.
