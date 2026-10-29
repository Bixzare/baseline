# Source-confirmed inactive-player repairs

The offline helper `hoop.domains.nba.sources.inactive_repairs` prepares the existing
string-field overlay format. It does not fetch NBA data, apply a repair, accept a
seed, write database facts, or infer nonparticipation from zeros or missing rows.

```powershell
uv run --locked python -m hoop.domains.nba.sources.inactive_repairs --archive PATH_TO_ARCHIVE --evidence PATH_TO_RETAINED_SUMMARY --output artifacts/inactive-repairs
```

Repeat `--evidence` for each retained snapshot. Inputs must contain the original
HTTP bytes, request identity and single receipt. The helper verifies their hashes,
chronology, final game, exact IDs, venue, both team scores and inactive identities.
Conflicting identities, positive minutes/statistics, malformed input or ambiguous
membership cannot produce an inactive repair. Missing players stay unresolved.
New output files finalize atomically; exact retries reuse identical evidence.

Prepared patches bind the original CSV hash/record/base-row hash and source bytes.
They repair missing identity/competition fields and annotate confirmed inactivity
with no invented injury reason. Applying them remains a separate local backfill
operation through `build_seed` or the documented `--repair` CLI. Repair evidence
advances availability; it cannot backdate an earlier feature snapshot.

The actual October 29 intermediate candidate applied 129 source-confirmed patches,
reducing quarantine from 135 to six. Its 32,305 player rows include 26,648 played
and 5,657 confirmed nonparticipants; 2,460 valid team sides remain. The intermediate
candidate is incomplete and unaccepted. See [the measured report](reports/2026-10-29-inactive-repairs.json).

Typed appearance/exclusion and compact-window review under ADR 0018 follow in a
separate change. This helper does not implement or authorize those operations.
