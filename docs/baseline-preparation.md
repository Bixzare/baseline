# Prepared player baselines

MODEL-001 prepares values and abstentions. It does not create official ledger
entries, activate a bundle, fetch NBA data or run a trained model. Real input
rehearsal remains gated by accepted seed/history, current schedule/roster mappings
and hosted database/artifact verification.

## Fixture walkthrough

Run `notebooks/02_baseline_and_ledger.ipynb` in a fresh project kernel, or:

```powershell
uv run --locked python -m hoop.domains.nba.baselines fixture --input tests/fixtures/nba/preparation.json --output artifacts/baseline-fixture
```

This invented fixture has three roster members and fifteen target slots. Two
players have history, producing ten numeric values; the rookie has five explicit
abstentions. Player 201 has 10/30 minutes and 4/20 points: mean minutes = 20,
pooled points rate = 24/40, composed points = 12. The same common-window identity
gives rebounds 5, assists 3 and threes 2. Availability is descriptive; an unavailable
flag does not alter the baseline. This is arithmetic verification, not accuracy.

## Cohort, evidence and common windows

Use saved current rosters for both teams, including reserves and players without
history. Unknown availability remains unknown. Missing/conflicting/stale rosters
or a missing/started/stale schedule block the game. Schedule evidence must be
received/validated by the cutoff and at most 30 minutes old; rosters at most 24
hours. Known stale source publication/generation also blocks readiness. Publication
will recheck these conditions at its own actual time.

The database capture reads selected schedule/roster identities and player history
inside one repeatable-read, read-only snapshot. Membership IDs are declared in
the roster artifact manifest. After closing the transaction, download/hash-check
those exact immutable roster objects and compare their membership. No network call
occurs inside the database transaction. A new database version cannot silently
replace those captured identities.

Cutoff eligibility precedes latest-revision selection, using the shared source
helper. Exclude the target occurrence and equivalent source game ID, future or
nonregular games and confirmed DNPs. Order up to ten prior appearances across
seasons/teams using verified actual starts or a verified source calendar. Dates
remain dates. Unknown/ambiguous ordering that affects the window produces an
abstention; IDs never serve as a chronology shortcut.

Freeze the appearance window before assessing values. Missing/invalid minutes,
nonpositive denominators or unresolved relevant history abstain all five targets.
Missing one counting stat abstains that target only. No older row replaces a recent
incomplete appearance and no smaller target-specific window is used. Gaps outside
a complete selected window need not block it. Relevant gaps request reconciliation.
Fewer than ten appearances are permitted and flagged. Valid overtime is uncapped.

Every member gets five values or explicit null/reason pairs. Output retains full
precision, target units, history counts, selected fact/check IDs and values,
cohort/source identities, cutoff, generation time, code/config/dependency hashes,
availability and target completeness. Nonfinite input evidence is retained as an
explicit invalid-value marker, never emitted as an invalid numeric forecast.

## Snapshot and real-input operations

`save_local` verifies content-addressed cohort, feature, descriptor and prepared
objects before reusing a snapshot. Later facts or target-game participants cannot
alter cutoff-ineligible inputs. Prepared files explicitly carry no publication
receipt and cannot assert official publication. The shared entry/snapshot contract
also accepts a synthetic card-game subject and signed target.

After owner review and source/hosted gates, the separate operation is:

```powershell
uv run --locked python -m hoop.domains.nba.baselines prepare --event OCCURRENCE_UUID --cutoff UTC_TIMESTAMP --output artifacts/prepared --confirm-hosted-gates
```

It reads accepted production evidence, retains verified config/cohort/features/
prepared artifacts with the separate runtime credentials, and records run events.
The configuration artifact hashes to the descriptor's canonical config hash. The
next issue registers model/bundle identities from this descriptor. Artifact failure
leaves the operation incomplete; no official candidate/receipt is created.

The initial 288-test combined suite passed locally, including both learning
notebooks plus the diagnostic notebook, baseline arithmetic, missingness,
late/future/target exclusion, role/revision reads and a mock-Storage integration
guard proving downloads occur outside transactions. Hosted source preparation
and forecasting readiness remain unverified. Later ledger functions must enforce
publication cutoff, complete slots and committed-visibility confirmation.
