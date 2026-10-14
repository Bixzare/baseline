---
name: hoop-data-quality
description: Build or review Baseline source adapters, backfills, normalization, data contracts, source health, and point in time feature inputs. Use for NBA data engineering and source failure investigations.
license: MIT; upstream notice in LICENSE.txt
---

# Baseline data quality

Locked project adaptation of wshobson/agents `data-quality-frameworks`, approved October 12, 2026.
Source revision and review notes are in the repository's `skills/README.md`.
Use the assigned issue and approved contracts. This skill does not approve draft design details.

## Workflow

1. Identify the capability required: history, future schedule, status, final box score, roster, or availability. Record required fields and coverage before selecting an endpoint.
2. Prove that capability from its intended execution environment. Treat schema, dates, identifiers, and completeness as evidence alongside HTTP status.
3. Define the raw-to-normalized contract: keys, types, null meanings, units, acceptable ranges, uniqueness, relationships, and timestamps.
4. Preserve raw bytes and a manifest before parsing. Include source/request identity without credentials, collection time, checksum, run ID, and parser version.
5. Validate before publishing usable data. Quarantine invalid inputs with an actionable reason and retain unaffected processing when possible.
6. Make backfill resumable. Repeat collection without duplicate normalized versions; preserve legitimate revisions with their new availability times.
7. Document the run and its limitations in the relevant notebook through shared package operations.

## Temporal correctness

- Keep event time, observed/source time, collection time, and feature cutoff distinct.
- Live features use only versions collected and validated by their cutoff. Never substitute the latest version for a historical version.
- Build aggregates from eligible prior events, excluding the target event and all future information.
- Choose the prediction population from the saved roster, not eventual participants.
- Missing injuries mean unknown availability. Missing roster evidence is not a successful empty population.
- Historical collection today cannot establish when a field was available years ago. Record assumptions and omit indefensible features from primary backtests.

## Operational boundaries

- Local `nba_api` for historical stats; verify CDN access on the actual cloud runner before relying on it.
- Honor source restrictions. No spoofing, proxy rotation, or bypass attempts.
- Use bounded retries and recorded request policy. No assumed guaranteed NBA rate limit.
- Validate freshness, expected coverage, missing scheduled runs, and reconciliation backlog, not only request failures.
- Source failures block affected forecasts and promotion according to approved policy; preserve incident history.
- Use pandas, explicit validation, and pytest first. This adaptation does not introduce Great Expectations or dbt.

## Evidence to return

- One valid fixture plus malformed, incomplete, stale, and revised variants; joins and keys verified.
- A repeat/resume check; zero games distinguished from failed or incomplete retrieval.
- Leakage checks proving future games, later corrections, trades, and late availability cannot change earlier features.
- A compact manifest/validation summary, exact environment tested, unresolved coverage, and recovery behavior.
