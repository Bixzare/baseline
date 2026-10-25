# ADR 0013: Prefer pinned bulk history with bounded, versioned repairs

Status: DRAFT decision record of the direction authorized October 25, 2026.
Owner review/lock of this record and runtime source acceptance remain pending.
The authorized source assessment can proceed without adopting the candidate seed.

## Context

Repeated full historical API collection adds access and request-volume risk.
The inspected Eoin version 525 supplies all five player targets and recent team
records, but contains invalid IDs, nonparticipation/missing-minute cases, and
older-season gaps. Wyatt version 238 does not establish the required recent
player-game history in its actual published files. See the [assessment](../dataset-comparison.md).

## Proposed decision

Use the [historical-data amendment](../PRD-data-source-amendment.md): pinned Eoin
basic files as candidate base, explicit normalization/quarantine, an independently
collected game-inventory cross-check, and local nba_api only for identified
repairs under accepted access policy. Preserve immutable base/patch provenance
and later observation times. Routine reads use validated artifacts.

Keep unknown participation and availability explicit. Collect pregame evidence
prospectively instead of reconstructing unsupported historical cohorts. Defer
injury ingestion for the first release and retain the existing promotion gates.
Rebaseline delivery to a future verified slate without backfilled predictions.

## Tradeoff

A bulk seed reduces upstream calls and makes repeated training reproducible, at
the cost of a second parser, a quarantine/repair report, and publisher/version
dependence. Rebuilding every box score or integrating two bulk datasets adds work
without resolving historical pregame timing. Neither is selected for this MVP.

## Verification

Check checksums, exact game coverage, IDs/joins, minutes and timezone semantics,
DNP/unknown distinctions, source-use conditions, immutable patch lineage, and
fresh-kernel offline execution. Keep source acceptance, runtime operational
access, full-seed completeness, backup, and production readiness separate.
