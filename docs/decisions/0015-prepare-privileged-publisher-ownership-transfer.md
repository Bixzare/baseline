# ADR 0015: Prepare privileged publisher ownership transfer

Status: DRAFT for owner review, October 27, 2026.

## Evidence

Hosted 0001 through 0005 are committed. Migration 0006 rolled back because
Supabase grants the migrator ADMIN without SET or INHERIT on a newly created
custom role. A local superuser hid this difference. PostgreSQL requires SET
permission to transfer function ownership to that role.

## Proposed correction

Before the first hosted application of 0006, explicitly grant the privileged
migration identity SET on baseline_publisher, with INHERIT false. After ownership
transfer, explicitly SET LOCAL ROLE baseline_publisher to assign function
execution privileges. Retain the existing final switch to baseline_owner.
Do not grant publisher membership to runtime or schema owner. Revoke temporary
publisher CREATE exactly as before. The publisher remains NOLOGIN and has no
role administration or global database privileges.

Tradeoff: this adds an explicit capability to the already privileged setup
identity. That identity is outside the runtime immutability boundary and already
has ADMIN on the role. Ordinary collector/predictor credentials gain nothing.

## Migration boundary

0006 has not committed to the only persistent Baseline project. Its original
hash is `3831b039beef5996f68247d730cdb860bb7207eea052c64eb7445d5e8ade2803`.
The correction changes the fresh-install file only after owner review. Do not
rewrite stored migration hashes. Recreate disposable fixtures with the original
hash. If another persistent Baseline installation at 0006 exists, stop and design
an additive upgrade before touching it. Applied 0001 through 0005 stay unchanged.

## Verification

A real Postgres test creates a non-superuser migrator with ADMIN but SET false,
then applies 0006 and verifies SET true, INHERIT false and no runtime membership.
The actual hosted rollback-only dry run reports the intended publisher function
owner, no publisher schema CREATE and no runtime membership. Nothing from that
dry run persists. Provider/API and runtime TLS checks remain separate.

The broader suite also exposed a disconnect test race. Its corrected test waits
for the fixture backend to disappear before checking lock release. The
production lock remains nonblocking and unchanged.

Source: [PostgreSQL 17 GRANT](https://www.postgresql.org/docs/17/sql-grant.html).
