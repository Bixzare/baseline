# Historical dataset comparison for Baseline

Status: Assessment performed October 24, 2026. The owner authorized incorporating its repair strategy on October 25; source/seed acceptance remains pending.
This report does not adopt a new source, amend locked requirements, or start DATA-001.

## Recommendation

Prefer Eoin Moore version 525 as the historical seed candidate. Its downloaded
player, team, game, and identity files support the five player targets and team
outcomes. Adopt only after the remaining coverage, normalization, provenance,
and permitted-use checks pass and the source decision is reviewed.

Do not choose Wyatt Walsh version 238 as the sole historical source for this MVP.
The actual published files differ materially from the current warehouse
description. My earlier statement that either dataset could do the job was based
on descriptions and was too broad. This report supersedes that assessment.

## Versions and evidence

Both datasets were queried through the official Kaggle client using kagglehub
1.0.3 in an isolated tool environment. Project dependencies were unchanged.
The earlier direct metadata GET requests returned HTTP 404; the official client
successfully retrieved metadata, inventory, and selected version-pinned files.
These 404 results therefore do not establish that the datasets are unavailable.

| Property | Eoin Moore | Wyatt Walsh |
| --- | --- | --- |
| Dataset | [NBA box scores and statistics](https://www.kaggle.com/datasets/eoinamoore/historical-nba-data-and-player-box-scores) | [NBA Database](https://www.kaggle.com/datasets/wyattowalsh/basketball) |
| Version inspected | 525 | 238 |
| Metadata last updated | October 24, 2026 | June 29, 2026 |
| Listed total file bytes | 1,866,983,047 | 4,660,601,876 |
| Latest date in downloaded game file | October 23, 2026 | June 12, 2023 |
| Publisher dataset license label | CC0: Public Domain | CC BY-SA 4.0 |
| Downloaded files | Games.csv, TeamStatistics.csv, PlayerStatistics.csv, Players.csv | game.csv, inactive_players.csv, dataset-metadata.json, run_summary.json, nba.duckdb |
| Additional inspection | Full scan of those CSVs, with detailed recent-season and saved NBA comparisons | SQLite schema inspected with bounded HTTP range reads; full SQLite contents not downloaded or audited |

Listed bytes are file inventory sizes, not measured compressed archive sizes.
Publisher labels are recorded facts, not independent confirmation of every
underlying data right. Repository software licenses do not replace dataset terms.

Raw evidence, download hashes, audit outputs, and SQLite schema pages are local
under `artifacts/dataset-comparison/8be6ca7339144953bdd1e7422e423c22/`.
This directory is ignored by Git. Exact files: `content-audit.json`,
`eoin-seed-gaps.json`, `wyatt-sqlite-schema.json`, and each publisher's
`official-client.json` and `downloads.json` files.

## Fit against project requirements

| Requirement | Eoin version 525 | Wyatt version 238 |
| --- | --- | --- |
| 2025-26 player baseline history | Suitable candidate with identified cleanup | Not demonstrated; game CSV lacks that season and SQLite has no direct player game-stat table |
| Minutes, points, rebounds, assists, threes | All five present in PlayerStatistics.csv | No equivalent player game-stat table in the inspected release |
| Historical team wins, scores, margin, total | Supported by game and team CSVs | Supported for older seasons by game.csv; not a recent seed |
| Stable identity joins | Numeric IDs available; canonical formatting and invalid IDs require validation | IDs present in older game/identity tables; modern player-game joins unavailable in this release |
| Later trained models using recent seasons | Promising; earlier-season gaps require repair | Published recent-season coverage is insufficient |
| Later advanced analytics | Extended player/team files and play-by-play listed, not content-audited | Current project documents broad warehouse coverage, but downloaded release does not establish it |
| Historical awards validation | Requires separate award/voting/rule evidence | Requires separate evidence; current package cannot be assumed to supply the documented warehouse |
| Fresh operational schedules/rosters/results | Some current records and schedule file listed; operational freshness/reliability remain unverified | Not established |
| Historical pregame rosters/injuries | Not established by final box scores or comments | Inactive-player records do not establish pregame publication timing |

The [Eoin pipeline](https://github.com/eoinmooremath/nba-data-pipeline) and
[Wyatt warehouse](https://github.com/wyattowalsh/nbadb) document collection and
intended outputs. Those descriptions are useful context, but the downloaded
release is the acceptance evidence. Baseline will consume data files rather
than execute either publisher's collection pipeline.

## Eoin: observed strengths and gaps

The full basic player CSV contains 1,673,641 rows across competitions. Detailed
2025-26 checks use canonical game IDs beginning `00225`; season classification
must also be validated against accepted competition metadata before import.

- Observed 1,230 game records, 2,462 team rows, and 32,309 player rows covering
  597 player IDs. Player rows include nonparticipants; these are not 32,309
  appearances. There were no duplicate game, game/team, or game/player keys.
- Two team rows use team ID `0` and score `0`. Quarantine these invalid rows.
  The remaining 2,460 team rows reconcile exactly with player point sums.
- All game IDs in this season's game file have player and team records. This is
  internal consistency, not proof against an independent expected-game inventory.
- 130 player rows have no player-team ID and cannot join to a team record.
  None has positive recorded minutes or nonzero values for the four target
  counting statistics. Preserve/quarantine these rows rather than guessing teams.
- 5,530 player rows lack minutes. Of these, 5,528 have nonparticipation comments;
  two have no comment. Interpret supported nonparticipation evidence explicitly.
  Missing minutes alone must never be converted to a confirmed DNP or zero.
- All four target counting-stat columns in this season pass the scan for missing,
  negative, and noninteger values. Every observed player ID joins to Players.csv.
- Recent minutes retain fractions. Older 2022-23 and 2023-24 records in this file
  have whole-minute precision, so a cross-season model must document precision.
- The player file includes outcome-time fields such as comments, starters, win,
  and home. Eventual starters and nonparticipation comments cannot be used as
  pregame features. Neither can final-season aggregates or target-game statistics.
- Game IDs are stored without their leading zeros in these CSVs. Restore and
  validate canonical ten-digit game IDs; never join on player/team names alone.
- Date fields do not carry an explicit UTC offset. Verify timezone semantics
  and daylight-saving conversion rather than invent UTC timestamps.

The scan also found 1,226 `00224` game records for 2024-25, two game records with
no player rows, and additional identity/reconciliation problems. That season
cannot be called complete without inventory reconciliation and repair.
For 2023-24, 66 `00223` games are labeled NBA Emirates Cup rather than Regular
Season. Filtering only the display label would incorrectly lose those records.

### Comparison with saved nba_api evidence

No additional NBA endpoint requests were made. The comparison used the saved
April 10-12, 2026 stock-client responses from the October 15 diagnostic.

| Check | Result |
| --- | --- |
| Player identity matches | All 636 sample rows matched |
| Player points, rebounds, assists, threes | Exact agreement for all 636 matched rows |
| Player minutes | 617 values differ; maximum absolute difference 0.7 minutes |
| Team identity matches | All 60 sample rows matched |
| Team minutes, scores, rebounds, assists, threes | Exact agreement for all 60 rows |

The saved LeagueGameLog player minutes are integers while the dataset retains
fractions. Precision explains a plausible part of the difference, but this
comparison does not establish that every differing value is merely rounding or
that either response is exact ground truth. Keep source precision and revisions
visible. The sampled agreement does not establish every season's correctness.

## Wyatt: description versus published files

The current repository describes a broad warehouse with player facts, derived
tables, and multiple formats. Version 238's actual SQLite schema instead contains
16 tables: game, game_summary, other_stats, officials, inactive_players,
game_info, line_score, play_by_play, player, team, common_player_info,
team_details, team_history, draft_combine_stats, draft_history, team_info_common.

There is no direct player game-stat table covering the five Baseline targets.
Player identity, inactive-player, and play-by-play records are not substitutes.
Deriving historical player box scores from play-by-play would add major work
and verification risk, so it is not recommended for the MVP.

Other observed limitations:

- `game.csv` contains 65,698 rows through June 12, 2023 and no 2023-24,
  2024-25, 2025-26, or 2026-27 regular-season rows. It has 56 repeated game IDs;
  these need examination rather than blind deduplication.
- The 12,288-byte `nba.duckdb` opens read-only but contains no tables.
- `run_summary.json` reports zero succeeded extractions and zero extracted rows.
  That does not date every table, but it cannot substantiate a fresh full rebuild.
- The SQLite schema was read through its complete schema btree using a 1 MiB
  prefix and three additional 4 KiB pages. No full SQLite table-row, date,
  completeness, or integrity audit is claimed.

The schema reader matched standard sqlite3 results on a separate generated
81-table/view fixture. All 16 recovered table definitions parse in SQLite.
The observed mismatch may reflect an incomplete migration/publication; its cause
has not been established. Reassess Wyatt only after a new release demonstrates
the required populated recent-season player and team tables.

## Next execution gate

Use the inspected Eoin version as the preferred candidate, keep nba_api for
bounded comparison or identified repairs, and avoid integrating both datasets.
The roughly 438 MB basic subset is sufficient for the current historical audit;
full play-by-play and extended files add no launch requirement.

Before source acceptance, reconcile expected game IDs independently, define
quarantine and DNP handling, validate minute/time/identity mappings, and review
the source-use decision. Then amend the existing source/backfill contracts in a
short reviewed decision and continue DATA-001. This report is not that approval.

The supplied kagglehub snippets request the latest full bundles. For reproducible
collection, pin accepted versions and request only needed files. These behaviors
are documented by [Kaggle](https://github.com/Kaggle/kagglehub#download-dataset).
Downloaded files need manifests and backups; the returned local path is not a
validation or completeness certificate.

Today is October 24, so the original October 20 opening-night deadline is past.
Historical records can seed forecasts and labeled backtests. They cannot create
opening-night live prediction evidence. Start the official ledger only for
future games after publication gates pass; rebaseline the delivery date with
the owner without weakening those gates.
