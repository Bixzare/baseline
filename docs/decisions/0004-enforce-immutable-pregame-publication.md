# ADR 0004: Enforce immutable predictions with pregame publication receipts

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD ledger requirements](../PRD.md#6-prediction-ledger-and-lifecycle), [forecast schemas](../design.md#63-forecasts-and-outcomes-phase-1), and [design publication controls](../design.md#7-ledger-publication-and-access-control). This record documents approved choices; database behavior remains to be implemented and verified.

## Context

Baseline's public track record must show predictions that were durably stored before games, using the model and inputs recorded at publication. Cloud and local recovery jobs may attempt the same forecast concurrently. A generated-at timestamp supplied by an application does not establish when a forecast became durably available.

Even a database insertion timestamp can precede transaction commit. The design therefore needs evidence that the committed forecast was visible before the publication deadline, alongside controls preventing later replacement.

## Decision

- Allow one official forecast decision per event occurrence, subject, and target. Store explicit abstentions where a prediction cannot be supported, with the same timing and provenance context.
- Aim to publish two hours before scheduled tip-off. Reject publication at or after scheduled tip-off minus 15 minutes, and whenever the game is already underway. Use the database's actual current time, not a caller-supplied or transaction-start timestamp.
- Prepare and verify immutable feature, cohort, and model references before publication. Perform no network calls inside the database publication transaction.
- Publish a complete game batch atomically: lock the occurrence, validate the schedule, roster freshness, feature cutoff, bundle, expected slots, and values, then commit predictions or abstentions and official-slot reservations together. Reject partial or conflicting content.
- After commit, use a separate database transaction to confirm that the immutable batch is visible and append a database-timed receipt before the cutoff. Confirm that the insertion and receipt transactions differ. Count a batch as validly published only with a timely receipt and no applicable invalidation.
- Identical retries preserve the original identity and content. Retry receipt confirmation for that same batch only before the cutoff. Missing or late confirmation leaves the batch unverified and counts as a coverage failure; it cannot justify replacement values or a backdated receipt.
- Runtime credentials cannot update, delete, or truncate forecast evidence, change its permissions, disable protections, or supply authoritative timestamps. Restrict publication-function access and owner privileges through migrations. Administrative access remains outside the runtime immutability guarantee.
- Append outcomes, outcome corrections, invalidations, and lifecycle events separately. Preserve the original prediction and the outcome/report version used for each comparison.
- A postponement creates a linked new occurrence, preserving the earlier forecast and exclusion. Schedule corrections or an earlier actual start can invalidate existing publication through appended evidence; a delayed-start observation cannot reopen a missed cutoff.
- Keep benchmarks, shadow forecasts, and historical replay distinct from the official record. Rehearsal uses a separate local database; these records cannot later be relabeled as official predictions.

## Reason and alternatives

Database constraints and restricted operations coordinate both runners and make immutability testable. The separate visibility receipt demonstrates that the original batch committed before the deadline, even if the insertion transaction or network response was delayed.

Application timestamps alone would leave persistence timing dependent on the caller. A single transaction timestamp would not establish timely commit. Allowing updates on retry would permit later values to replace the first forecast. Those alternatives would weaken the intended public evidence and are not selected.

## Consequences

Publication requires an additional short database transaction. A forecast may be stored but remain unverified if confirmation fails or arrives too late. That missed coverage remains visible even when the values were generated earlier. Official slots remain reserved for the original batch.

Outcome revisions can change measured error without changing a forecast, so reports and dashboard history must retain their revision references. Protected runtime behavior is not independent proof against the database administrator; see [W-11](../../Weaknesses.md#w-11-ledger-immutability-does-not-protect-against-the-database-owner).

## Verification required during implementation

- Test actual restricted Postgres roles for denied updates, deletes, truncation, schema changes, and untrusted timestamps. Verify publication-function grants and fixed object resolution.
- Exercise concurrent cloud/local writers, identical and conflicting retries, partial batches, invalid values, and stale or changed schedule/roster evidence.
- Test exact cutoff equality, a transaction opened before the cutoff but checked after it, games already started, and delayed commit. A receipt from the insertion transaction must be rejected.
- Verify timely separate-transaction confirmation, retry of the same batch, late or missing confirmation, and visible coverage failure without replacement forecasts.
- Test postponement and upstream ID reuse, earlier actual starts, outcome corrections, original provenance preservation, and separation of official, shadow, replay, and rehearsal evidence.

Approval: the owner explicitly said "lock" on October 12, 2026. No ledger constraints, publication functions, or receipt tests have been executed by this planning record.
