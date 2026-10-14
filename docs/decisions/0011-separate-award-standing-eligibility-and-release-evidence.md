# ADR 0011: Separate award standing, eligibility, and release evidence

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD awards requirements](../PRD.md#10-awards-ladders-v15), [locked eligibility and validation amendment](../PRD-awards-eligibility-amendment.md), [design awards contract](../design.md#12-awards-and-eligibility-watch-v15), and [dashboard history](0010-publish-an-independent-dashboard-with-honest-history.md). This record documents approved awards policies; historical source completeness, scoring formulas, and release evidence remain outstanding.

## Context

The owner wants weekly award standings and visibility into leading players who may miss a games requirement. A strong statistical season, a reachable eligibility threshold, and an eventual voter decision answer different questions. Mixing them would conceal contenders or imply confidence the data does not establish.

Awards have few annual outcomes and require historical candidate and voting evidence beyond the initial game-data seed. They are v1.5 and cannot delay Phases 0 and 1.

## Decision

- Produce weekly statistical ladders for MVP, ROY, DPOY, 6MOY, and MIP. Publish up to five provisionally eligible candidates with rank, movement, eligibility status, main statistical drivers, actual snapshot cutoff, and scoring/model version. Missing places remain unfilled. A player absent from the previous top five is a new entrant; do not invent a numerical movement.
- Preserve the full statistical candidate ranking before eligibility filtering. Add an eligibility watch for top-five statistical contenders whose games requirement is at risk or whose standard path is unreachable, including contenders filtered out of the main ladder. Affected main-ladder entries also show risk badges. Statistical rank is not a calibrated winning probability, vote share, or official NBA ranking.
- Version eligibility rules by award and season and reverify applicability before release. Under the rules recorded in the PRD, MVP, DPOY, and MIP use the standard 65-game threshold; ROY and 6MOY do not. Qualifying appearances normally require 20 minutes, with at most two appearances of at least 15 but fewer than 20 minutes counting. Use validated minute precision. Official exception and injury-route determinations require verified evidence, not an inference from statistics.
- Check 6MOY reserve appearances against starts, with strictly more reserve appearances required. Use verified rookie classification for ROY. Missing rookie evidence means unknown eligibility; missing prior-season data for MIP is a scoring limitation rather than an invented official exclusion rule. Preserve rule sources with the versioned rule artifact.
- For threshold T, accumulated qualifying games Q, and verified remaining opportunities R, display games needed as max(0, T minus Q), maximum standard-path total Q plus R, and the required remaining qualification share when R is positive. Q at least T means the games threshold is met. Q plus R below T means the standard path is unreachable, without deciding an official exception. Missing required schedule or minute evidence means unknown; handle R=0 without division by zero.
- Use the latest 10 fully observed regular-season roster opportunities, including missed games, for the conservative pace scenario. Let F count full-minute qualifying appearances in that window; projected additional qualifying games are (F / 10) times R. Show a pace warning only when Q plus that projection is below T while Q plus R is at least T. Before 10 supported observations, show the required share without a pace warning. Include used historical lower-minute allowances in Q, show unused allowances separately, and do not assume their future use. This is descriptive, not an injury forecast or a probability of disqualification.
- Preserve weekly snapshots, input evidence, rule/scoring versions, and the candidate population available at the cutoff. Trades, schedule corrections, later participation, exceptions, and official award outcomes cannot rewrite earlier snapshots. Store verified final results as separate versioned outcomes and compare them with the saved standings.
- Require at least three complete chronological evaluation seasons for each released award. Use only earlier seasons for training, tuning, and benchmark selection. Compare equivalent elapsed-season checkpoints against a predefined simple award-specific benchmark. Report NDCG at five using verified final voting points as relevance, eventual winner rank, per-season results, candidate coverage, and sample limitations. Weekly observations do not count as independent annual outcomes; three seasons is a minimum review policy rather than proof of reliability.
- Never select historical candidates using final vote recipients or construct features from later-season information. Final voting points are evaluation labels. Missing voting evidence is unknown; zero relevance for a nonrecipient requires complete verified results establishing no points. Apply the historical season's eligibility rules, not the newest rules retroactively.
- Before dependent implementation, complete the v1.5 source audit and fix accepted sources, evaluation seasons, checkpoints, candidate/label coverage, benchmark and scoring formulas, voting-point relevance transformation, and tie conventions in versioned configuration. Do not choose formulas using the evaluation seasons. Insufficient evidence keeps the affected ladder unreleased, documented in the awards notebook and Weaknesses.md; it does not block the game platform.

## Reason and alternatives

Separate ranking and eligibility assessments keep strong statistical contenders visible while explaining participation risk. A simple transparent scenario is inspectable without pretending to model future injuries or formal exception decisions.

A chronological benchmark comparison across complete seasons reduces leakage and exposes limited annual evidence. Combining many weekly snapshots into an apparently large independent sample would overstate confidence. An unverified award source or formula cannot become a release assumption.

## Consequences

Awards need more source auditing and historical reconstruction than the game baseline. Different ladders may become releasable at different times. The conservative pace scenario can warn even when unused allowances could help; its assumption must remain visible. Eligibility uncertainty and missing evidence remain explicit product states.

## Verification required during implementation

- Verify season-specific rules and official source provenance, minute boundaries, the two-game allowance, reserve/start ties, rookie uncertainty, and separately sourced exceptions.
- Test threshold equality, early-season provisional status, no remaining games, missing schedule/minute evidence, trades, postponements, and unknown schedule slots.
- Test missed games in the 10-opportunity denominator, fewer than 10 observations, exact pace boundaries, and used versus unused allowances. Statistical ranking and eligibility filtering must reproduce independently.
- Inject later participation, roster changes, exceptions, final vote recipients, and future-season features; verify they cannot alter an earlier candidate population or snapshot.
- Verify release is blocked for fewer than three complete evaluation seasons or missing required candidate/voting evidence. Reproduce frozen benchmark comparisons, relevance/tie conventions, and per-season reports from the recorded inputs.
- Test new entrants, unchanged ranks, missed weekly updates, preserved history, and eventual winners inside/outside the published top five or absent from saved candidate evidence.

Approval: the owner explicitly said "lock" on October 12, 2026. No award source audit, eligibility engine, ladder, or historical validation has been executed by this planning record.
