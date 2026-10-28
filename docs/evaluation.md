# Baseline errors and coverage

EVAL-001 provides immutable live/rehearsal reports for seven days, 30 days and
season to date. Periods are UTC and half open. The September 1 configuration is
the season calendar lower bound, not an asserted opening-night tip-off; only
regular-season events enter live reports. Replay reporting remains a separate
future input path, never a source for official live metrics.

## What a report means

Numeric error is prediction minus actual; absolute error removes the sign.
Per-target MAE is the sum of absolute errors divided by scored observations.
Minutes and counting-stat units remain separate. Confirmed DNP zeros enter overall
MAE; played-only MAE is also shown. Unknown actuals remain unscored. Zero scored
rows produce unavailable MAE with a reason. There is no challenger comparison yet.

Schedule coverage divides valid complete player batches by expected supported
occurrences. Numeric coverage divides valid numerical decisions by saved
roster-player-target opportunities; abstentions stay in the denominator. Missing
rosters or unassignable schedule times make the corresponding denominator/rate
unknown. Excluded, invalidated, stored-unverified and pending occurrences remain
visible. Actual-participant coverage and actual-minute/team groups are explicitly
retrospective diagnostics. Unavailable role/availability grouping is labeled.

Existing batches use their frozen cohorts. Uncovered games can use only both
independent roster snapshots saved before that occurrence's publication cutoff,
with verified identities and eligible freshness. Later rosters or final player
lists cannot reconstruct a missing pregame denominator.

## Reproducibility and storage

One read-only repeatable snapshot captures the eligible ledger and opportunity
references. Source/observation, receipt, lifecycle and outcome times are bounded
by the report cutoff. Schedule corrections determine the period; a late delay
cannot reopen an already closed occurrence. Outcome revisions are selected before
calculation. Artifact downloads/hash checks occur after the snapshot closes.

Compact manifests retain occurrence/observation/batch/receipt/roster/outcome IDs,
policy, code and dependency identity. Batch references bind their immutable
decisions without copying every numeric row into daily full-season JSON. Exact
reproduction reads those frozen IDs, not whichever outcome is latest today.
Changed outcomes produce a new report; old evidence remains. Artifact corruption,
missing references, changed code or a conflicting retry fails explicitly.

Reports and references are immutable under runtime credentials. Only controlled
read/append is granted; private report tables are not anonymous dashboard reads.
Database administrators remain outside that protection. Actual hosted behavior is
unverified. Fixture source/report evidence cannot establish real NBA accuracy.

## Commands and walkthrough

```powershell
uv run --locked python -m hoop.domains.nba.evaluation report --kind live --period 7d --persist --output artifacts/reports
uv run --locked python -m hoop.domains.nba.evaluation reproduce --report REPORT_UUID --output artifacts/reproduced
uv run --locked python -m scripts.rehearse_publication --reports
```

Report operations use the restricted database and separate Storage identity.
The default report kind is rehearsal; `--persist` explicitly appends evidence.
The last command requires disposable local `BASELINE_TEST_DSN`, creates/removes
an isolated database and uses invented sources with mock Storage. Notebook Run All
remains offline; its Postgres section is opt-in and uses the same operations.

Independent arithmetic checks produce 4 points MAE and 10 minutes MAE, numerical
coverage 5/6, and diagnostic participant coverage 1/2. A disposable historical
owner fixture independently produces 85.5 points MAE; a later correction produces
86.5 while the earlier report still reproduces 85.5. Owner-created fixture timing
does not verify production publication timing. The protected-ledger rehearsal's
intentional invalidation correctly produces unavailable accuracy.

Measure real report growth and runner resources before repeated scheduled season
reports; fixture byte counts are smoke measurements, not a season capacity claim.
Source/seed, hosted credentials/permissions, archival capacity and backup gates
remain open. No production report or public accuracy number was published here.

The October 27 protected-ledger rehearsal retained 4,990 report/manifest bytes and reproduced report `bce045c6-41b3-5f52-b8f9-1fbd52e775dd`. It showed one invalidated game, zero valid numerical coverage and unavailable MAE.
