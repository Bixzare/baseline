---
name: hoop-postgres
description: Design or review Baseline Postgres schemas, SQL migrations, ledger publication, role permissions, public dashboard reads, backup restoration, and query performance. Use for changes to persisted contracts or database behavior.
license: MIT; upstream notice in LICENSE.txt
---

# Baseline Postgres

Locked project adaptation of Supabase `supabase-postgres-best-practices`, approved October 12, 2026.
Source revision and review notes are in the repository's `skills/README.md`.
Consult current official Postgres/Supabase documentation for version-dependent behavior.

## Inspect before changing

1. Read the assigned schema contract and existing migrations. Distinguish approved requirements from proposed design details.
2. Identify every caller and role: migration owner, restricted collector/predictor, evaluator, and anonymous dashboard.
3. Define keys, relationships, timestamp meaning, null meaning, uniqueness, precision, and revision behavior.
4. Write a migration and its verification/recovery procedure. Test both a fresh database and upgrading the prior schema.

## Ledger integrity

- Official predictions are append-only. Uniqueness covers event occurrence, subject, and target.
- Never use an upsert that updates an official prediction on conflict. Replays preserve the existing record and report its identity.
- Outcomes, source revisions, invalidations, and model decisions are separate records.
- Use restricted database permissions and database-side publication checks. A client timestamp is not a commit timestamp.
- Exercise transactions that cross the deadline, duplicate local/cloud writers, early starts, rescheduling, partial failure, and retry.
- Commit a complete immutable game batch after storing required artifacts, then confirm visibility in a second transaction before the cutoff. Retry confirmation of the same batch only. Missing or late confirmation is unverified coverage; never backdate or replace it, or substitute transaction-start time for the receipt.
- Keep network calls and training outside database transactions. Bound lock waits without weakening atomicity.
- Database owner privileges are outside the runtime immutability guarantee; document that limit honestly.

## Public access

- Expose only intended public tables/views and fields. Anonymous clients may read those records and cannot mutate them.
- Protect private operational/raw data with grants and applicable row policies; verify behavior through the actual API roles.
- Check view and function privileges, including execution grants and the search path of privileged functions.
- Never place service or migration credentials in the browser. Public client configuration is not permission to write.
- Do not add login, tenancy, or per-user tables to this public read-only product.

## Capacity and recovery

- Inspect actual query plans and data volumes before adding indexes or tuning. Index join/filter keys where evidence supports them.
- Use bounded query results, appropriate connection pooling, and short transactions.
- Measure storage and retention needs before relying on a free-tier limit. Do not add partitioning or extensions by default.
- Keep archive/artifact identity independent of local absolute paths.
- Verify a database and artifact restore from the independent cloud-synced backup, including completed synchronization.

Return the migration, role-based test results, publication failure evidence where affected, and any capacity or recovery limit.
