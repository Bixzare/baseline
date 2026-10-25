These seven small JSON files are **synthetic parser fixtures**, authored for SOURCE-001.
They are not observations, do not establish NBA source access or coverage, and must
never count as live capability evidence. Schema references are nba_api 1.11.4
ScoreBoard, BoxScore, LeagueGameLog, CommonTeamRoster, and the candidate NBA
schedule resource documented in nba_api issue 296. IDs, stats, and dates were
chosen to test identity joins, preseason classification, opening-night Eastern
date versus UTC date, fractional minutes, and empty response semantics.

Observed raw bytes belong in the ignored artifact archive with immutable manifests.
No genuine no-game response has been observed merely by testing `no-games.json`.
