# DB-002: Persist private artifacts and source evidence

Status: LOCKED by the project owner on October 14, 2026.

Prepared: October 13, 2026

Phase: 0. Priority: launch blocker. Dependencies: DB-001 and SOURCE-001 implemented and owner-reviewed. Required outputs are the dedicated Supabase Free project, migration runner, restricted database role, and shared source-report format. DATA-001 may proceed independently; history tables and seed import are a separate issue.

Session estimate: about 3 to 4 focused hours plus owner review and hosted checks, assuming project access is ready. Authentication and managed-policy restrictions are verification gates. Report a blocker rather than extending this into a new server, paid resource, or full collector implementation.

## Goal and context

Give collection and prediction jobs a tested way to retain private evidence, reference verified bytes, and record successful or failed source attempts. Implement four platform evidence tables and the restricted artifact access approved in ADR 0012. Keep NBA parsing in domain code.

Baseline must publish player baselines before October 20, 2026 at 19:00 UTC, targeting 17:00 UTC. This issue supplies evidence infrastructure. Event/history tables, seed import, forecasts, scheduling, public reads, and full backup automation remain separate tasks.

Required guidance: AGENTS.md and `.agents/skills/hoop-postgres/SKILL.md`; use `hoop-python-testing` for integration/failure checks and `hoop-data-quality` for source timing. Locked references: [ADR 0003](../decisions/0003-store-operational-records-and-versioned-artifacts.md), [ADR 0012](../decisions/0012-restrict-runtime-artifact-storage-access.md), and [design evidence tables](../design.md#61-platform-operations-and-evidence-phases-0-1). The contracts below are sufficient without prior chat.

## Persisted contract

Add ordered migrations after DB-001. UUID IDs are primary keys; references below are foreign keys. Store timezone-aware UTC times, version state/configuration values in code and migrations, and distinguish unknown from zero. JSON fields contain objects with bounded, sanitized summaries.

| Table | Required columns and behavior |
| --- | --- |
| `platform.runs` | `run_id`; operation, domain, environment, code_version, config_hash; started_at. Environment separates rehearsal from production. Immutable operation identity; no NBA-specific columns. |
| `platform.run_events` | `run_event_id`; run_id; recorded_at; state; optional reason_code; details. Append transitions. Terminal events carry counts, duration, and failure/incomplete reasons. Reuse an event ID only for an exact retry; never update its content. |
| `platform.artifacts` | `artifact_id`; sha256; kind, format, schema_version; byte_count; created_at; storage_uri; manifest. Unique storage URI, valid SHA-256 representation, nonnegative size, and no credentials or signed tokens in the URI. Register only verified durable objects. |
| `platform.source_checks` | `check_id`; run_id; source_id, adapter_version; requested_at; optional received_at, validated_at, source_published_at, raw_artifact_id, http_status, record_count; state; validation_summary. One immutable completed attempt, including failure. Preserve credential-free request identity and parser/configuration provenance in the summary. |

**Approved schema refinement:** `source_checks.received_at` is null when no response arrives. Preserve attempt completion in a run event, rather than inventing receipt of a timed-out request. The owner approved this narrow refinement by locking this issue on October 14, 2026; it is incorporated into design v1.3.

For accepted input, requested_at, received_at, and successful validated_at must exist in order. HTTP status is null when none was received; record_count is null when unknown, not a fabricated zero. An invalid response can retain its actual receipt time and raw artifact while validated_at stays null. A legitimate validated empty response can have record_count zero. Source publication time is supplied only when supported by the source, never copied from ingestion time.

Use immutable evidence rows with restricted runtime reads/inserts as needed, no update/delete/truncate rights, no ownership/DDL/grant privileges, and no anonymous private reads. Database-recorded creation/event times are not caller assertions of historical publication. Exact retries preserve IDs and contents; conflicting reuse of an ID or URI fails without overwriting. Table keys/FKs and race handling must enforce these rules, not just Python checks.

## Artifact and authentication contract

- Use the dedicated backend Supabase Auth identity and configured private artifact bucket. Policies bind its verified ID and bucket; authenticated users in general receive no access. Permit reads and new objects only. Deny replacement/upsert, deletion, moves, bucket administration, unrelated-bucket access, and anonymous access. Database writes still use the separate restricted psycopg role. Neither credential path may mutate Storage metadata through SQL or access private application tables through the Data API.
- Provision identity/bucket through a repeatable supported setup operation. Administrator credentials are limited to controlled setup/recovery and never supplied to collection jobs, PR CI, notebooks, or browsers. Storage policies and application grants use repository migrations; preserve managed table structures. Record the nonsecret identity/bucket settings and setup verification.
- Each job signs in from environment secrets, keeps its session in memory, and renews only its own session. Do not share refresh tokens across jobs or use global sign-out that disrupts other jobs. Verify the pinned client and token propagation on Windows/Linux. Bound authentication retries; never fall back to a privileged key.
- Keep raw, history, features, models, and reports under separate content-addressed prefixes. Reject unsafe paths. Hash exact bytes, store size/format/version, upload with overwrite disabled, then read and verify before registering a usable artifact. Reuse an existing key only after its bytes and canonical descriptor agree. Separate source observations retain their own timing/provenance even when identical raw bodies share an artifact.
- Keep network calls outside database transactions. An upload can succeed before a database failure; retry the same bytes/identity, verify the existing object, and finish registration without replacement. An unregistered object is not accepted evidence. Do not implement automatic deletion of orphan objects in this issue.
- Retain raw invalid responses when possible, but never mark them valid inputs. If storage fails, record a failed source attempt without a fictitious artifact reference. If the database is also unavailable, keep a sanitized local failure report and return failure; do not claim durable operational recording succeeded.
- Expose a shared eligibility check for source evidence at a feature cutoff: accepted state, known receipt and successful validation no later than the cutoff, and no later known publication time. A later correction with an older event/publication time still fails the earlier cutoff. Historical assumptions remain separate from observed evidence.

## Execution sequence

1. Inspect actual DB-001 and SOURCE-001 outputs. Reuse their migration, connection, provenance, and source-report operations; do not create a second database client or rewrite NBA adapters.
2. Implement the four tables, restricted grants, evidence registration, and artifact client in shared platform modules. Use a synthetic non-NBA source fixture to demonstrate the boundary.
3. Add deterministic client/failure tests and real Postgres integration checks. For local Storage policy tests, use isolated test fixtures representing the required provider relations/identity claims; these are test scaffolding only, never deployed provider replacements. Exercise the actual migration policies and explicitly label the limits of this simulation.
4. After owner review, apply migrations with DB-001 tooling and run controlled setup. Rehearse upload/read and permission denial from Windows and a manually dispatched GitHub Actions workflow using runtime credentials only. Use small rehearsal fixtures, not production forecast data. Any cleanup requires controlled administrative maintenance, not runtime delete grants.
5. Bridge a SOURCE-001 report into the shared evidence writer and show success, invalid-response, and transport-failure records in rehearsal. Archived/synthetic fixtures do not establish current NBA source health. Preserve original report times and label their provenance rather than inventing an earlier capture.
6. Record measured object/database/index growth for the fixtures against the project's verified allowances. Do not claim a season fits from this small sample. Update README and AGENTS.md with verified setup/check commands and Weaknesses.md with evidenced blockers. Full capacity monitoring, daily backup, and isolated recovery remain later launch gates.

## Acceptance criteria

- [ ] Fresh and upgraded real Postgres databases obtain the four tables and restricted grants through migrations. Required CI tests do not silently skip database setup.
- [ ] Exact retries and concurrent attempts cannot overwrite evidence, duplicate one artifact URI, or register unverified bytes. Distinct source observations survive deduplication.
- [ ] Windows and actual cloud rehearsal can authenticate, create/read a private fixture, and verify its hash. Hosted permission denials are recorded independently of fixture/SQL test results.
- [ ] The backend identity cannot replace/delete/move objects, administer buckets, access unrelated buckets, or read private application data through the Data API. Anonymous and other authenticated identities cannot access private artifacts.
- [ ] Success, validated empty data, invalid response, timeout, storage failure, and database failure remain distinguishable. Missing response/count/publication data is not fabricated.
- [ ] Cutoff checks reject late collection/validation/corrections even with an older event timestamp. No historical availability assumption is presented as observed pregame evidence.
- [ ] No secrets appear in tracked files, reports, URIs, notebook outputs, or logs. PR CI uses deterministic fixtures and disposable Postgres; hosted checks are separate, manually invoked operations.
- [ ] README, AGENTS.md under 200 lines, migration/setup notes, and the failure report are current. No history import, ledger, public dashboard, automated backup, or scheduled collector is included.

## Required tests

- Test fresh/upgrade migrations, keys/FKs, hash/size validation, UTC ordering, null response time, state/count semantics, sanitized JSON, and actual runtime/anonymous grants. Attempt update/delete/truncate/DDL and verify rejection.
- With two independent database connections, race identical registration and conflicting URI/ID descriptors. Verify one canonical record and preservation of all distinct observation IDs.
- Mock token expiry, successful renewal, renewal refusal, concurrent independent sessions, invalid credentials, rate limiting, bounded retries, and sanitized exceptions. Verify no administrator credential fallback or shared session persistence.
- Exercise successful upload with lost response, concurrent object creation, duplicate-key read/hash reuse, corrupt/truncated bytes, unsafe paths, invalid-body retention, upload failure, and database failure after upload. Registration must never claim a missing or corrupt object is usable.
- Exercise the real Storage APIs for read/create success and all required denials using backend, anonymous, and different authenticated identities. Record failures or unverified checks honestly; no hosted secret is required for PR CI.
- Leakage fixtures: receipt after cutoff; validation after cutoff; corrected body received later with an older source/event time; unknown publication time; and exactly-at-cutoff supported input. Unknown publication time does not remove receipt/validation requirements. Test the generic interface with a second-domain fixture.

## Failure decision, likely files, and handoff

Fixture work can progress while hosted authentication is blocked, but launch storage readiness stays unverified. Report the exact failing role/operation and a supported correction for review. Do not broaden grants, use a service key in ordinary jobs, add an upload server, or purchase infrastructure to bypass the gate.

Likely files: ordered `migrations/`; `src/hoop/platform/artifacts/`, evidence/run/source-contract modules, and thin CLI operations; a small SOURCE-001 report persistence bridge under `src/hoop/domains/nba/sources/`; dependency/lock files as needed; `tests/unit/`, `tests/integration/`, `tests/leakage/`, and isolated provider fixtures; a manual storage-verification workflow; nonsecret configuration/environment examples; `docs/database-setup.md`, `docs/artifact-storage.md`, README.md, AGENTS.md, and Weaknesses.md. Raw bodies and credentials remain outside Git.

Return the PR, migration/check outcomes, actual role and Storage denial evidence, cloud workflow link, Windows results, fixture artifact/run/check IDs and hashes, measured usage, setup/rotation instructions, and unresolved gates. Explain upload-before-registration recovery, why a SQL policy test alone cannot prove the hosted API, and the difference between a source failure and an empty validated response.

Approval: the owner explicitly said "lock" on October 14, 2026. This finalizes the specification and its stated null-response-time refinement; a separate coding-agent assignment starts execution. No identity, bucket, evidence table, source persistence, or hosted permission test has been implemented by this planning record.
