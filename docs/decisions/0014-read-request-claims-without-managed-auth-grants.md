# ADR 0014: Read request identity without managed Auth grants

Status: DRAFT for owner review, October 27, 2026.

## Evidence

The new Free project `lkwfzdfaqempnwffocmm` is healthy in eu-west-1 on
Postgres 17.11. Repository migrations 0001 and 0002 applied with exact hashes.
Migration 0003 rolled back: its grant on the managed Auth schema did not take
effect. The hosted `postgres` role has Auth usage without grant option.
Only 0001 and 0002 remain in application migration history.

Supabase documents this exact behavior and supports reading the request user ID
from the request settings instead:
[managed Auth permission guidance](https://supabase.com/kb/troubleshooting/permission-errors-when-granting-custom-roles-access-to-the-auth-schema).

## Proposed decision

Correct migration 0003 before its first hosted deployment. Remove the ineffective
Auth grants. Inside the existing private identity gate, read the legacy request
subject setting with the JSON claims subject as fallback, matching the provider's
identity semantics. Keep the binding, fixed search path, private schema, backend
UUID and bucket checks. Keep the application owner without provider role
membership or managed Auth access.

The claims are trustworthy only on the supported Data API/Storage path after
provider JWT verification. A caller with direct SQL access can set custom request
settings. Do not grant the restricted SQL runtime access to this identity helper;
this change does not turn caller-supplied SQL settings into authentication.

## Migration boundary and tradeoff

This is a proposed exception for a reviewed migration that has not reached any
Baseline hosted database. Its original SHA-256 is
`739ca9b03d75e1dcf46b8ff82af09c163185f0ea5ec1f4bbae74997e54d4071c`.
The only persistent Baseline project is currently at 0002. Never rewrite a
stored migration checksum or bypass drift checks. Disposable development/test
databases that applied the old 0003 must be recreated. If a persistent deployment
with that hash is discovered, stop and prepare a separate additive upgrade path.

Tradeoff: this one-time fresh-install correction changes the file hash and needs
explicit owner approval. It avoids granting every authenticated-user privilege
to the application owner or adding an administrator-owned identity wrapper.
Existing applied migrations 0001 and 0002 remain byte-identical.

## Verification and deployment

Local real-Postgres tests cover both claim formats, absent identity, wrong user,
wrong bucket, no managed Auth access and no inherited authenticated role.
A rollback-only hosted dry run created the helper and two Storage policies with
Auth schema access false and provider-role membership false. The transaction was
rolled back; it did not deploy 0003. Actual Auth sign-in and Storage API permission
verification remain separate gates.

Apply the correction only after owner review/lock, then continue the reviewed
migration sequence and verify hashes, private schemas and denied roles.
