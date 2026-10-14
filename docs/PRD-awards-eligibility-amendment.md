# PRD amendment: awards eligibility watch and release validation

Status: LOCKED by the project owner on October 12, 2026. Incorporated into PRD v1.1.

Prepared: October 12, 2026

Amends: AWARD-01, AWARD-02, AWARD-03, and the v1.5 dashboard in PRD version 1.0. Current requirements: [PRD version 1.1](PRD.md).

## Requested behavior

Show when a player is a strong statistical award contender but may miss the award because of the games-played requirement. Statistical standing and eligibility must remain distinct. The feature does not claim to predict how voters will vote.

Keep the main top-five ladder of provisionally eligible candidates. Add an eligibility watch for players in the top five of the statistical ranking before eligibility filtering who are at risk or cannot reach the standard games threshold. Show risk badges on affected main-ladder entries too. An excluded contender must not disappear without explanation.

For each relevant contender, show:

- Award, statistical rank, and snapshot date.
- Qualifying games completed, required threshold, and games still needed.
- Remaining regular-season opportunities based on verified schedule and roster context, with unknown schedule slots identified.
- Whether the standard threshold remains mathematically reachable.
- The share of remaining opportunities that must qualify, when it can be calculated reliably.
- A clearly labeled pace warning, when enough participation history exists to support it.
- A short plain-language explanation and any verified official exception status.

Use award-specific rules already required by AWARD-02. A regular appearance is not necessarily a qualifying appearance. Do not apply the standard 65-game threshold to awards that do not use it. Reaching the threshold establishes only that part of eligibility, not that a player will win.

## Approved pace calculation

The owner approved this calculation and locked the amendment on October 12, 2026.

- Let Q be qualifying games already accumulated, T the award's standard threshold, and R the verified remaining opportunities. The standard path is reachable when Q plus R is at least T.
- Use the latest 10 fully observed regular-season roster opportunities, including missed games. Let F be the number of those opportunities in which the player met the standard full-minute threshold. The projected additional qualifying games are (F / 10) times R.
- Show a pace warning when Q plus that projection is below T while the standard path is still reachable. Before 10 supported opportunities, show the required remaining participation share without a pace warning.
- Include permitted historical lower-minute allowances in Q. Show unused allowances separately and do not assume future use in the projection. Label this conservative assumption.
- Missing required schedule or qualifying-minute evidence produces an unknown assessment. The scenario is descriptive, not a probability of disqualification or an injury forecast.

See [design Section 12.2](design.md#122-transparent-risk-calculations) for boundary cases and snapshot behavior.

## Example display

Illustrative numbers, not a claim about a real player:

> Statistical MVP rank: 2. Games requirement at risk: 50 qualifying games, 18 opportunities remaining. Needs 15 of those 18 to qualify. Recent participation pace would leave the player short of the standard threshold.

If the same player had only 12 opportunities remaining, display:

> Statistical MVP rank: 2. Standard threshold unreachable: the maximum is 62 qualifying games. Official exception status: unknown.

Do not replace that wording with an unconditional claim of ineligibility when an official exception may apply. Unknown schedule coverage or qualifying-minute data produces an unknown assessment, not a calculated exclusion.

## Approved release validation

The owner approved this policy and locked the amendment on October 12, 2026. It strengthens AWARD-03's minimum validation requirement.

- Each released award ladder requires at least three complete chronological evaluation seasons. Use only earlier seasons for any training, tuning, or benchmark selection.
- Compare equivalent points in each season against a predefined simple award-specific benchmark. Report the eventual winner's rank and NDCG at five using verified final voting points, with per-season results and candidate coverage.
- Preserve candidates beyond eventual vote recipients. Final voting results are evaluation labels, never a way to select the earlier candidate population or construct its features.
- If verified candidate history or voting results are insufficient, keep the affected award unreleased and document the limitation. Three seasons is a minimum review policy, not proof of statistical reliability; weekly snapshots do not substitute for additional evaluation seasons.
- Resolve exact sources, evaluation checkpoints, benchmark and scoring formulas, and metric conventions in the v1.5 data audit after launch, before dependent implementation. See [design Section 12.3](design.md#123-awards-modeling-and-release-gate).

## Acceptance criteria

- An otherwise leading statistical candidate remains visible when excluded by the standard games rule.
- Main-ladder eligibility filtering and statistical ranking are independently reproducible.
- Fixtures verify games needed, remaining opportunities, required participation share, and exact reachability boundaries.
- Risk treatment distinguishes early-season incomplete totals from an actual pace warning or an unreachable threshold.
- Missing schedule slots, trades, postponed games, minute qualification, and sourced exceptions are handled explicitly.
- The feature displays no implied probability of winning or probability of receiving an exception.
- Weekly snapshots preserve what was known then. Later games, schedule revisions, and exception decisions cannot alter earlier snapshots.
- Fixtures verify the approved 10-opportunity calculation, including missed games, fewer than 10 observations, exact threshold equality, missing evidence, and used versus unused lower-minute allowances.
- Release evidence covers three complete evaluation seasons per award, frozen benchmarks and metric definitions, and reproducible prior-only snapshots. A fixture verifies that insufficient seasons or missing required candidate/voting evidence blocks release of the affected award.

This addition is v1.5 and does not change the opening-night critical path.

Approval: the owner explicitly said "lock" on October 12, 2026. Incorporated into PRD v1.1 and recorded in its version history.
