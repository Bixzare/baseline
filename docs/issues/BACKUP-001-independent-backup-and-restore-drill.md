# BACKUP-001: Verify independent backups and isolated restoration

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Phase: 1. Priority: launch blocker. Dependencies: DB-001/DB-002, LEDGER-002, OUTCOME-001, EVAL-001, and OPS-002 implemented and owner-reviewed. Setup provides the chosen existing cloud-sync provider/folder, permitted unattended verification route, supported export connection, and an isolated restore target. These remain execution inputs, not assumed resources. Session estimate: about 3 to 4 agent hours plus real export/upload/restore and owner review.


## October 25 execution context

The owner resumed sequential execution with the [historical-data amendment](../PRD-data-source-amendment.md).
Use accepted pinned seed/repair artifacts, preserve quarantine and unknowns,
and never infer historical pregame cohorts from outcomes. Injury ingestion is
deferred for the first release. The original October 20 target is past;
all timing/readiness gates now apply to the first approved future slate.
This task is backlog until its implemented/reviewed dependencies pass.
No runtime source acceptance, merge, deployment, or retrospective publication
is established by this amendment. Required tests and contracts below remain.


## Goal and scope

Create daily independent copies of application database state, required objects, and the historical archive, prove remote delivery, and restore a downloaded copy into an isolated target. No paid backup/PITR, public dump publication, or restore into production. Deadline: before official publication on October 20, 2026 at 19:00 UTC.

