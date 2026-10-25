# LEDGER-001: Establish ledger tables, permissions, and baseline registration

Status: LOCKED by the project owner on October 14, 2026.

Prepared: October 14, 2026

Phase: 1. Priority: launch blocker. Dependencies: DB-003 and MODEL-001 implemented and owner-reviewed, including DB-001/DB-002 foundations. Required inputs are the migration/role mapping, verified artifacts, and actual baseline version descriptor. Isolated schema work can proceed without live sources; hosted registration requires accepted configuration evidence.

Session estimate: about 3 to 4 focused hours plus owner review and controlled hosted migration/bootstrap. Scope is nine tables, database integrity/access tests, and initial baseline registration. Guarded publication and receipt confirmation are the next issue; scheduling and outcomes remain separate.


## October 25 execution context

The owner resumed sequential execution with the [historical-data amendment](../PRD-data-source-amendment.md).
Use accepted pinned seed/repair artifacts, preserve quarantine and unknowns,
and never infer historical pregame cohorts from outcomes. Injury ingestion is
deferred for the first release. The original October 20 target is past;
all timing/readiness gates now apply to the first approved future slate.
This task is backlog until its implemented/reviewed dependencies pass.
No runtime source acceptance, merge, deployment, or retrospective publication
is established by this amendment. Required tests and contracts below remain.


## Goal and context

Give prepared player baselines immutable model/bundle identities and a protected destination for complete game batches, predictions, abstentions, reservations, receipts, and lifecycle events. Keep ordinary runtime access read-only for these records until protected operations exist. This issue cannot publish an official forecast.

Opening-night forecasts must be published before October 20, 2026 at 19:00 UTC, targeting 17:00 UTC. The approved policy requires another transaction confirming committed batch visibility before scheduled start minus 15 minutes. Table creation and insertion timestamps alone do not meet that gate.

