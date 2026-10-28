# Local historical seed workflow

DATA-001 implements a candidate archive, not production acceptance. The first
supported source is the pinned Eoin 525 basic snapshot for 2025-26. No database
rows, forecasts, or public data are written. The source notebook defaults to
invented fixtures; the full-data CLI is an explicit operation.

## October 25 local evidence

The separately collected LeagueGameLog team inventory contains 1,230 unique
2025-26 regular-season game IDs. Exact IDs match Eoin 525, with no missing or
unexpected games. This required one approved local request, with a 30-second
timeout and no retries. Inventory evidence is retained under run
`ec872caa5377441c9623dc7b1c60a43c`, with body SHA-256
`8030861397de701ff20a51c4316731080e648ac751e4be80c68e2e786c9dd9cc`.
The separate canonical inventory-manifest hash is
`8ad2be7b9f55eb17d64477377903a0c405e28fa7b458015eb6c163178a0ad785`.
These identify different bytes; the earlier body-hash label was incorrect.

The full normalization retained 32,176 player rows (26,648 played and 5,528
explicitly did not play) and 2,460 team rows. It quarantined 133 player records
and two team records. No patches were applied. The seed is **incomplete**, not
accepted for import. Game completeness does not resolve ambiguous player history.
The unpatched player and team Parquet hashes are respectively
`eabc2a87a61e86c337ba5f199b63286c7f96d1207ed7955022e3fec1d34162dd`
and `f69e4fa997ff5bd8435066f4551dda66115399d1df0976a1a960808559a1775a`.
The archive occupied 438,881,722 bytes after the first run; later manifest
versions add small amounts. Backup synchronization remains unverified.

Original raw bodies, quarantine details, candidate manifests and observations
remain in ignored `artifacts/seed-2025-26/`. The manifest records exact parser,
dependency, lock and input identities. Each candidate remains immutable;
the convenience pointer always says `source_accepted: false`.

Observed October 25 candidate unit:
`18382472ce93cf99480403e1c9881da7e2253451bbd2f4bd40765a4c26004df6`.
A repeat of the full-data command verified hashes and reused this completed
candidate in 6.1 seconds. Exit status 1 is intentional for an incomplete seed;
replay does not convert it into an accepted one. Local Windows validation passed
170 tests, Ruff lint/format, mypy, the domain boundary, wheel/sdist build and a
fresh project-kernel import check. Hosted CI is separate evidence.

## Fixture walkthrough

Select the Baseline Python 3.12 kernel and run
`notebooks/01_sources_and_backfill.ipynb` from a fresh kernel. It calls the same
`build_seed` operation as the CLI and demonstrates readback and verified reuse.

```powershell
uv sync --locked
uv run --locked python -m hoop.cli seed --source tests/fixtures/nba/seed --manifest tests/fixtures/nba/seed/manifest.json --inventory tests/fixtures/nba/seed/inventory.json --archive artifacts/seed-rehearsal
```

The command reports candidate status, not source acceptance. Missing inventory
or unresolved data produces an incomplete report and exit 1. This is deliberate,
not a successful complete seed. A replay reuses verified artifacts; it still
records another source observation. Run `uv run --locked pytest` for offline
fixtures and fresh-kernel execution; no live NBA request occurs in PR checks.

## Retained real inputs and independent inventory

The historical source root contains the four basic CSVs. Supply a manifest with
`source_id`, positive `dataset_version`, timezone-aware `collected_at`,
`evidence_kind` (`observed_download` or `synthetic_fixture`), and a `files` map
of filenames to exact SHA-256 hashes. Preserve the original download receipts.
Do not regenerate a collection time from the date of a later local copy.

The owner approved unchanged released nba_api defaults for bounded local
inventory/targeted repairs on October 25. No copied cookies, custom identity,
TLS impersonation, proxy rotation, or retry after denial is permitted.

```powershell
uv run --locked python -m hoop.domains.nba.sources.inventory --season 2025-26 --archive artifacts/source-inventory --confirm-local-machine
```

This makes one team-game-log endpoint call with a 30-second timeout and no
retries. It preserves raw response bytes before native parsing. It requires
two distinct team sides for each regular-season game. The returned inventory
includes exact game IDs, source identity, actual observation time, and raw hash.
Collection shares underlying NBA provenance with the bulk publisher; it is a
separate collection cross-check, not a wholly independent source guarantee.

```powershell
uv run --locked python -m hoop.cli seed --source PATH_TO_PINNED_CSVS --manifest PATH_TO_DOWNLOAD_MANIFEST --inventory PATH_TO_RETAINED_INVENTORY --archive PATH_TO_LOCAL_ARCHIVE
```

Personal source/archive paths stay out of tracked configuration. Source objects
are copied and hashed into content-addressed `objects/`. Normalized player/team
Parquet, an immutable seed manifest, run observations, and quarantine reasons
remain inside the archive. `checkpoints/` and `candidate-current.json` are
replaceable convenience state, verified against immutable artifacts before reuse.
Corrupt/missing objects or a changed checkpoint fail reuse rather than silently
accepting partial data. A process interrupted before checkpoint finalization can
restart; complete objects are deduplicated, and partial files are never accepted.

## Interpretation and limitations

- IDs remain strings, including canonical ten-digit game IDs. Trades retain the
  team observed for that game rather than applying a player's current team.
- Counting stats are finite nonnegative integers. Overtime scores remain intact.
  Minutes convert to seconds with the original reported text and precision.
- Supported nonparticipation comments are outcome evidence. Null/zero alone is
  not DNP proof. Ambiguous rows are quarantined and retained in coverage reports.
- Regular-season IDs and allowed competition labels must agree. Other seasons,
  preseason, and Cup finals do not enter this seed. Regular-season Cup games
  retain their original source classification and normalized regular competition.
