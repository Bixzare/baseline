# Ledger schema and baseline registration

LEDGER-001 supplies nine tables, integrity/access rules and controlled initial
baseline registration. It does not supply publication/confirmation functions.
Official forecasting remains unavailable. Hosted migrations/bootstrap/readback
are unverified while project, seed and source gates are pending.

## Integrity and access

Models and bundles are immutable identities. Each bundle component must exist,
match its target and have the bundle domain. An active pointer has the same
domain/family and a positive generation. Batches preserve their original bundle
even if a later activation changes the pointer.

Official uniqueness is occurrence + subject type + subject ID + target. It has
no model-version or role escape. The initial role is official; adding shadow or
replay write paths requires a later migration. Runtime writes remain denied.

`official_slots.decision_kind` selects a prediction or abstention. Each child has
a generated matching kind and a deferred FK to the reservation. Generated
conditional reservation columns have deferred FKs back to the selected child.
Together these enforce exactly one matching child at commit, in either insertion
order, using Postgres referential integrity rather than snapshot-sensitive row
counts. The global slot primary key arbitrates competing transactions. Missing,
contradictory and cross-batch children cannot commit.

Prediction model IDs must match the batch bundle's target mapping. Abstention
targets must belong to that bundle. Schedule observations belong to the same
occurrence; event/bundle domains agree; feature/cohort objects are registered
feature artifacts. Numeric values reject NaN and both infinities. Finite signed
values remain representable for future team margins and other domains; later
publication checks enforce NBA target ranges and full cohort completeness.

Receipts require a different transaction ID, matching policy and a time at least
as late as batch recording. These structural conditions are not proof of timely
commit or independent visibility. The next issue supplies actual clock/cutoff,
committed visibility, authoritative metadata and complete-game publication checks.
Privileged fixture receipts are not live evidence.

| Actor | Allowed scope |
| --- | --- |
| Migration/setup | Own application schema and register initial baseline through the controlled operation. |
| `baseline_publisher` | Nonlogin function owner with necessary private reads and ledger inserts; no ownership, schema creation, mutation, grants or role administration. |
| `baseline_runtime` | Private model/ledger reads; no direct ledger/model insert, receipt, active-pointer change or privileged role switching. |
| Anonymous/Storage Auth | No private ledger access. |

Internal guards resolve trusted schema-qualified objects and have no PUBLIC or
runtime execute grant. No protected publisher functions are exposed yet.

## Controlled bootstrap

A successful real MODEL-001 preparation saves
`registration-descriptor.json` under its output directory. Fixture preparation
does not create this file or invent a registered configuration artifact.
The descriptor references the exact verified config bytes and actual code/config
identity, with no learned model artifact or training cutoff.

After source/hosted gates and owner review:

```powershell
uv run --locked python -m hoop.platform.ledger bootstrap --descriptor artifacts/prepared/registration-descriptor.json --confirm-hosted-gates
uv run --locked python -m hoop.platform.ledger inspect --domain nba --family player_recent_appearance_mean
```

Bootstrap uses `BASELINE_MIGRATION_DSN` plus the separate restricted Storage
backend credentials to verify config bytes before opening a transaction. Inspect
uses only `BASELINE_RUNTIME_DSN` and verifies the connected role. Secrets remain
in environment configuration, never the descriptor or repository.

The transaction takes a bounded per-domain/family lock, registers one model per
target, the bundle, generation-one pointer, bootstrap run and activation event
atomically. The NBA descriptor covers all five launch targets; shared code does
not hard-code them. The audit records actual database times, configuration
artifact/hash, code identity, initial generation and reason.

Exact reruns preserve IDs, timestamps, generation and the initial audit event.
Changed code/config under an existing version fails. Concurrent first attempts
yield one activation. Failure between related inserts rolls everything back.
Rerunning after a later activation cannot reset the pointer. A new version after
initialization must use the separately reviewed promotion path.

## Verification and remaining gates

Real Postgres checks cover fresh/upgrade migrations, circular FK insertion orders,
partial decisions, opposite-kind races under read committed, repeatable read and
serializable isolation, invalid bundle/model/receipt relationships, SQL nonfinite
rejection, actual role denials and bootstrap concurrency/rollback/retry.
A synthetic card-game bundle/event commits a finite signed target through the
same schema without basketball columns in the shared modules.

The October 26 isolated rehearsal registered five models, one bundle and one
generation-one pointer, with one bootstrap run/event and zero forecast batches or
receipts. Runtime readback matched all five components. Bundle ID was
`216b1768-a603-5ba2-a18e-7778e002ba99`, bootstrap run
`34d69611-b515-57ec-bf3f-e79aa2c5ec20`, activation event
`1b248bc9-bb76-5658-b673-67777a689c18`; config hash was
`7b468a958ebd83f680b746aefbfb01732ea397d3bfd8da4195643f0052c29a44`
(328 canonical bytes). The disposable database was removed after inspection;
`.cache/ledger-001-rehearsal.json` retains the local report and migration hashes.
This mock-Storage/real-Postgres result does not establish hosted registration.

The final combined stack passed 326 local tests, Ruff lint/format, strict mypy,
platform boundaries, wheel/sdist build and fresh-kernel imports. Linux/Windows
PR checks are recorded independently. No required local Postgres test was skipped.

Hosted registration and restricted readback remain pending; no production schema
or pointer was changed in this batch. A reviewed real bootstrap must leave
forecast and receipt tables empty. Actual predictions wait for LEDGER-002 and
verified source/history/backup/operational readiness.

References checked October 26: [Postgres constraints](https://www.postgresql.org/docs/17/ddl-constraints.html),
[transaction isolation](https://www.postgresql.org/docs/17/transaction-iso.html),
[function security](https://www.postgresql.org/docs/17/sql-createfunction.html).
