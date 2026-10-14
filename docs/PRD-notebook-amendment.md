# PRD amendment: executable learning notebooks

Status: LOCKED by the project owner on October 12, 2026. Incorporated into PRD v1.1.

Prepared: October 12, 2026

Amends: PRD version 1.0, especially PLAYER-02, EVAL-02, MODEL-01, and ENG-01. Current requirements: [PRD version 1.1](PRD.md).

The owner requested notebooks for data engineering, exploratory data analysis, and the model training cycle, with clear labels and concise cells. The owner confirmed the workflow choices below and locked this amendment on October 12, 2026. It is retained as the approval record for the requirements incorporated into PRD v1.1.

## NOTEBOOK-01: Execute and understand the real workflow

Jupyter notebooks are the owner's main interactive route for running, inspecting, and understanding data engineering, EDA, training, evaluation, and model lifecycle work. They must execute real operations and display their results, rather than serve only as static reports.

Shared processing logic lives in tested Python modules. Notebooks and scheduled jobs call those same modules, preventing a separate exploratory implementation from drifting away from production behavior. Short exploratory transformations and visualizations may remain in notebooks; reusable production logic belongs in the package.

Use local VS Code notebooks with the same project environment as command-line operations. Select the project kernel explicitly. Notebook execution must not depend on a global Python environment or an unrelated Conda environment.

## NOTEBOOK-02: Planned notebooks

| Notebook | Purpose | Delivery |
| --- | --- | --- |
| 01_sources_and_backfill.ipynb | Verify sources, collect history, inspect schemas, validate records, and inspect persisted data. | Phase 0 |
| 02_baseline_and_ledger.ipynb | Follow schedule and roster selection, historical features, baseline projections, publication, and outcome reconciliation. | Phase 1 |
| 03_eda.ipynb | Explore missingness, minutes, production rates, roles, team trends, and season differences. | After launch |
| 04_training_and_evaluation.ipynb | Construct chronological splits, train, compare baselines, inspect errors, and explain projections. | Models v1 |
| 05_monitoring_and_promotion.ipynb | Inspect accuracy and drift, evaluate challengers, and understand promotion or rejection. | MLOps phase |
| 06_awards.ipynb | Explore award history, eligibility, historical ranking evaluation, and weekly movement. | v1.5 |

Keep the first two notebooks compact so they fit the opening-night critical path. Detailed EDA and trained-model notebooks follow after launch. The design document may refine the notebook organization without removing this coverage.

## NOTEBOOK-03: Cell and output conventions

Use short, clearly labeled cells with one purpose at a time. Each logical section identifies its purpose and inputs, executes a step, inspects its results, and gives a brief interpretation. Explain consequential choices and surprising results without verbose tutorial text or large unfiltered outputs.

Keep concise charts, summary tables, and interpretations in committed notebooks. Keep large datasets and model artifacts outside the notebook, referenced by their recorded versions or checksums. Do not commit credentials or sensitive operational output.

The documented walkthrough must execute in order from a fresh kernel using its declared inputs. Expensive steps reuse explicitly identified artifacts when available. Reuse must verify the relevant input and configuration identity; an unlabeled cached result cannot stand in for a new run.

## NOTEBOOK-04: Execution boundaries

Default to local or rehearsal data. Any production publication must be an explicit, clearly labeled operation, disabled in the normal walkthrough, using the same protected publication path as scheduled jobs. Opening or running the default notebook must not publish official forecasts or promote a production model.

Development training runs locally. Scheduled automated training moves to GitHub Actions only after representative runtime and memory measurements show it fits the available runner and budget. If it does not fit, the design must choose an alternative automated runner or a smaller workload; it must not silently replace the autonomous training requirement with manual notebook runs.

## Acceptance criteria

- A reader can trace raw input to validated data, features, predictions, evaluation, and lifecycle decisions through the notebooks and linked modules.
- The documented walkthrough runs sequentially from a fresh kernel with explicit inputs and the project environment.
- Notebook and command-line executions produce matching results for the same fixed fixture, configuration, and artifact versions, within documented numeric tolerances.
- Default execution uses rehearsal data and cannot create official predictions or change the active production model.
- Production-affecting operations remain protected by the same database and lifecycle controls used by automation.
- Cells have clear labels and concise output; large artifacts are linked by identity rather than embedded.
- Expensive operations identify whether they executed or reused an artifact and why that reuse is valid.
- CI verifies the shared production modules and a lightweight fixture-based notebook execution path. CI does not require live NBA access or a full historical backfill on each pull request.

Approval: the owner explicitly said "lock" on October 12, 2026. Incorporated into PRD v1.1 and recorded in its version history.
