# LEDGER-002: Publish complete batches and confirm timely commit

Status: LOCKED under the owner's batch planning approval on October 14, 2026.

Prepared: October 14, 2026

Phase: 1. Priority: launch blocker. Dependencies: LEDGER-001 and MODEL-001 implemented and owner-reviewed, with their DB-001/DB-002/DB-003 foundations. Required inputs are registered baseline identities, verified artifacts, current accepted schedule/roster evidence, and the restricted publication-owner/runtime roles. Fixture implementation can proceed while hosted inputs are blocked; official readiness cannot.

Session estimate: about 4 focused hours plus owner review and database checks. Limit work to protected operations, the shared two-transaction client, and rehearsal notebook/tests. Live collection, scheduler activation, outcomes, evaluation reports, and public dashboard remain separate issues.


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

Turn a prepared five-target player cohort into immutable ledger records with evidence that the original batch committed before the deadline. A stored batch is not valid official coverage until a timely separate-transaction receipt exists and no applicable invalidation exists. Retain failed/unverified attempts honestly.

Opening night is October 20, 2026 at 19:00 UTC, with publication targeted at 17:00 UTC. For every occurrence aim two hours before the accepted scheduled start; reject new publication or confirmation at or after start minus 15 minutes, or when the game is underway. Do not backdate, replace, or relabel a forecast.