Required guidance: AGENTS.md and `.agents/skills/hoop-postgres/SKILL.md`; use `hoop-python-testing` for real Postgres/role checks. Locked references: [ADR 0004](../decisions/0004-enforce-immutable-pregame-publication.md), [model records](../design.md#61-platform-operations-and-evidence-phases-0-1), [forecast tables](../design.md#63-forecasts-and-outcomes-phase-1), and [publication controls](../design.md#7-ledger-publication-and-access-control). Contracts below stand alone without chat history.

## Table contract

Add ordered migrations after DB-003. UUID IDs are primary keys; references below are foreign keys except external subject IDs. Store UTC timestamps, version roles/targets/policies, and preserve full prediction precision. No outcomes, evaluation, alerts, or MLOps tables yet.

| Table | Columns and behavior |
| --- | --- |
| `platform.models` | model_id; domain, family, target, version; code_version, config_hash; optional artifact_id and training_cutoff; created_at. Unique domain/family/target/version. Baselines may omit a learned artifact/cutoff; code and configuration identity are required and immutable. |
| `platform.model_bundles` | bundle_id; domain; components JSONB mapping targets to model UUIDs; created_at; config_hash. Immutable nonempty object. Every referenced model exists, has this domain, and matches its target key. |
| `platform.active_bundles` | domain and family composite key; bundle_id; generation BIGINT. Bundle domain agrees; generation is positive. Controlled initial bootstrap is the only pointer write path introduced here. |
| `platform.forecast_batches` | batch_id; run_id; event_id; bundle_id; feature_artifact_id; cohort_artifact_id; schedule_observation_id; generated_at, feature_cutoff, recorded_at; scheduled_start; publication_policy_version; content_hash; insertion_transaction_id TEXT. Schedule observation belongs to this occurrence; event and bundle domains agree. Cutoff is no later than generation/recording. |
| `platform.predictions` | prediction_id; batch_id; subject_type, subject_id, target, role; model_id; value DOUBLE PRECISION; unit. Unique batch/subject_type/subject_id/target/role. Finite values and nonempty identities/unit. Model identity agrees with the bundle's target mapping. |
| `platform.abstentions` | abstention_id; batch_id; subject_type, subject_id, target, role, reason_code; details JSONB. Same unique slot identity; no numeric value. One slot cannot appear in both prediction and abstention tables. |
| `platform.official_slots` | event_id, subject_type, subject_id, target composite key; batch_id; decision_kind TEXT, either prediction or abstention. Batch/event agree. One immutable official reservation across batches, including abstentions; no role/model-version escape from the key. |
| `platform.publication_receipts` | receipt_id; batch_id unique; observed_committed_at; confirming_transaction_id TEXT; policy_version. Immutable. Transaction IDs differ, receipt time is no earlier than batch recording, and policy agrees with the batch. Actual visibility/deadline enforcement comes next. |
| `platform.prediction_events` | prediction_event_id; batch_id; optional prediction_id; recorded_at; kind, reason_code; optional source_check_id. Immutable lifecycle/correction/invalidation evidence. Referenced prediction belongs to the same batch. |

**Approved schema refinement:** official_slots includes decision_kind as a shared discriminator for the two decision tables. Their separate unique indexes alone cannot stop a prediction and abstention occupying the same slot. The owner approved this column by locking the issue on October 14, 2026; it is incorporated into design v1.4 without changing the one-decision policy.

Use SQL constraints or narrow tested guards for cross-table relationships. Every official child must match its reservation's event, batch, subject, target, and kind. At transaction completion, every reservation has exactly one matching child. Allow the future publisher to insert reservation and child within one transaction without permitting a partial committed decision. Test exclusion across independent concurrent transactions and supported isolation modes, not just a Python check or a snapshot-sensitive lookup.

The initial forecast role is official. Later benchmark/shadow/replay support needs explicit tested write paths and any required migration; it cannot relabel records. Rehearsal uses a separate local/disposable database, never a mutable production mode.

Reject NaN and both infinities in SQL. The next publication issue applies domain target ranges and validates the complete cohort, including nonnegative NBA player targets. Do not impose a universal nonnegative constraint that would exclude future signed team margins. Add indexes needed for identity, integrity, and bounded reads, without speculative partitioning.

## Access and authoritative metadata

- Migration access owns the tables and policy objects. Create a narrow nonlogin publication-function owner with required read/insert grants only. It must not own ledger tables, inherit migration access, bypass policies, or receive update/delete/truncate, schema creation, grant, or role-administration privileges. Runtime/anonymous identities cannot assume it.
- Runtime gets necessary private ledger/model reads, with no direct inserts, mutations, active-pointer writes, or receipt creation. Anonymous clients get no private reads/writes. Preserve safe application default privileges and the separate Storage identity restrictions. Do not temporarily grant direct ledger writes.
- Protected publication/confirmation functions and their execute grants arrive in the next issue. Internal guard functions added here need fixed trusted object resolution and no unintended PUBLIC/runtime execute access. Create functions and restrictive grants in one migration transaction; [PostgreSQL function security](https://www.postgresql.org/docs/current/sql-createfunction.html).
- Define database recording/event time and transaction-ID defaults using the verified project Postgres version. Defaults are not proof of timely commit or permission to trust client-supplied values. Protected operations will derive authoritative metadata themselves and use actual clock time for cutoff checks, rather than transaction-start time. [Time functions](https://www.postgresql.org/docs/current/functions-datetime.html), [transaction identifiers](https://www.postgresql.org/docs/current/functions-info.html#FUNCTIONS-PG-SNAPSHOT).
- Generation/cutoff remain recorded preparation metadata. This issue proves structural integrity and denied runtime forgery paths; it cannot prove publication timing before the protected operations exist. Privileged fixture receipts are not live publication evidence.

## Controlled baseline bootstrap

Use a small reviewed setup command outside routine workflows, with privileged database credentials supplied through environment secrets. Schema/grant changes still come only from migrations, never hosted-console SQL.

Read MODEL-001's actual descriptor and verified configuration artifact. Register one immutable model per launch target, one NBA player bundle covering all five targets, and one initial active pointer. Validate domain/target/version/code/configuration identity and referenced artifacts. Do not invent a learned artifact or training cutoff for this deterministic baseline.

Create a bootstrap run and matching activation run event in the same short transaction as model/bundle/pointer registration. Record IDs, initial generation, configuration artifact/hash, code identity, reason, and database time. Verify artifacts before the transaction; no network calls within it. Later MLOps records preserve this bootstrap provenance.

An exact rerun returns the same IDs without changing contents, timestamps, generation, or audit history. Conflicting metadata under an existing version fails and requires a new version. Concurrent attempts cannot create competing initial identities or duplicate activation events. If a later champion is active, rerunning bootstrap must not restore the initial baseline pointer.

## Execution sequence

1. Inspect actual migrations, project Postgres version/roles, and MODEL-001 descriptors. Implement the nine tables, guards, restrictive grants, and small controlled bootstrap.
2. Test fresh/upgrade paths and constraints on disposable Postgres. Privileged fixture loading is confined to tests and explicitly distinguished from runtime capabilities. Test real roles and concurrent conflicts before hosted application.
3. After owner review, apply migrations using DB-001 tooling and run controlled baseline bootstrap. Read back registered identities with runtime credentials and match all five targets/configuration hashes to the descriptor. Forecast/receipt tables stay empty.
4. Update README, AGENTS.md under 200 lines, database/bootstrap notes, and Weaknesses.md with commands, evidence, and remaining gates. Do not add empty notebook publication sections or claim official publication.

## Acceptance criteria

- [ ] Nine tables and integrity/access rules are reproducible through fresh/upgrade migrations on real Postgres. Shared official reservations prevent contradictory decisions, including concurrent writes.
- [ ] Invalid event/batch/model/child/receipt relationships and nonfinite values are rejected. Fractional finite values remain precise and future signed targets remain representable.
- [ ] Runtime cannot write ledger/model records directly, create receipts, change active pointers, mutate evidence, change grants, or assume the nonlogin owner. Anonymous private access is denied.
- [ ] Controlled bootstrap registers the actual five-target bundle and audit event atomically. Reruns/concurrency preserve IDs/times/generation and cannot reverse later activation.
- [ ] Hosted runtime reads match the descriptor. Forecast/receipt tables remain empty; timing/completeness verification stays pending the next issue.
- [ ] PR lint/type/tests and real Postgres checks pass. Setup/README/AGENTS.md clearly distinguish schema readiness from publication readiness.

## Required tests

- Fresh/upgrade migrations; keys/FKs; domain/target mismatch; malformed bundle JSON/UUIDs; nonexistent models; duplicate versions; invalid generations; missing/mismatched reservation children; lifecycle cross-batch references; and identical insertion/confirmation IDs.
- Actual SQL rejection of NaN and both infinities; retention of fractional finite values. No global nonnegative rule that blocks signed numeric targets.
- Two independent connections racing official reservations and opposite prediction/abstention kinds. Test supported isolation modes and insertion order. Exactly one matching decision can commit; conflicting content rolls back without replacement.
- Actual runtime/anonymous attempts at direct inserts with caller timestamps, update/delete/truncate, active-pointer changes, guard execution, DDL, grants, and role switching. Verify denial and inspect nonlogin-owner/default PUBLIC privileges.
- Bootstrap empty state, exact rerun, changed code/config under the same version, failure between related inserts, concurrent initialization, and rerun after a simulated later activation. Verify atomic rollback and original audit identity retention.
- Changing an active pointer in an isolated privileged fixture cannot rewrite model/bundle references on an existing batch. A synthetic second-domain bundle/event works without NBA target names hard-coded into platform constraints.
- The next issue supplies actual cutoff, visibility, receipt, and feature-leakage tests. Default timestamps and privileged fixture inserts are not substitutes.

## Failure decision, likely files, and handoff

A managed-role/grant limitation needs a supported reviewed correction, not migration credentials in a collector or direct runtime ledger INSERT. Failed bootstrap leaves no partial activation. Without protected functions, official publication stays unavailable.

Likely files: ordered `migrations/`; `src/hoop/platform/ledger/` schema/read/registration helpers; thin controlled CLI bootstrap; NBA descriptor mapping where domain-specific; `tests/integration/`, `tests/unit/`, and fixtures; setup/bootstrap documentation, README.md, AGENTS.md, and Weaknesses.md. No schedule workflow, public read table, outcome evaluator, or publication function here.

Return the PR, exact checks/migration outcomes, real role/grant evidence, registered model/bundle/configuration IDs, bootstrap run/event identity, hosted readback, race/failure results, and outstanding publication gates. Explain official-slot versus per-batch uniqueness, immutable versions, and why an insertion timestamp does not prove timely commit.

Approval: the owner explicitly said "lock" on October 14, 2026. This finalizes the specification and its decision-kind refinement; a separate coding-agent assignment starts execution. No ledger migration, baseline registration, official forecast, or receipt has been implemented by this planning record.
