# ADR 0018: Adjudicate historical rows with explicit source evidence

Status: LOCKED by the owner on October 29, 2026. Implementation is approved; seed acceptance and hosted import remain separate.

## Evidence

The pinned Eoin 525 candidate has 135 quarantined rows in 20 games. Bounded local
nba_api 1.11.4 requests on October 29 retained raw responses with unchanged
released defaults, no retries, and actual receipt times. Explicit InactivePlayers
records match 129 of the 130 identity/label failures, including game and team IDs.
Existing string-field repair overlays can correct those 129 rows without a new
parser policy. The full original raw CSVs remain immutable.

All three ambiguous zero-minute players have positively matched PlayerGameLog
entries for the same player, game and season. A control player explicitly listed
inactive is absent from that day's game log. Missing log entries and zero values
alone are never evidence of nonparticipation. Reported zero minutes remain
reported zero with their precision limitation; no unobserved seconds are invented.

Two extra team records have team/opponent ID 0, blank competition/minutes and
zero scores. Each game already has two valid normalized team sides. Retained NBA
summaries identify the real sides; the zero-ID records cannot be repaired into
additional teams without creating duplicates.

The remaining player record, person 1641712 in game 0022500826 on February 22,
is absent from the retained inactive and traditional-box-score responses. It
remains unresolved, not a DNP. There are 16 later valid played appearances for
that player; the compact seed's latest ten are all strictly after the unknown row.

## Decision

Add explicitly typed, evidence-bound repair operations alongside existing field
repairs. Every operation binds original file hash, original CSV record number,
base-row hash, reason, retained evidence hash, and actual evidence receipt time.
Conflicting operations, missing evidence, changed parent rows or malformed source
identities fail. A new parser version and candidate manifest preserve all previous
versions and use a new availability time no earlier than the repair evidence.

1. A confirmed inactive record may repair identity/competition fields and add a
   neutral nonparticipation annotation. Never invent an injury or medical reason.
2. A positive appearance operation may resolve the three zero-minute records only
   when the retained game-log entry matches player/game/season/date and reported
   statistics. Keep original reported precision and mark zero-minute appearances
   ineligible for per-minute rates. Never use absence to infer DNP or a roster.
3. An invalid-extra-team exclusion is permitted only for the two reviewed zero-ID
   rows, with both valid team sides and final scores corroborated by retained NBA
   evidence. Preserve the excluded rows, hashes and reasons in the manifest.
4. Keep the one orphan player row unresolved. A compact launch seed may be reviewed
   with that row outside its required window only if ten valid appearances are
   strictly later. Validate this condition on every plan and apply; reject ties,
   fewer later appearances or any affected selected history. This does not declare
   the full historical dataset complete or resolve participation in the old game.

Store every repair overlay and source body in cloud evidence before importing
facts. Cloud lineage must resolve independently of laptop files. New parser or
manifest versions do not inherit the prior calendar-only approval automatically.
Rerun date/coverage checks and present the exact new candidate for owner acceptance.
No source acceptance, hosted fact import, model activation or publication follows
from locking this ADR. Full-roster historical evaluation remains unverified.

## Tradeoff and acceptance before use

This adds a small typed adjudication contract instead of weakening unknown/DNP
rules or silently discarding bad rows. The narrowly scoped unresolved record can
remain archived without blocking a compact window that cannot depend on it.
Broader historical use stays blocked until that record is resolved separately.

Owner lock; exact-source matching and stale/corrupt evidence tests; positive versus
missing appearance tests; exclusion uniqueness/score tests; strict window/tie
checks; repair availability leakage tests; cloud lineage/readback and real Postgres
import/resume tests; fresh-kernel walkthrough; final owner review of the candidate.
