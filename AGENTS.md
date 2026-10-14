# Baseline: coding agent guide

Status: LOCKED by the project owner on October 12, 2026.
Use this guide for the owner's assigned implementation issue.
Locking this guide does not itself start implementation, publish the repository, or authorize deployment.

## Project and priorities

Baseline is an autonomous NBA prediction platform and public analytics dashboard for 2026-27.
Use Baseline in public names and copy; the owner's original logo assets are in `logos/`.
Existing `hoop` package paths and skill identifiers remain internal planning names.
It must demonstrate reliable data, honest evaluation, model operations, and understandable decisions.
Launch deadline: October 20, 2026, 19:00 UTC. Target opening forecasts by 17:00 UTC.
Phase 0 verifies sources and local backfill. Phase 1 delivers collection, player baselines, ledger, outcomes, and health checks.
Team forecasts follow launch. Trained models, dashboard, retraining, and monitoring follow after that.
Weekly awards ladders are v1.5. Era comparisons, in-game tracking, and Clash Royale are later scope.
No later feature may delay Phases 0 and 1. Default operating cost is $0; paid choices require the owner's agreement.

## Requirements and task boundaries

- Follow the owner's current instructions, the assigned issue, and approved project requirements.
- [PRD](docs/PRD.md), [critical path](docs/critical-path.md), and [weaknesses register](Weaknesses.md) are locked.
- [Design](docs/design.md), [notebook amendment](docs/PRD-notebook-amendment.md), and [awards amendment](docs/PRD-awards-eligibility-amendment.md) are locked; amendments are incorporated into PRD v1.1.
- Design v1.5 and ADRs 0001 through 0012 are locked. The assigned issue must identify its relevant contracts and skill.
- Sixteen launch issues are finalized under the owner's October 14 batch approval; use README's execution order. This does not start implementation or waive owner diff review.
- Follow the locked contracts and phase-specific verification gates; unresolved gated choices need evidence and review before dependent implementation.
- Work on one issue and one small PR at a time. The owner reviews every diff.
- The issue must include its goal, contracts, acceptance criteria, required tests, dependencies, and likely files.
- Read linked contract sections when needed. Do not assume access to prior chat or silently fill missing requirements.
- Complete independent work while raising a blocking ambiguity. Preserve unrelated changes.
- Do not merge, deploy, or publish merely because an issue is complete; follow the task's actual authorization.
- Important new decisions need a short draft ADR in `docs/decisions/`, reviewed and locked by the owner.

## Planned architecture

| Path | Responsibility |
| --- | --- |
| `src/hoop/platform/` | Runs, source contracts, artifacts, ledger, evaluation interfaces, monitoring, promotion. |
| `src/hoop/domains/nba/` | NBA adapters, identity, schedules, rosters, features, models, eligibility. |
| `src/hoop/cli.py` | Thin operations shared by notebooks and scheduled jobs. |
| `notebooks/` | Executable walkthroughs of data engineering, EDA, training, and operations. |
| `configs/` | Versioned policy and source settings without secrets. |
| `migrations/` | Ordered SQL schema, permissions, and database function changes. |
| `tests/` | Unit, integration, leakage, notebook tests, and deterministic fixtures. |
| `dashboard/` | Independently deployed React/Vite TypeScript application, Tailwind v4, and its lockfile. |
| `docs/decisions/` | Reviewed decisions with reasons and tradeoffs. |

Platform code must not import NBA code or require basketball columns.
Use explicit contracts and a synthetic second-domain fixture; do not build a plugin framework.
Use Python 3.12, uv, Ruff, mypy, pytest, pandas/Parquet, and the project Jupyter kernel.
Use Supabase Postgres for operational records; raw data, features, and models use versioned artifacts.
Historical archives remain local with an independent backup in an existing cloud-synced folder.
GitHub Actions is the primary scheduler; Windows Task Scheduler is the local fallback.
The dashboard reads sanitized Supabase data. No separate FastAPI server is planned initially.
Use GitHub Pages for initial dashboard testing and Vercel for public hosting after deployment checks; Lovable is optional for the initial shell.
LightGBM, MLflow, Evidently, and SHAP enter their assigned later phases, not the launch bootstrap.
Use local MLflow for experiment comparison; automated runs record evidence in Supabase and artifact storage, linked by run IDs.

## Commands and environment