Required guidance: AGENTS.md and `.agents/skills/hoop-postgres/SKILL.md`; use `hoop-python-testing`, `hoop-data-quality`, and `hoop-notebooks`. Locked references: [ADR 0004](../decisions/0004-enforce-immutable-pregame-publication.md), [design publication controls](../design.md#7-ledger-publication-and-access-control), [freshness/missing facts](../design.md#82-freshness-and-missing-facts), and [LEDGER-001](LEDGER-001-schema-permissions-and-baseline-registration.md). Contracts below stand alone without chat history.

## Protected operations and boundary

Add operations through ordered migrations, owned by LEDGER-001's narrow nonlogin function owner. Ordinary runtime executes only the approved entry points; direct table writes remain denied. Use fixed trusted search paths, qualified objects, validated/bounded arguments, and explicit grants with PUBLIC access revoked in the same migration transaction. Preserve ownership/DDL restrictions after any controlled ownership-transfer step. [PostgreSQL function security](https://www.postgresql.org/docs/current/sql-createfunction.html).

Keep generic transaction, slot, receipt, and idempotency logic under platform code/SQL. NBA roster/target/schedule validation belongs in a thin NBA entry point that invokes the protected shared operation. Do not make platform modules import NBA code, create dynamic plugin discovery, accept arbitrary function names, or expose the internal core as a validation bypass. The NBA entry point supports the official player family only at launch.

| Operation | Required behavior |
| --- | --- |
| Publish prepared batch | Lock the occurrence, validate complete inputs/current eligibility, derive authoritative metadata, and atomically insert batch, decisions, and official reservations. Return identity without implying the client has committed or confirmed it. |
| Confirm committed batch | In another transaction, verify visibility, a different database transaction ID, current occurrence/deadline eligibility, and absence of invalidation. Append one database-timed receipt. Never regenerate or replace the batch. |
| Append lifecycle evidence | Validate occurrence/batch/source references and append supported postponement, cancellation, schedule/start invalidation, or audit events. No value edits, cleared invalidations, fabricated receipts, or reopening old slots. |

## Input integrity and completeness

- Upload/read/hash-check required artifacts before opening the publication transaction. Pass their registered IDs and the small serialized content needed for validation, including cohort and both roster memberships. SQL checks hashes/size/schema against immutable artifact records before interpreting that content. No network calls or object-store downloads occur inside transactions.
- Hash the exact supplied bytes under a versioned encoding/serialization contract; do not assume Python JSON serialization and Postgres JSONB rendering produce identical bytes. Use supported server SHA-256 functionality verified against the actual project version; [binary-string hashing](https://www.postgresql.org/docs/current/functions-binarystring.html). Reject duplicate keys/slots, malformed identities, schema/version mismatch, nonfinite numbers, and oversized inputs. Set and document measured payload/transaction limits before hosted rehearsal.
- Bind roster payloads to their persisted NBA roster_snapshot/member-artifact/source-check IDs, team, and season. Derive expected player IDs from those verified memberships. Require the prepared cohort to match exactly, including rookies, reserves, and unknown availability. Each expected player has exactly five target decisions: minutes, points, rebounds, assists, and threes made. Each decision is one numeric value or one abstention, never both.
- Bind feature/cohort IDs, cutoff, generation metadata, input references, and prepared values to the same immutable preparation manifest. Validate accepted history/source references at the feature cutoff and valid target units/ranges. A changed roster or incompatible preparation requires preparation again before the first stored batch, not silent editing during publication.
- Validate the active registered player bundle and each target's model/configuration mapping at insertion; reject a stale or substituted descriptor. Freeze those IDs in the batch. A later activation never changes an existing batch and does not justify regenerating it during confirmation.
- SQL proves agreement with persisted references and roster content; it does not independently prove source truth or model accuracy. Hashes and runtime restrictions are not a guarantee against an administrator changing both evidence and permissions.

## Time, schedule, and freshness

Use the database's actual current clock after acquiring locks and again before returning from guarded writes. Derive recorded_at and insertion/confirmation transaction IDs in the protected operations; caller-supplied authoritative fields must be rejected or absent from the interface. Do not use transaction-start time for the deadline; [PostgreSQL time functions](https://www.postgresql.org/docs/current/functions-datetime.html).

Require successful schedule/status evidence no more than 30 minutes old and referenced roster evidence no more than 24 hours old at publication, with supported source-generation freshness and identity checks. All model inputs must have been available by their feature cutoff. A newly observed game-status check may validate publication safety after that cutoff; it cannot become a later model feature. Current accepted status/known actual start may veto publication even when an older prepared schedule said upcoming.

Apply the stored schedule history and versioned cutoff policy, not a caller-selected tip-off. A supported correction accepted before the previously effective deadline can update the schedule. A later delayed-start observation cannot extend a deadline already closed for the same occurrence. An earlier correction that places the deadline in the past immediately blocks new publication/confirmation. Test both ordinary timely corrections and prohibited reopening. A verified postponement uses a linked new occurrence through the collector; it never frees old reservations.

Known underway/final/postponed/canceled states and contradictory essential evidence block new official writes. Later evidence of an earlier actual start or an invalidating schedule correction appends an invalidation and changes derived validity, preserving original values/receipts. Suspended/unresolved occurrences remain explicitly pending until their treatment is verified; do not infer a fresh occurrence automatically.

## Two-transaction client and retry contract

1. Verify prepared artifacts and consult existing official state. If a player batch already exists for the occurrence, reuse that stored identity/content; do not extend its cohort or create replacement values even if new players would not overlap existing slots.
2. In transaction one, call the protected publication entry point and commit the complete batch/decisions/reservations together. Bound lock waits and statement duration. An error rolls back every forecast row and reservation from that attempt.
3. Start a new transaction to confirm committed visibility. Compare its database transaction ID with the stored insertion ID. Append observed_committed_at using the database clock only when strictly before the effective cutoff and the occurrence remains eligible, then commit. This time is an upper bound on the original batch's commit, not its exact commit timestamp.
4. Report success only after receipt persistence is acknowledged or read back. Do not wrap both operations in one surrounding transaction. Use independent connections in integration tests; the real client may reuse a connection after a completed commit as long as transaction identity changes.

Define a content hash over the versioned immutable forecast payload, including occurrence/bundle, cohort/feature references, cutoff/generation, units, values, and abstention reasons. Operational retry run IDs and server recording/receipt times do not create new forecast content. Verify the hash server-side rather than accepting a caller's claimed hash.

Exact retries return original IDs and timestamps. Different content, added/removed cohort members, changed targets/models, or a reused ID with different content fails. After a lost commit response, read stored state and confirm the same batch rather than prepare again. A confirmation retry returns an existing receipt unchanged; after cutoff, this is readback only, not a new receipt or success for an unverified batch.

Missing/late confirmation retains the original batch/reservations as unverified and excludes it from valid official coverage. No replacement, deletion, backdated receipt, or automatic retry beyond cutoff. Preserve database rejection reasons through sanitized run events in a separate transaction after rollback; if the database is unavailable, retain a local failure report without claiming durable audit recording. A transient retry must be bounded and recheck authoritative eligibility.

## Execution sequence and notebook

1. Inspect the actual MODEL-001 manifest/encoding and LEDGER-001 guards. Implement compatible hash/content binding and the protected platform/NBA operations without weakening existing grants or creating another forecast writer.
2. Implement the shared client protocol and a derived read result distinguishing stored/unverified, timely-confirmed, invalidated, and excluded/pending records. A raw prediction row or receipt alone must not imply current validity.
3. Extend `02_baseline_and_ledger.ipynb` on small fixtures in a separate disposable Postgres database. Show prepared cohort, atomic insertion, commit/receipt transaction distinction, exact retry, missing confirmation, and invalidation. Explain that outcome reconciliation comes in the later outcome issue.
4. Add actual-role, transaction, concurrency, cutoff, leakage, and fresh-kernel checks to PR CI using disposable Postgres. Use a fixed-clock pure policy helper for exact arithmetic boundary tests and actual database clock/transaction barriers for integration tests; production entry points never accept a test clock override.
5. After owner review, apply function/grant migrations through DB-001 tooling and verify hosted runtime execute/denial behavior without inserting fake production forecasts. Real official publication is reserved for the later readiness/launch assignment. Record unexecuted hosted publication checks honestly.
6. Update README, AGENTS.md under 200 lines, publication/recovery notes, and Weaknesses.md with exact commands, statuses, and remaining source/orchestration gates.

## Acceptance criteria

- [ ] Restricted runtime can execute only guarded entry points; internal bypasses, direct writes, authoritative-field forgery, role switching, and unsafe object resolution are rejected.
- [ ] Complete saved roster cohorts and five decisions per player are enforced using bound artifact content. Partial/mixed/malformed batches and invalid model/source/time references cannot commit any forecast rows or reservations.
- [ ] Publication and confirmation use current database time and different transactions. Equality/late arrival, early starts, stale essential inputs, and reopening an already closed deadline are rejected.
- [ ] Concurrent cloud/local attempts cannot replace or extend official content. Exact retries/lost responses preserve IDs, values, recording times, and receipts.
- [ ] Missing/late confirmation stays unverified with original reservations. Derived valid coverage requires a timely receipt and no applicable invalidation; corrections never alter original predictions.
- [ ] Notebook/CLI share the tested protocol in a separate disposable database. Default Run All cannot write production forecasts or contact live sources.
- [ ] PR checks and real Postgres tests pass. Hosted permissions are separately verified; no rehearsal record is inserted into the production ledger or represented as an official season forecast.

## Required tests

- Independent connections racing identical and conflicting complete batches; forced partial insertion failure; reservation/decision-kind conflicts; changed cohort with no overlapping subjects; invalid active bundle; malformed payload/hash/encoding; nonfinite/negative NBA values; wrong units; and cross-domain references.
- Actual restricted-role denial of direct writes, internal core execution, PUBLIC/anonymous invocation, supplied authoritative times/transaction IDs, mutation/grant/role changes, and temporary-object/search-path substitution. Test a synthetic second-domain core fixture without NBA imports.
- Cutoff equality in pure comparison tests, and real database transactions opened before but checked after cutoff. Hold/release locks across the deadline and delay first commit beyond it. Verify that no second-transaction receipt can certify a batch not visible before cutoff.
- Same insertion/confirmation transaction; successful separate visibility; lost insertion/receipt responses; retry before/after cutoff; absent/late receipt; and changed active pointer after insertion. Original batch identity/model references never change.
- Missing/stale roster or schedule, newer started status, timely schedule correction, late delayed-start reopening, earlier actual start, invalidation, postponement/upstream-ID reuse, and unresolved suspension. A new occurrence may receive a new batch without restoring the old one.
- Explicit leakage: source receipt/validation after feature cutoff, future result, eventual participant/start list, late roster membership, and substituted history/feature bytes. Complete cohort checks cannot pass with only eventual participants or successful predictions.
- Fresh-kernel notebook execution against disposable fixtures with production connections/live transport blocked; semantic CLI equivalence; bounded retries; failures recorded outside rollback; and clear local-only reporting when database audit persistence fails.

## Failure decision, likely files, and handoff

Permission, source, artifact, timing, or completeness failure blocks the affected write. Do not loosen grants, skip receipt confirmation, fill missing players with zeros, publish a partial batch, or use an admin credential in the client. An implementation with passing fixtures but missing required hosted/source gates remains not launch-ready.

Likely files: ordered function/grant `migrations/`; `src/hoop/platform/ledger/` and shared run/artifact helpers; NBA publication validators/entry points; thin CLI; versioned publication/serialization policy; `tests/integration/`, `tests/unit/`, `tests/leakage/`, `tests/notebooks/`, and fixtures; `02_baseline_and_ledger.ipynb`; publication/setup notes, README.md, AGENTS.md, and Weaknesses.md. No collector workflow, production fixture forecasts, dashboard, or outcome evaluator.

Return the PR, exact checks, migration/grant evidence, separate transaction IDs/times from rehearsal, race/delayed-commit/retry results, cohort binding evidence, notebook walkthrough, derived status examples, and unverified hosted gates. Explain the difference between generation, insertion, committed visibility, and receipt persistence, including one lost-response recovery scenario.

Approval: the owner authorized "lock for the remaining backlog" on October 14, 2026, retaining the launch-first planning order. This finalizes the specification; a separate coding-agent assignment starts execution. No function, publication client, receipt, invalidation, notebook execution, or official forecast has been implemented by this planning record.
