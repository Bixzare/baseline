# ADR 0009: Share tested operations with executable learning notebooks

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD notebook requirements](../PRD.md#notebook-01-execute-and-understand-the-real-workflow), [locked notebook amendment](../PRD-notebook-amendment.md), [design notebook execution](../design.md#13-notebook-execution-and-learning), and [CI strategy](../design.md#15-migrations-ci-and-test-strategy). This record documents approved workflow choices; the project environment and notebooks have not been implemented.

## Context

The owner wants to execute and understand data engineering, EDA, training, and model operations through concise notebooks. Scheduled production work must remain reproducible without a running notebook kernel. Separate notebook implementations would create another version of the pipeline to maintain.

The same project also needs meaningful validation on every PR, including Windows development and Linux job execution, without depending on NBA uptime during CI.

## Decision

- Use Python 3.12 with uv, a dependency lockfile, and an explicitly selected project Jupyter kernel in local VS Code. Verify pinned dependencies and drivers on Windows and Linux before recording working setup commands.
- Put reusable processing and production logic in tested package modules. CLI entry points, notebooks, GitHub Actions, and Windows Task Scheduler use those same operations. Short exploratory transformations and visualizations may stay in notebooks.
- Deliver the six walkthroughs specified in the PRD: sources/backfill and baseline/ledger during Phases 0 and 1; EDA after launch; training/evaluation with models; monitoring/promotion with MLOps; awards in v1.5. Keep the first two compact.
- Give each logical section a short purpose, declared inputs, an execution step, a result inspection, and a concise interpretation. Use clear labels and bounded output so the owner can trace decisions and results.
- Make the documented path execute sequentially from a fresh kernel with explicit configuration and artifact identities. Record the dependency lock hash in run metadata. Avoid hidden state shared between notebooks.
- Keep concise charts, tables, and interpretations in committed notebooks. Reference large data and models through manifests and checksums. Secrets and sensitive operational output cannot enter notebook cells or committed outputs.
- Default to fixtures or rehearsal data. Full backfill and production publication are explicit opt-in operations disabled in the default walkthrough. Run All cannot publish official forecasts or activate a production model. Demonstrate publication in local rehearsal Postgres using the same migrations and permissions.
- Reuse expensive results only after validating their input and configuration identities. Label whether a step executed or reused an artifact and why; stale cached output cannot stand in for a new run.
- Run PR CI with locked installation, Ruff lint/format checks, mypy, pytest unit and leakage tests, real Postgres integration tests, and lightweight fixture notebook execution. Add dashboard lint, type checks, tests, and build when frontend code exists.
- Use Linux CI with a disposable Postgres service matching the project major version, plus a minimal Windows job for imports, paths, and notebook environment compatibility. Do not silently substitute SQLite for database behavior tests.
- Keep live NBA access probes separate from PR CI. Notebook CI cannot call live NBA endpoints or production Supabase, and cannot require full history collection or model training for every PR.
- Keep README and AGENTS.md commands current as entry points are implemented and verified. Each implementation PR links one issue, includes relevant data validation and leakage tests, and explains the data flow, reason, tradeoff, checks, and a failure scenario for owner review.

## Reason and alternatives

Shared operations make the learning walkthrough an inspectable route through the actual pipeline. The fixture path catches hidden kernel state, environment drift, and differences between notebook and CLI results while keeping routine checks small.

Copying production logic into notebooks would create duplicate maintenance and evaluation paths. Static notebooks alone would not meet the owner's request to execute the workflow. Running full backfills or live-source calls on every PR would make correctness checks depend on external access and large workloads. Those alternatives are not selected.

## Consequences

Some exploratory code must move into modules when it becomes reusable production logic. The notebook needs enough explanation to make the shared operation understandable, while its core processing remains in the package.

Fresh-kernel execution and a second operating-system check add CI work, so use small deterministic fixtures. Full source access, resource, backup, and release rehearsals still occur separately. Explicit production operations retain the same ledger and lifecycle protections; notebooks do not provide a shortcut around them.

## Verification required during implementation

- Verify the selected project kernel and locked dependencies on Windows and Linux, documenting the actual working commands.
- Execute each delivered notebook from a fresh kernel on declared fixtures and compare key outputs with the CLI using the same manifests and documented numeric tolerances.
- Test rejection of invalid cache reuse after input/configuration changes, and verify execution versus reuse is visible in outputs.
- Verify the default walkthrough and Run All cannot publish official forecasts or change the active model. Verify the fixture CI path cannot contact live NBA endpoints or production Supabase.
- Exercise actual Postgres constraints and roles, data validation failures, and explicit future-information leakage fixtures in the relevant PR checks.

Approval: the owner explicitly said "lock" on October 12, 2026. No notebook, package environment, or CI pipeline has been executed by this planning record.
