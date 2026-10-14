---
name: hoop-ml-lifecycle
description: Implement or review Baseline chronological evaluation, model training, experiment tracking, drift monitoring, retraining requests, champion/challenger decisions, and rollback. Use for model lifecycle work after the launch baseline.
license: MIT; upstream notice in LICENSE.txt
---

# Baseline ML lifecycle

Locked project adaptation of wshobson/agents `ml-pipeline-workflow`, approved October 12, 2026.
Source revision and review notes are in the repository's `skills/README.md`.

## Reproducible stages

Keep validation, features, fitting, evaluation, promotion, and forecasting independently callable and testable.
Record source/feature manifests, observation windows, configuration, code/dependency versions, seed, metrics, and artifact checksum.
Notebooks and CLI operations call the same modules. Start with local training; verify runner resources before enabling scheduled cloud training.
Use the selected batch stack. This skill does not add Airflow, Kubernetes, managed ML hosting, feature stores, or experiment services.

## Evaluation honesty

1. State the target, candidate population, feature availability rules, chronological split, and exclusions before fitting.
2. Fit transformations, tune hyperparameters, and select models without using the final evaluation interval.
3. Compare one and three completed-season training windows as assigned. Era comparisons remain a separate analysis.
4. Freeze the artifact before the evaluation window. The confirmed design uses a recent 30-day holdout and therefore a training-data lag.
5. Evaluate champion and challenger on identical observations; retain difficult rows, missing predictions, and coverage failures.
6. Deploy only the evaluated artifact. Refitting on the holdout creates a different, unvalidated artifact.

For players, train minutes and rates separately. Rate targets cannot divide by zero minutes; final output evaluation includes confirmed DNP zeros.
Initial rate models omit predicted minutes as an input. A later approved change using predicted minutes needs training inputs generated without seeing those rows' outcomes.
Judge rate changes on composed counting-stat forecasts. Judge minutes changes on minutes plus all affected final outputs.
Change one component at a time; if the active bundle changes, re-evaluate against the new bundle.
Team probability uses Brier score with log-loss/calibration guardrails; numeric targets use MAE and their specified guardrails.
Awards require chronological seasons and snapshot cohorts beyond eventual vote recipients, using award-specific eligibility known then.
Each released award requires three complete evaluation seasons after any training, tuning, or benchmark-selection seasons, with frozen checkpoints/formulas, a simple benchmark, NDCG at five, and winner ranks. Missing required candidate or voting evidence blocks that award; weekly snapshots are not independent annual outcomes.

## Promotion decision

- Use versioned policy, including the locked starting gates: 2% relative primary loss reduction, 30-day paired window, 100 distinct games, and 100 observations per required group.
- Blocking groups and secondary metrics must not worsen more than 5%. Player groups use shared baseline minutes: below 10, 10 to below 25, and at least 25.
- Count distinct games once across player rows and targets. Small groups mean insufficient evidence, not a waived gate.
- Handle zero reference losses explicitly. A zero primary champion loss cannot demonstrate the required relative improvement.
- Data integrity, leakage, artifact validity, and required coverage must all pass. Log rejection and insufficient evidence as fully as promotion.
- Player promotion needs full-roster historical evidence or prospective saved cohorts. Participant-only results remain exploratory; shadow training can continue while the baseline remains active.
- Activation must be atomic; retain the previous usable champion on failure. Preserve all historical forecasts.

## Monitoring and training requests

- Report 7-day and 30-day metrics with counts, coverage, baseline comparisons, and data health.
- Separate missingness/source failure, distribution drift, and demonstrated loss degradation.
- Calibrate drift thresholds from historical reference periods. Drift alone requests investigation, not automatic retraining or promotion.
- Weekly training requires validated new data. The confirmed extra trigger is loss above 1.05 times baseline on 100 matched distinct games for three daily checks, with a seven-day cooldown.
- Deduplicate triggers; a scheduled run can satisfy a pending extra request. Invalid data blocks training and promotion.
- Training failure must not stop healthy forecasting. Record the trigger, failures, gates, activation, and rollback with policy and artifact versions.

Return an evaluation report, notebook walkthrough, reproducible artifact manifest, gate tests, and a plain-language reason for the decision.