- Source date/local datetime is retained; UTC start remains null until source
  timezone semantics are independently verified. No midnight UTC is invented.
- Normalized records reference raw hashes and CSV record numbers. Artifact/run
  manifests retain source receipt and validation times. Historical availability
  and pregame roster reconstruction remain unverified.
- Same input/parser/config identities can reuse normalized versions. Corrections
  and repair evidence create distinct versions, preserving earlier artifacts.
- No backup or remote synchronization is claimed by building a local archive.
  BACKUP-001 must verify off-device delivery and restoration before release.

## Explicit repair overlays

Optional `--repair PATH` accepts a JSON overlay, never an edit to a raw CSV.
Required fields: source identity; target file and CSV record number; parent raw
SHA-256; canonical base-row SHA-256; string-valued column changes; reason; actual
evidence collection time; evidence filename relative to the overlay; evidence
SHA-256. Evidence bytes are archived before a repaired version is finalized.
The `row_hash` helper calculates the canonical row identity before normalization.

Conflicting overlays, stale parent rows, missing evidence, future receipt times,
and changed hashes fail. A repaired version's availability cannot precede its
evidence/validation. Earlier checkpoints remain independent. This interface
does not authorize broad recollection or automatic guessed repairs.

## October 28 read-only quarantine audit

Inspect the retained candidate without another NBA request or database write:

```powershell
uv run --locked python -m hoop.domains.nba.sources.seed_audit --archive artifacts/seed-2025-26 --report artifacts/seed-quarantine-audit.json
```

The command verifies the immutable manifest, normalized objects, relevant original
raw checksums, and each referenced CSV record. The saved report includes exact
base-row hashes for a later evidence-backed overlay, raw identity/minute/comment
fields, and normalized subject overlaps. Exit 0 means the audit completed, not
that the seed passed acceptance. It never changes the candidate pointer.

The actual audit found 135 quarantined rows across 20 games: 80 player identity
failures, 50 blank/unsupported player competition labels, three ambiguous player
participation/minute records, and two invalid team records. Every affected game
has two valid normalized team sides. None of the quarantined subjects overlaps a
valid normalized subject in that game. All 133 player rows have zero values for
the four requested counting statistics; that does not establish DNP. All 135
remain unresolved. Report manifest SHA-256:
`1a98b146ef110647fcd165c7928abeb8b7df42d5ca3521cb413d1033449db123`.

One bounded local BoxScoreTraditionalV3 request for game `0022500641` returned
HTTP 200 using unchanged released nba_api 1.11.4 defaults, without retries.
It confirms player `1628396` belongs to team `1610612754` in that response, but
still reports `0:00` and an empty comment. That does not resolve participation.
The complete response and timestamps are retained under local run
`b0da2baf2cf84c059a5ada3500c46291`; no repair overlay was applied.
A single CDN request with Baseline's normal identity for the same historical box
score returned HTTP 403 under run `83f259dbc6e349b9acfc23e4a0a0112c`.
No CDN retry or alternate identity was attempted. This is local historical-access
evidence, not proof about the separate current-game or cloud capabilities.

A separate offline gzip audit reduced the four original files from 438,321,084
to 60,615,087 bytes and verified exact decompression checksums. No files were
uploaded during that measurement. The largest encoded file still exceeds 16 MiB.
The owner then locked [ADR 0017](decisions/0017-encode-large-raw-archives-with-verified-parts.md),
and its bounded archive implementation is in the platform follow-up PR. Quarantine, acceptance, date
semantics, hosted readback, and full independent backup remain separate gates.


The actual candidate has now been staged as seven content addressed parts in
60,615,087 encoded bytes, with exact original hashes verified. The guarded v2
planner accepts these staged references and still reports three blockers:
`calendar_convention_unverified`, `seed_acceptance_missing`, and
`seed_quarantine_unresolved`. Its selection remains 5,447 player rows, 1,698
team rows and 849 supporting games, with 76 short player histories.
This is an import plan, not an imported or accepted seed.

Actual Windows retention registered all four archive roots and seven parts in
Supabase using restricted identities. Its final rehearsal reported failure;
a separate bounded read-only pass verified all four original hashes and
438,321,084 logical bytes from Supabase alone. The failure remains recorded.
No accepted source checks, NBA history facts, rosters, models or forecasts were
created by archive retention. Cloud Actions verification and independent backup
reconstruction are separate checks, reported only when completed.


The actual affected-player analysis found 118 distinct player IDs in quarantine.
Forty have at least ten later valid appearances, 78 have fewer than ten, and 42
have none. These are potential window impacts, not permission to discard records,
truncate histories, or infer participation. Resolving or explicitly bounding that
uncertainty requires a reviewed source/seed decision before production import.


The independent OneDrive readback and isolated restore subsequently passed for
backup `5805b78b-bdd9-424c-9079-0d5422c24bae`: 13 files, 60,794,320 physical
bytes, 12 registered artifacts, 27 tables, and all four original raw files
(438,321,084 logical bytes). Reconstruction used remotely downloaded bytes,
not the provider or laptop archive. Runtime mutation was denied and the temporary
database was removed. The measured restore took 170 seconds with an explicit
600-second budget after the incomplete first readback. This verifies the current
hosted application/raw snapshot; local normalized manifests/inventory and daily
automation are not covered, so the complete launch backup gate remains false.


The owner subsequently approved date-only ordering for the exact pinned seed.
The record in `docs/approvals/2026-10-28-seed-calendar.json` clears only that gate;
it is not seed acceptance. All 135 quarantined rows remain unresolved. The owner
selected the existing `main` branch for the cloud archive check after merging
PR #41, with no expansion of the rehearsal environment's secrets allowlist.