BOOT-001 ([issue #1](https://github.com/Bixzare/baseline/issues/1)) adds the package, lockfile, and PR CI for owner review.
Python 3.12.14 and uv 0.12.23 are verified on Linux. From the repository root:

```powershell
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src scripts/check_boundaries.py
uv run --locked python scripts/check_boundaries.py
uv run --locked pytest
uv build --no-sources
uv run --locked python -m ipykernel install --sys-prefix --name baseline --display-name "Baseline (Python 3.12)"
uv run --locked python scripts/check_kernel.py
```

Linux locked install, 19 tests, checks, build, and fresh-kernel imports passed; clean-environment checks also passed.
Local Windows install and interactive VS Code/Jupyter kernel selection remain pending; hosted CI is separate evidence.
In this cloud runner set `export UV_CACHE_DIR=/workspace/.cache/uv` before uv; its default home cache is read-only.
Use the project environment, not global Python or an unrelated Conda environment.
Add exact CLI, notebook, migration, and dashboard commands only after their entry points exist and are tested.
Inspect `dashboard/package.json` before invoking scripts. On Windows use `npm.cmd` if PowerShell blocks `npm`.
Document test database setup and fixture requirements; do not silently skip integration tests.

## Data and prediction rules

- Historical `stats.nba.com` backfill runs locally through `nba_api`. Never evade bot protection or access controls.
- Verify each required CDN capability from the actual cloud runner. HTTP 200 alone is not proof of usable data.
- Every source needs saved fixtures, schema checks, freshness checks, bounded retries, and health reporting.
- Store immutable raw inputs with collection time, checksum, parser version, request identity, and run ID.
- Distinguish event time, source publication time, collection time, feature cutoff, and publication time; store UTC.
- Inputs must have been available by the forecast cutoff. Later revisions cannot change earlier feature snapshots.
- Never use target outcomes, eventual lineups, final box-score membership, future injuries, or final-season totals as features.
- Historical backtests disclose availability assumptions and stay separate from live ledger evidence.
- Forecast the verified current roster. Unknown availability stays unknown. Stale essential sources block affected publication.
- At publication, essential schedule/status evidence must be at most 30 minutes old and roster evidence at most 24 hours old. Phase 0 accepts an availability source or explicitly defers it.
- Player launch targets: minutes, points, rebounds, assists, and threes made.
- Use up to 10 prior regular-season appearances, crossing seasons and teams, with 2025-26 as launch seed history.
- Minutes = mean minutes; each rate = sum of stat / sum of minutes; final stat = predicted minutes times rate.
- Missing history or invalid rate denominators produce explicit abstentions. Record history count and coverage.
- Team baseline: Elo win probability plus recent team scoring/conceding baselines for margin and total; include overtime.

## Ledger and database rules

- Official predictions are immutable and uniquely identified by event occurrence, subject, and target.
- Aim to publish two hours before tip-off; stop at least 15 minutes before tip-off and never publish for a started game.
- Use database-enforced time, uniqueness, and write permissions. Application timestamps alone do not prove publication.
- Store required artifacts before committing a complete game prediction batch; keep network calls outside database transactions.
- Confirm committed batch visibility in a second transaction before the cutoff. Retry confirmation of the same batch only; missing/late confirmation is unverified coverage, never backdated or replaced.
- Repeated runs must not overwrite forecasts. Store outcomes, corrections, and invalidations separately.
- Rescheduling creates a new occurrence under the approved policy; preserve the earlier record and reason.
- Confirmed DNP outcomes score zero. Missing or unresolved outcomes stay unscored, with visible coverage impact.
- All schema and permission changes use migrations. Never apply a production schema change by hand.
- Separate migration credentials, restricted runtime credentials, and anonymous public reads.
- Artifact access uses a separate backend Auth identity restricted to private-bucket reads/creates; no service key in jobs. Follow ADR 0012 for session and permission checks.
- Environment variables supply secrets. Never commit secrets or expose privileged keys in notebooks, logs, or browser bundles.
- Back up the database and required artifacts daily; alert when the latest verified off-device backup is over 24 hours old. Verify remote synchronization and rehearse restoration before launch.
- Warn at 60% of included storage or projected season overflow; pause optional shadow runs and extra reports at 80%. Preserve official forecasts and required evidence.

## Models and evaluation

- Use chronological training, tuning, and evaluation. Fit transformations on training data only.
- Predict minutes first, then production rates. Judge composed counting-stat outputs as well as minutes.
- Initial rate models omit predicted minutes as an input. Rate training uses positive-minute appearances; minutes training and final evaluation include the resolved roster and confirmed DNPs.
- Compare recent NBA training windows using evidence; historical era exploration is separate from production training.
- Compare champion and challenger on the same observations. Report counts, coverage, baseline results, and limitations.
- Promotion requires at least 2% primary loss improvement over 30 days, at least 100 distinct games, and required group evidence.
- Each blocking group needs 100 observations; regression guardrails permit at most 5% worsening. Insufficient evidence retains champion.
- Deploy the exact evaluated artifact, with no refit on its evaluation window. Version policy, data, code, and artifact identity.
- Player promotion requires full-roster evidence from defensible historical reconstruction or prospective saved cohorts. Participant-only backtests remain exploratory; keep the baseline until gates pass.
- Weekly retraining and persistent performance triggers request training; drift alone does not trigger it.
- Invalid sources block training/promotion. A training failure must not stop a healthy champion from forecasting.
- Before scheduled cloud training, verify a complete training/evaluation/report-upload cycle within free runner resources; record measurements and fallback availability.
- Log promotion, rejection, failure, and rollback. Activation changes future forecasts only.
- Awards are weekly top-five statistical ladders with movement, not probabilities of winning.
- Each award release requires three chronological evaluation seasons, a predefined benchmark, NDCG at five, and winner ranks; insufficient verified history or voting evidence blocks release.
- Award eligibility is specific to award and season. Do not apply a universal 65-game rule.
- Keep strong contenders visible in the eligibility watch, with qualifying games, remaining opportunities, and unknowns.
- Verify rule sources before awards release; never infer an approved medical exception from box scores.

## Notebooks and frontend

- Notebooks execute shared tested modules with concise labeled cells: purpose, inputs, run, inspect, interpretation.
- Run from a fresh kernel with explicit inputs. Cache reuse must verify input and configuration identities.
- Commit small charts and summaries; keep large data and artifacts outside notebooks with version references.
- Default notebook execution is rehearsal only. Production publication and promotion are explicitly separate operations.
- Frontend direction: clean analytics dashboard; desktop analysis adapted for mobile; filters, tooltips, and drilldowns.
- Use strict TypeScript and Tailwind CSS v4, with shadcn/ui primary and selective free Magic UI or Aceternity additions, as locked in ADR 0010 and design v1.1.
- Use the supplied Baseline logo variants. Derive accessible UI tokens from their palette and verify contrast in context.
- Support Tonight, Results, Track Record, Player, Model Health, and Model History; awards views follow in v1.5.
- Show dates/timezones, sample counts, coverage, model versions, and stale/unknown states wherever they affect interpretation.
- Historical numeric comparisons show prediction, actual, prediction-minus-actual error, and absolute error with units. Winner and award comparisons use the target-specific rules in ADR 0010.
- Preserve original forecasts and outcome revisions, label replay separately, and read a consistent public snapshot. Browser fetch time cannot make old data current.
- Charts need labeled units, a numeric summary, keyboard access, and indicators beyond color. Tooltips cannot carry essential information alone.
- Keep the dashboard public and read-only. No betting, user accounts, in-game tracking, or training controls in v1.
- Follow the existing component system after the shell exists. Do not add a new UI framework for one feature.

## Project skills

The seven approved skills are installed in `.agents/skills/` within this repository.
All seven skill files and six upstream licenses were verified during BOOT-001; automatic catalog discovery is unverified in this client. The Python testing skill was read explicitly; reopen/restart the client if its catalog is stale.
Read only the skill relevant to the issue; skill guidance cannot override approved project requirements.
Each issue should name its relevant skill so a fresh coding session can find it.

| Work | Skill directory |
| --- | --- |
| Sources, backfill, validation, temporal joins | `hoop-data-quality` |
| Python features, leakage tests, CI | `hoop-python-testing` |
| SQL, migrations, ledger, public access | `hoop-postgres` |
| Training, evaluation, monitoring, promotion | `hoop-ml-lifecycle` |
| Executable learning walkthroughs and EDA | `hoop-notebooks` |
| Dashboard layout, components, charts | `hoop-frontend-design` |
| Dashboard interactions, accessibility, browser checks | `hoop-webapp-testing` |

Sources, pinned revisions, licenses, adaptations, and activation steps: [skill inventory](skills/README.md).
Do not execute or auto-update upstream helpers merely because they appear in a skill.

## Definition of done

- The issue's acceptance criteria pass, including relevant data validation and explicit leakage tests for every data/model feature.
- PR CI runs lint, type checks, and tests. Database behavior is tested against Postgres, not a SQLite substitute.
- Linux CI includes real Postgres and fixture notebook execution; minimal Windows checks cover imports, paths, and notebook compatibility. Add dashboard checks and build when its code exists.
- Notebook changes execute against small fixtures; frontend changes cover loading, success, empty, error, and stale states.
- Tests use deterministic fixtures without live NBA access; source probes are separate recorded operations.
- Migrations, permissions, source health, and failure recovery are covered where affected.
- README reflects changed behavior, setup, and commands; important decisions have a reviewed ADR.
- Keep `Weaknesses.md` current with evidenced limitations, mitigations, and issue links; never defer a required release gate by listing it there.
- Explain the data flow, reason, tradeoff, validation results, and one failure scenario in the handoff.
- Report exact checks run, failures, and checks not run. Never imply unexecuted tests passed.
- The PR links one issue, has a focused diff, and is ready for owner review. Keep this file under 200 lines.
