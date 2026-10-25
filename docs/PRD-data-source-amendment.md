# Historical data and recovery amendment

Direction authorized by the owner on October 25, 2026: incorporate the dataset
gap strategy into the plan and resume sequential issue execution. This amends
the historical source approach, not the five player targets or release gates.
Actual source/seed acceptance and owner diff review remain required.

## Historical seed and repairs

- Prefer the inspected Eoin Moore version 525 basic game, team, player-stat,
  and player-identity files as the candidate 2025-26 seed. Pin version and hashes.
  Do not ingest a floating latest version or treat metadata as completeness.
- Preserve original downloaded bytes and manifests. Normalize into versioned
  artifacts only after validation; training and dashboard reads use local/stored
  artifacts rather than making repeated historical API calls.
- Quarantine invalid IDs, conflicting records, unsupported competition, and
  unresolved targets. Preserve their source row identity and an actionable reason.
- Resolve the two observed team ID 0 rows and 130 player rows with no team ID
  explicitly. No guessed team assignment or silent deletion from coverage counts.
- Missing minutes are distinct from zero minutes and confirmed nonparticipation.
  Supported DNP/DND/NWT comments are outcome evidence only, subject to an explicit
  parser policy. Ambiguous rows stay unknown; zero alone is not DNP proof.
- Restore canonical ten-digit game IDs, preserve player/team IDs as strings,
  document minute precision, and verify source timezone semantics including DST.
  Classify regular-season Cup games using verified competition mappings.
- Reconcile exact games against a separately collected expected-game inventory.
  Record its provenance. Shared NBA origins mean this is a cross-check, not a
  wholly independent guarantee. A matching aggregate count alone cannot pass.
- Generate a bounded repair list with source row/game/player identity, failed
  contract, required evidence, and resolution state. Use local nba_api only for
  identified missing/conflicting evidence, subject to reviewed request policy.
  Preserve patch source, original record reference, collection time, and versions.
  Never overwrite a raw dataset or backdate a correction's availability.
- The existing stock-header permission was diagnostic only. Do not broaden it,
  replay cookies, impersonate TLS, rotate proxies, or retry denied hosts to make
  a repair pass. Source configuration acceptance is still an explicit gate.
- If repair is unavailable, expose the gap and block affected source/seed
  acceptance or record the approved target-specific abstention. Unaffected work
  can proceed; coverage must retain excluded/unknown cases.

## Scope and evaluation

The MVP retains five player baseline targets, immutable publication, outcomes,
coverage, source health, and recovery. Team forecasts follow that increment.
Start with 2025-26 only. Repair earlier seasons before using them for later
multi-season training; all-time comparisons, detailed historical rotations,
historical injury reconstruction, awards, and live tracking remain deferred.

Explicitly defer injury ingestion for the first release; availability is unknown.
Do not infer a historical forecast roster from final box-score participants,
starter fields, or nonparticipation comments. Keep historical backtest assumptions
visible. Save schedule, roster, availability if later adopted, feature, forecast,
and outcome versions prospectively. Keep the baseline until existing full-cohort
promotion gates pass; participant-only exploration cannot waive them.

The dataset does not replace fresh schedule/status, current roster, or final-result
verification. Cloud access is unresolved; local recovery needs working source
evidence and the later awake/connected scheduler rehearsal.

## Execution and delivery

SOURCE-001 resumes first with a reusable offline dataset assessment and repair
report; it may return truthful failed/unverified gates. DATA-001 follows reviewed
historical interfaces and builds resumable normalization, Parquet, and the source
walkthrough. Later tasks retain their existing dependency order.

The October 20 target has passed. Release at the next future slate for which all
readiness gates pass; do not invent a new guaranteed date. Historical replay stays
separate from official live predictions. Never insert retrospective forecasts to
fill missed opening-night coverage. Owner review remains required for each PR.

Acceptance: deterministic malformed/identity/participation/precision fixtures,
immutable repair lineage and leakage tests, expected-inventory and unknown-coverage
cases, fresh-kernel fixture execution, and a measured real-seed report. No source
or seed is accepted merely because those tests pass.
