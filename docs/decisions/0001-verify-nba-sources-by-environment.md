# ADR 0001: Verify NBA sources in their intended environments

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: choices already approved in the [critical path](../critical-path.md), [PRD v1.1, DATA-01](../PRD.md#data-01-source-verification-and-provenance), and [design Section 4](../design.md#4-source-adapters-and-access-gates). This record documents those choices; it does not claim source verification has passed.

## Context

Baseline needs historical player/team records, future schedules, game status, final results, and current rosters. The proposal identifies stats.nba.com access restrictions from cloud environments. CDN access from GitHub Actions remains unverified. A successful response alone does not establish usable fields, coverage, freshness, or permitted access.

Phase 0 must resolve these capabilities before Phase 1 can publish honest player baselines. Trained models, team forecasts, the dashboard, and awards follow later and cannot delay the opening-night launch scope.

## Decision

- Run historical stats.nba.com backfill locally through nba_api. Retain raw evidence, validate normalized records, and make collection resumable.
- Probe candidate CDN capabilities from the actual GitHub Actions runner. Verify required fields and behavior before accepting an adapter; do not infer future schedule or roster support from today's scoreboard.
- Choose accepted adapters separately for cloud and local execution. Keep the exact request/parser configuration versioned and source observations timestamped.
- Use the tested Windows collector path if a required capability fails from cloud runners but works locally. Document the need for an awake, connected machine and rehearse the fallback before launch.
- If a required schedule, roster, history, or final-result capability cannot be verified in either environment, report a failed gate and obtain a scope or source decision. Do not present incomplete evidence as working collection.
- Accept a dependable availability source or explicitly defer it. Unknown availability stays visible.
- Never spoof identity or bypass bot protection. Access denial stops the affected source run and produces a health failure under the configured retry policy.

## Reason and alternatives

This uses the environments already selected by the owner and treats source reliability as something to measure. It keeps endpoint assumptions out of model and platform code through explicit adapters.

Running every NBA request in the cloud was rejected because historical access is restricted and CDN access is unverified. Making local collection the only planned runner would add routine dependence on the owner's machine; it remains the recovery path where needed. A different permitted source can be considered only after a capability fails and its access, provenance, and cost are reviewed.

## Consequences

The launch may depend on local collection for capabilities unavailable in the cloud. This limits autonomy while that machine is asleep or offline. The dashboard and health records must expose missing or stale evidence. Later source changes need renewed capability checks and parser fixtures.

No access probe, backfill, fallback rehearsal, or injury-source selection has been executed as part of this ADR.

## Verification required during implementation

- Save evidence from the intended cloud and local environments for each required capability, including identities, UTC starts, participation, minute precision, and source timestamps where supplied.
- Review fixtures for a completed game, an upcoming game, a no-game day, roster joins, malformed payloads, and repeated requests. Verify backfill resume and duplicate handling.
- Confirm validation failures, stale responses, access denial, and source outages produce the expected health and publication behavior without attempting access evasion.
- Rehearse the local fallback and notification delivery; record machine availability and the final availability-source decision.

Approval: the owner explicitly said "lock" on October 12, 2026. Acceptance of this record does not establish that the implementation gates have passed.
