# Protected publication

LEDGER-002 implements guarded fixture-tested operations. It does not activate
production. Hosted Supabase, accepted seed/source routing, raw archival capacity,
independent backup and operating readiness remain gates.

## Data flow and encoding

MODEL-001 saves `retained.json` and its registered artifact identities. Before a
transaction, the NBA client downloads and hashes prepared/cohort/feature bodies
and both roster bodies. SQL verifies the exact UTF-8 bytes against immutable
artifact hash, size, kind and schema records. JSON duplicate keys are rejected.
Each main body is limited to 2 MiB; roster arguments together to 1 MiB, with at
most 60 players and five decisions per player. These conservative project limits
need measurement against a real accepted roster before hosted rehearsal.

The versioned `publication-jsonb-v1` content hash is generated entirely in SQL
from PG17 JSONB text, including prepared content except the operational run ID,
bundle and feature/cohort references. No Python rendering is claimed to equal
Postgres rendering. Raw artifact hashes always cover original supplied bytes.
The provisional Postgres major must be checked against the real hosted project.

SQL binds saved roster/source IDs, two teams, season, full membership, the active
model/config/code mapping, cutoff-eligible history revisions, units and finite
nonnegative decisions. Missing-history players remain explicit abstentions.
The internal generic storage function is not runtime executable. Only the
explicit NBA entry point can call it for this release; platform Python does not
import NBA modules. A trusted administrator remains outside this role guarantee.

## Transactions and recovery

An occurrence advisory lock also covers observation inserts. Publication checks
the actual database clock after locking and again before returning. A schedule
delay observed after its earlier deadline cannot reopen that occurrence. Current
status and roster evidence must remain fresh. The client uses a ten-second
statement timeout and functions use a two-second lock timeout.

Transaction one stores the complete batch, predictions/abstentions and slots.
Transaction two verifies a different transaction ID and eligibility, then appends
one receipt. Its database time bounds the first commit from above. A transaction
that commits after cutoff cannot receive a timely receipt. A receipt cannot
certify its own eventual commit time; success also requires acknowledged receipt
commit/readback. Exact retries retain original IDs/times. Conflicting content
cannot replace or extend the original family batch.

After a lost response, query the stored batch and confirm that same identity.
Never prepare replacement values. Missing/late confirmation leaves original
reservations and `stored_unverified` coverage. `platform.batch_status` also checks
known invalidating observations, so a failed lifecycle append cannot temporarily
make an excluded game count. Lifecycle evidence is append-only and idempotent.
Failure audits run after rollback; unavailable audit storage is reported locally.

## Commands and rehearsal

Offline/local setup, no hosted forecast writes:

```powershell
uv run --locked python -m scripts.rehearse_publication
```

This requires `BASELINE_TEST_DSN` pointing at a disposable local service. It
creates a uniquely named database, applies migrations, uses invented sources and
mock Storage, publishes through the actual restricted role, checks exact replay,
and removes the database. The optional Postgres notebook section calls the same
rehearsal; default Run All does not connect to Postgres or live sources.

Only after separate hosted/source/backup readiness and owner review:

```powershell
uv run --locked python -m hoop.domains.nba.publication --retained artifacts/prepared/retained.json --bundle BUNDLE_UUID --confirm-hosted-gates
```

The runtime database and separate restricted Storage identity use existing env
configuration. Migration credentials never enter the publisher. No actual
production publication was performed in this batch.

October 27 local fixture rehearsal: insertion transaction `12796`, confirmation
`12797`, batch `349fdcf6-a3f9-47b7-a30e-3412cdd36fbf`, insertion
`08:03:33.488975 UTC`, committed observation `08:03:33.520878 UTC`. This is synthetic
evidence, not a season prediction. Required hosted permission checks remain open.

References: [function security](https://www.postgresql.org/docs/17/sql-createfunction.html),
[byte hashing](https://www.postgresql.org/docs/17/functions-binarystring.html),
[actual clock semantics](https://www.postgresql.org/docs/17/functions-datetime.html).