Read AGENTS.md and skills `hoop-postgres`, `hoop-data-quality`, `hoop-python-testing`. Contracts: [ADR 0003](../decisions/0003-store-operational-records-and-versioned-artifacts.md) and [design recovery](../design.md#16-retention-backup-and-capacity). The owner selected an existing cloud-synced folder; provider/path are intentionally configured during setup, not hard-coded or shared as secrets in chat.

## Export and consistency contract

- Use the verified DB-001 privileged export route only in the controlled local backup job, outside collectors/cloud prediction workflows. Store credentials in environment provisioning, not command arguments, tracked files, dumps of login passwords, or reports. Pin/verify compatible pg_dump/restore tools and TLS/session/direct behavior.
- Export application schemas, actual migration history, object dependencies, grants/roles needed for restoration, and nonsecret setup/code/lock identities. Do not assume a selected-schema dump restores independently; inspect managed Auth/Storage and function dependencies. Recreate supported provider setup separately rather than exporting production Auth passwords/tokens. [pg_dump guidance](https://www.postgresql.org/docs/current/app-pgdump.html).
- Use a consistent database snapshot for dump, row-count checks, and required-artifact reference inventory, via supported snapshot sharing or a demonstrated equivalent. Record a conservative database-derived represented cutoff no later than snapshot acquisition, separate from export/upload completion times. Finish the snapshot/dump before object downloads; do not hold a publication transaction during backup.
- Preserve all authoritative season records, original IDs/timestamps/transaction references, outcome/report versions, and activation/bootstrap provenance. Snapshot inventory covers recursively referenced raw, feature/cohort, configuration/model, outcome, and report objects. Include the complete accepted local 2025-26 archive/manifests; deduplicate unchanged bytes across backup sets without losing references.
- Download/copy exact required object bytes through supported read access and verify SHA-256/size. Database backups alone do not preserve Storage object contents; [Supabase backup guidance](https://supabase.com/docs/guides/platform/backups). Missing/corrupt references make the backup incomplete.
- Stage dump/objects/manifest in an ignored nonsynced directory, then finalize a complete immutable set into the configured private sync folder. The manifest records backup ID, source project, represented cutoff, migration/code/lock identity, counts, every required file/hash/size, dependency/role setup, and completion state, without credentials/private absolute paths.

## Daily delivery and freshness

Schedule a local daily backup at 08:17 UTC after the normal 07:17 reconciliation slot, with bounded retry and an explicit manual command. If reconciliation fails, back up the existing truthful state and record the failure; do not skip all protection waiting for healthy results. Coordinate overlapping local backups without changing forecasts.

During setup, verify the actual provider's permitted unattended sync-status/listing/download API or CLI and access conditions. A green local file icon, local existence, or copy completion is insufficient. Independently locate the remote set and verify it by remote download/hash readback into a separate nonsynced location. If reliable remote verification cannot be established, the backup gate remains unverified and needs a reviewed correction, not a substitute local success flag.

Append sanitized platform run events containing backup ID, manifest hash, represented cutoff, export completion, remote verification time/evidence, counts, and success/partial/failure reasons. OPS-002 consumes this contract. Age is measured from the latest complete remotely verified set's represented cutoff; absent/unverified or older than 24 hours alerts. Reuploading the same old snapshot does not reset age.

Measure disk/provider capacity and complete-set growth. No automatic deletion at launch; report projected exhaustion and seek a reviewed retention change preserving required evidence before a hard limit. No paid upgrade, unrelated folder cleanup, or backup in the same application bucket as the only independent copy.

## Isolated restore and safety

- Verify destination identity/absolute paths before restoration. Use a supported isolated native/test database, secure disposable test environment, or dedicated Free restore project if account allowance permits. Never reset/delete production or an unrelated project, upload production backups to public CI/artifacts, install a VM/WSL without an explicit task, or assume a second free slot exists.
- Fetch the remotely stored set, validate manifest/files, recreate required nonsecret schema/role/provider dependencies through reviewed tooling, and restore original application records. Resolve artifacts through an isolated archive/bucket mapping without rewriting original ledger references, IDs, timestamps, or values. Reprovision secrets separately; restored automation stays disabled.
- Verify schema/migration checksums, authoritative table counts, representative original batch/prediction/receipt IDs and times, model/bundle pointers, source/outcome/report revisions, permissions, and all required artifact hashes. At launch, production may have no forecasts yet: use a separately identified rehearsal backup containing ledger evidence for the preservation drill, plus a real independent export/readback of production's current state. Never plant fake production forecasts to make the drill look complete.
- Record represented recovery point, actual recovery duration, isolation/permission verification, unresolved dependencies, and records that would be lost after the cutoff. Recovery cannot recreate trusted pregame timestamps from notebooks/log memory. An old or partial set must fail visibly.

## Acceptance criteria

- [ ] Consistent database/reference export and complete archive/object set are produced with verified identities/hashes and no exposed credentials.
- [ ] Actual unattended provider verification demonstrates an off-device copy; daily task, age events, and OPS-002 alerts use the represented cutoff correctly.
- [ ] A downloaded remote set restores into a verified isolated target, retaining original forecast/receipt IDs/times and referenced bytes without production effects.
- [ ] Managed dependencies/roles and secret reprovisioning are documented and tested; dump success alone is not restore readiness.
- [ ] Fixture CI tests pass without production data/providers. Real delivery/restore evidence, capacity, commands, and limitations appear in README/AGENTS.md/runbook/Weaknesses.md.

## Required tests

- Concurrent writes around export snapshot, matching row-count/reference inventory, interruption during dump/object copy/finalization, missing/corrupt object, wrong manifest hash, rerun/deduplication, and partial sets never marked complete.
- Provider sync pending/failure, remote bytes missing/changed, local success without remote readback, absent verified set, 24-hour boundary, and later upload of an older snapshot. Use mocked provider boundaries in CI, actual provider verification separately.
- Disposable Postgres restore with real ledger fixture records and their original receipts/transaction IDs, versioned corrections, grants, migration identity, and artifact resolution. Wrong production/unrelated destination and unsafe paths must refuse before writes.
- Restore against required managed dependencies, interrupted restore, stale schema/lock mismatch, secret redaction, and disabled restored automation. Compare semantic counts/hashes rather than claiming byte-for-byte database files.
- Actual remote download/isolated restore drill from the owner's chosen provider and target, with evidence separate from fixtures. No historical replay timestamp becomes an official live record during restoration.

## Files and handoff

Likely files: shared backup/snapshot/manifest/restore helpers and CLI; provider verification adapter/configuration after setup; local Task Scheduler definition; unit/integration/failure fixtures; backup/recovery runbook, README.md, AGENTS.md, Weaknesses.md. Permission changes use migrations; full backup sets remain outside Git and public Actions artifacts.

Return PR/checks, snapshot/backup IDs and hashes, remote verification evidence, isolated target/drill results, original-record comparisons, measured capacity/recovery time, task state, and remaining setup gates. Unsupported provider verification or no safe restore route blocks backup readiness; report it early rather than weaken the criterion.

Approval: the owner's October 14 batch approval locks this specification. A separate assignment starts execution. No export, sync, backup, restore, provider choice, or local task has been executed by this document.
