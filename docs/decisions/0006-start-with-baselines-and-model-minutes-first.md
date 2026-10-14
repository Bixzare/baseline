# ADR 0006: Start with baselines and model minutes before production rates

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD player requirements](../PRD.md#4-player-projections), [team requirements](../PRD.md#5-team-predictions), and [design Section 9](../design.md#9-features-and-models). This record documents approved model policies; data exploration, training, and validation remain outstanding.

## Context

Baseline must publish useful, auditable player forecasts before opening night without making trained-model development a launch dependency. Player counting stats depend on both playing time and production while on the court. Team outcomes need their own benchmarks and cannot depend on complete player predictions at launch.

Historical appearances are easier to observe than complete historical roster opportunities. Treating every absent box-score row as a DNP would create unsupported training labels. Additional historical seasons also need evidence of relevance to the current production task.

## Decision

- Launch with minutes, points, rebounds, assists, and threes made for the verified roster, or an explicit target abstention. Use up to 10 prior completed regular-season appearances available at the feature cutoff, crossing seasons and teams, seeded from 2025-26. Preserve history count and unknown availability.
- Predict baseline minutes as the mean of those appearances. For each counting stat, divide its sum by the sum of minutes over the same window, then multiply that rate by predicted minutes. With identical complete windows, this equals the mean counting stat; the decomposition claims no additional baseline accuracy.
- Support fewer than 10 appearances with a history flag. Missing history, missing required fields, or an invalid denominator cannot become an invented zero prediction. Confirmed DNP outcomes still count as zero in all-roster evaluation.
- Introduce team baselines after the player launch: Elo for home-win probability, plus recent scoring and conceding averages for margin and total. Both use only earlier available final results and include overtime in the target outcomes.
- Fix the initial Elo policy: initialize at 1500 before the 2025-26 seed season, K=20, home advantage of 65 rating points, base-10 logistic scale 400, and retain 75% of each rating's deviation from 1500 at season boundaries. These are versioned benchmark settings, not tuned claims. A probability of 0.5 displays no preferred winner.
- Use each team's last 10 completed regular-season games for scoring. Expected home points average home-team recent points scored and away-team recent points allowed; reverse the pairing for away points. Margin is home minus away, and total is their sum. Flag shorter histories and abstain if either team has no usable history. Do not force agreement between Elo and the scoring benchmark's preferred side.
- After launch, use a dedicated LightGBM minutes candidate and separate rate candidates, with simple baseline and linear comparisons in development. Train minutes on defensible roster opportunities, including confirmed DNPs. Fit rates only on positive-minute appearances, weighted by exposure minutes; initially omit predicted minutes as a rate-model feature.
- Evaluate composed minutes-times-rate counting stats, alongside minutes. Team candidates predict win probability, margin, and total separately. Any probability calibration is fitted on earlier development data only.
- Initially collect three completed seasons for player/team model development and compare one-season versus three-season windows chronologically. Choose the production window from evidence; historical era comparisons remain a separate later module.
- Keep features small and justified by EDA. Target-game outcomes, eventual starters, future roster changes, and later source revisions cannot enter earlier feature snapshots. Optional player aggregates used by a team model need their own prior-only provenance.
- If historical roster/DNP reconstruction is insufficient, keep the baseline official and collect prospective roster and outcome evidence. Defensible candidate training and shadow forecasts may continue, but promotion waits for the full cohort and evaluation gates. Never manufacture historical absences from a player-by-game cross product.
- Version the training manifest, cutoff, feature order/types, preprocessing, imputation, target definitions, random seeds, dependency lock, and compatibility checks. Apply the recorded zero floor to nonnegative targets, preserving valid negative margins; reject malformed or nonfinite outputs. Do not cap minutes at 48 because the targets include overtime.

## Reason and alternatives

Baselines establish the data, publication, and evaluation path early and provide a continuing comparison. Separating minutes from rates makes changes in playing time and productivity inspectable. Initially omitting predicted minutes from rate features avoids another training dependency.

Training complex models before reliable collection would put model work ahead of the launch gates. Participant-only evaluation would omit missed-game errors. Training across every historical era without comparison would add volume without establishing usefulness. Those alternatives are not selected.

## Consequences

The appearance-based baseline can overpredict a likely nonparticipant, reacts slowly to changing roles, and abstains for players without usable history. Multiplying separate minutes and rate estimates is an approximation; dependence between the two can affect final errors. Independent team components can produce differing winner implications. These limitations must appear in evaluation and [Weaknesses.md](../../Weaknesses.md).

Historical evidence may be insufficient for immediate model promotion. The baseline remains valid as the official champion while prospective evidence accumulates. Prediction intervals are deferred until coverage is evaluated, and explanations describe model contributions without claiming causality.

## Verification required during implementation

- Verify baseline outputs, one/fewer/exactly 10 appearances, excess history, trades, season rollover, zero-minute denominators, unknown fields, abstentions, and future-game exclusion.
- Test Elo update availability order, home/away signs, season regression, the 0.5 convention, scoring formulas, shorter histories, and overtime. Preserve independent benchmark identities.
- Test the difference between resolved roster opportunities and appearances, confirmed DNP evaluation, positive-minute rate fitting, exposure weights, and composed outputs.
- Exercise leakage fixtures for target starters, post-cutoff roster/source revisions, future results, and player-derived team inputs. Compare training windows with identical chronological folds.
- Reproduce model inputs and outputs from versioned manifests; verify valid negative margins, nonnegative target floors, overtime minutes, and rejection of incompatible or nonfinite results.

Approval: the owner explicitly said "lock" on October 12, 2026. No baseline implementation, trained model, performance comparison, or production-window selection has been completed by this record.
