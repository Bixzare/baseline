# ADR 0003: Store operational records in Postgres and evidence in versioned files

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [design Sections 5 and 6](../design.md#5-storage-and-identifiers), [database access controls](../design.md#7-ledger-publication-and-access-control), [migration strategy](../design.md#15-migrations-ci-and-test-strategy), and [retention, backup, and capacity](../design.md#16-retention-backup-and-capacity). This record documents approved choices; setup and recovery verification remain outstanding.

## Context

Baseline needs durable operational records shared by scheduled jobs and a public dashboard. The prediction ledger needs transactional publication and restricted write permissions. Raw responses, complete historical archives, feature snapshots, models, and detailed reports also need reproducible identities, but repeating those large payloads in database rows would consume the project's limited storage.

The default budget is $0. Neither free-tier capacity nor backup recovery has been measured. Keeping a local archive alone does not provide an independent recovery copy.

## Decision

- Use Supabase Postgres for operational records, recent normalized history, forecast records, outcomes, model history, and decision summaries. Use separate platform and NBA schemas, plus sanitized read tables for the public dashboard.
- Use psycopg with explicit SQL and no launch ORM. Apply ordered, phase-specific SQL migrations from the repository, recording migration IDs and checksums. Never edit an applied migration or change the production schema by hand.
- Separate migration credentials, restricted runtime roles, and anonymous public reads. Privileged credentials remain outside collection jobs and browser bundles; secrets come from environment variables.
- Prefer a direct database connection where supported. Test the included session pooler as the IPv4 fallback, including migrations and backup/restore, with TLS and a small connection count.
- Store raw inputs, feature/cohort snapshots, models, and detailed reports as versioned files referenced by manifests with checksums and provenance. Use private object storage for files cloud jobs need, and prevent replacement of accepted artifacts. Verify hashes on reads.
- Keep the full historical Parquet archive locally with an independent backup. Upload only measured partitions needed by active cloud workloads; seed enough normalized recent history in Postgres for launch baselines. A scheduled job cannot depend on an unreferenced laptop-only file. DuckDB remains an optional local archive query tool.
- Preserve official forecasts, publication evidence, required source and feature references, outcome revisions, evaluation manifests, and activation decisions. Identical raw bodies may be deduplicated; distinct observations and their metadata remain preserved.
- Back up the database and required artifacts daily to the chosen existing cloud-synced folder. Supply its provider and path during setup. Verify completed remote upload, and alert when the latest verified off-device backup is over 24 hours old, measured from its represented data cutoff.
- Restore an off-device backup into an isolated database before launch. Verify migrations, forecast IDs, original timestamps, artifact hashes, and counts. Document recovery gaps without reconstructing trusted prediction timestamps.
- Warn at 60% of each included storage allowance or projected season overflow. At 80%, pause optional shadow runs and additional reports. Preserve official evidence and resolve capacity before the hard limit. An alert does not authorize a paid upgrade.

## Reason and alternatives

Postgres keeps shared operational state, constraints, and access controls in one place. Versioned files keep bulky evidence reproducible without repeating it in every forecast row. Explicit SQL makes the publication and permission behavior visible during owner review; phase-specific migrations avoid building later schemas during launch.

A sole DuckDB/Parquet operational store would require a different design for concurrent cloud/local publication and public data delivery. Keeping all raw and historical payloads in Postgres would spend scarce database capacity on data better represented as referenced files. Adding an ORM now would introduce another abstraction around a small set of explicit, security-sensitive SQL operations. Those alternatives are not selected.

## Consequences

Evidence spans the database and referenced files, so both must be included in manifests and recovery checks. A database export without its required object contents is incomplete. Connectivity, table/index growth, object size, and egress need actual measurement before claiming the deployment fits the free tier.

Local backup exports and synchronization depend on an awake, connected machine. Records created after the latest verified backup may be lost in an outage. Application permissions do not provide a tamper-proof guarantee against the database or storage administrator. These limitations remain visible in [Weaknesses.md](../../Weaknesses.md).

## Verification required during implementation

- Apply migrations from an empty real Postgres database; exercise checksum/history handling and restricted roles. Verify the intended connection path from Windows and GitHub Actions.
- Verify runtime credentials cannot perform schema changes and public credentials can read only sanitized data, with no writes or privileged operation access.
- Check manifest references, artifact hashes, rejection of replacement/corrupt files, and preservation of distinct source observations during deduplication.
- Measure representative database and index growth, object storage, and projected season usage against current account allowances. Test the 60% and 80% boundaries without deleting official evidence.
- Rehearse the daily backup, remote-upload verification, age alert, and isolated restore from the off-device copy, including original ledger timestamps and referenced artifacts.

Approval: the owner explicitly said "lock" on October 12, 2026. No database, storage resource, migration, or backup has been deployed by this planning record.
