---
name: hoop-python-testing
description: Design and run Baseline pytest coverage for Python features, data validation, temporal leakage, database integration, orchestration, and CI. Use when implementing or reviewing Python changes and regressions.
license: MIT; upstream notice in LICENSE.txt
---

# Baseline Python testing

Locked project adaptation of wshobson/agents `python-testing-patterns`, approved October 12, 2026.
Source revision and review notes are in the repository's `skills/README.md`.

## Select meaningful checks

Translate each issue acceptance criterion into an observable result or invariant before implementation.
Use fixed fixtures, explicit expected values, and parametrized boundary cases. Assertions must not recalculate the answer using the implementation under test.
Avoid coverage targets that reward trivial tests. Every feature still needs its applicable automated tests.

| Change | Required emphasis |
| --- | --- |
| Parser or adapter | Schema, identity, nulls, units, duplicate/revised data, transient/permanent failures, freshness. |
| Feature or baseline | Exact values, history boundaries, season rollover, trades, missing history, zero denominator, future exclusion. |
| Ledger or migration | Real Postgres, runtime/public roles, duplicate workers, immutable rows, deadline boundary, interrupted publication. |
| Training or promotion | Chronological splits, fitted-transform boundaries, artifact identity, matched coverage, gate boundaries, failure retention. |
| Scheduler | Missing invocation, duplicate trigger, cooldown, stale source, fallback race, safe recovery. |
| Notebook | Fresh-kernel fixture run, package/CLI equivalence, explicit cache identity, no default production writes. |

## Isolation

- Keep unit tests in `tests/unit/`, Postgres checks in `tests/integration/`, temporal checks in `tests/leakage/`, and walkthrough checks in `tests/notebooks/`.
- Use sanitized fixtures in `tests/fixtures/`. Routine PR tests must not contact live NBA services or production databases.
- Mock network boundaries, not the data and permission behavior being verified.
- Test Postgres constraints with the actual restricted roles. SQLite and owner-only tests cannot establish ledger protection.
- Inject a clock for Python time logic; separately test the database's own clock and transaction behavior.
- Use fixed seeds when randomness matters. Avoid arbitrary sleeps and execution-order dependencies.

## Leakage cases

Freeze a prediction cutoff, then add a future game, later injury report, corrected box score, final-season aggregate, or future roster change.
Earlier features, cohorts, and predictions must remain identical. Include UTC date changes and daylight-saving boundaries.
Fit preprocessing only on training observations. If minutes predictions feed rate training, ensure they are generated without fitting on the same row's outcome.
Backtest records must never become official live forecasts.

## Run and report

Use the verified project commands in `AGENTS.md` once bootstrap creates them; do not install ad hoc global dependencies.
Run the affected checks, then the required PR suite. Investigate failures rather than weakening assertions or skipping required integrations.
Return exact commands and outcomes, acceptance criteria covered, and checks not run with reasons.
Tests requiring actual source access belong to explicit source verification tasks, with saved evidence.
