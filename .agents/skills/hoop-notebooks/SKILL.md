---
name: hoop-notebooks
description: Create or revise Baseline Jupyter walkthroughs for data engineering, EDA, baseline prediction, training, evaluation, monitoring, promotion, and awards. Use when the owner needs to run a workflow and understand its decisions through concise labeled cells.
---

# Baseline learning notebooks

Original project skill, approved October 12, 2026 from the owner's confirmed notebook requirements.
It is not an upstream catalog download. Requirements are in the locked `docs/PRD-notebook-amendment.md`, incorporated into PRD v1.1, and locked ADR 0009.

## Structure

State the question answered, required input versions, project kernel, expected runtime, and generated artifacts at the top.
Use short sections with clearly labeled cells: purpose, inputs, run, inspect, and interpretation.
Explain one consequential choice or result at a time. Prefer a small table or labeled chart over unfiltered logs.
Show the data flow and the reason for a choice, including one limitation or failure mode where it matters.

| Notebook | Role |
| --- | --- |
| `01_sources_and_backfill.ipynb` | Source verification, raw data, validation, resumable backfill. |
| `02_baseline_and_ledger.ipynb` | Schedule/roster cohort, baseline inputs, rehearsal publication, outcomes. |
| `03_eda.ipynb` | Missingness, minutes/rates, roles, team trends, season comparisons. |
| `04_training_and_evaluation.ipynb` | Temporal splits, fitting, baselines, errors, explanations. |
| `05_monitoring_and_promotion.ipynb` | Accuracy, drift, trigger evidence, promotion/rejection, recovery. |
| `06_awards.ipynb` | Historical labels, candidate coverage, eligibility, ranking, weekly movement. |

The first two walkthroughs stay compact for launch. Do not create empty later notebooks to imply completion.

## Shared execution

- Reusable data and model logic lives in `src/hoop/`; notebooks and automation call the same functions.
- Keep short exploratory transforms and visualizations in the notebook when they are not production logic.
- Execute in order from a fresh project kernel with explicit inputs. No dependence on a previous session's variables.
- Display artifact identity and whether a step ran or reused a cache. Verify source/configuration identity before reuse.
- Keep full datasets, serialized models, and large HTML reports outside the notebook. Reference their paths and checksums.
- Commit concise outputs that help review, with run date and data version; remove credentials and private operational detail.

## Learning and evaluation

Separate training-only EDA that informs feature selection from final holdout evaluation.
Label exploratory all-season charts so they cannot be mistaken for inputs available at a historical cutoff.
Preserve missingness and population exclusions in summaries. Do not plot only successful predictions and hide abstentions.
Explain SHAP as model attribution, not proof of causation. Show a baseline comparison before model complexity.

## Side effects and checks

Default to local/rehearsal data. Run All must not publish official forecasts, promote a model, or perform a full live backfill unexpectedly.
Keep production operations explicit, disabled by default, and routed through the same protected package operations as automation.
Verify fresh-kernel execution on small fixtures and equivalence with the corresponding CLI/package workflow.
Document the full-data run separately; a fixture smoke test is not evidence that a live collection or full training run succeeded.
