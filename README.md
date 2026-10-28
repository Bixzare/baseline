# Baseline

NBA season prediction platform and public ML analytics dashboard for 2026-27.

Status: implementation now covers source validation, seed planning, player baselines, protected ledger publication, outcomes, evaluation and batch operations. The dedicated Supabase Free project is healthy on Postgres 17.11, and reviewed migrations through 0010 are applied. Windows restricted runtime TLS, backend sign-in/refresh and private Storage create/read now pass. ADR 0016 verifies the concealed Storage mutations on Windows and Actions. Accepted recurring sources, seed acceptance, full historical backup coverage, daily backup execution and Windows notification delivery remain release gates. Production is disabled. See [execution status](docs/execution-status.md) and [hosted setup evidence](docs/supabase-setup-status.md).

## Brand

The product name is **Baseline**, confirmed by the owner on October 12, 2026. Supplied brand assets:

- [Full logo](logos/baseline-logo.svg) and [reversed logo](logos/baseline-logo-reversed.svg).
- [Compact mark](logos/baseline-mark.svg) and [reversed mark](logos/baseline-mark-reversed.svg).

The SVGs use navy `#0B2D6E`, orange `#FF7A1A`, and cream `#F5F1E8`. These are brand colors, not a complete accessible UI palette. Dashboard work must verify text and chart contrast in context.

Existing `hoop` package paths and skill identifiers are internal planning names; public names and copy use Baseline.

## Delivery

Phases 0 and 1 prioritize verified data collection, local historical backfill, five player baseline targets, an immutable prediction ledger, outcomes, and source health before October 20, 2026 at 19:00 UTC.

Team forecasts follow launch. Trained models, automated evaluation/retraining/promotion, and the public dashboard follow after that. Weekly awards ladders are v1.5; in-game tracking and era comparisons are later work.

Student Developer Pack benefits are optional and add no launch dependency. Any adopted benefit must have a recorded expiry, renewal cost, and replacement path; candidates are documented in the technical design.

Approved dashboard hosting plan: GitHub Pages for initial testing, then Vercel for the public dashboard subject to deployment checks. Lovable is optional for generating the initial UI shell. The reviewed frontend remains in this repository; no paid plan or deployment has been authorized by this planning decision.

## Planning documents

| Document | Status |
| --- | --- |
| [Original proposal](Initial-project-description.md) | Original scope; later confirmed decisions take precedence. |
| [Critical path](docs/critical-path.md) | Locked v1.1; revised conditional October 14-20 calendar and explicit deadline risk. |
| [PRD](docs/PRD.md) | Locked v1.1; incorporates both approved amendments. |
| [Technical design](docs/design.md) | Locked v1.5; incorporates approved architecture refinements and the batch-approved launch operating policies. Runtime verification gates remain. |
| [Notebook amendment](docs/PRD-notebook-amendment.md) | Locked; incorporated into PRD v1.1. |
| [Awards eligibility and validation amendment](docs/PRD-awards-eligibility-amendment.md) | Locked; incorporated into PRD v1.1. |
| [ADR 0001: NBA source verification](docs/decisions/0001-verify-nba-sources-by-environment.md) | Locked. |
| [ADR 0002: Platform and domain boundary](docs/decisions/0002-separate-platform-and-domain-code.md) | Locked. |
| [ADR 0003: Storage, migrations, and recovery](docs/decisions/0003-store-operational-records-and-versioned-artifacts.md) | Locked. |
| [ADR 0004: Immutable pregame publication](docs/decisions/0004-enforce-immutable-pregame-publication.md) | Locked. |
| [ADR 0005: Scheduling and local recovery](docs/decisions/0005-schedule-batch-jobs-with-local-recovery.md) | Locked. |
| [ADR 0006: Baselines and minutes-first models](docs/decisions/0006-start-with-baselines-and-model-minutes-first.md) | Locked. |
| [ADR 0007: Evaluation and artifact promotion](docs/decisions/0007-promote-only-chronologically-evaluated-artifacts.md) | Locked. |
| [ADR 0008: Monitoring, retraining, and tracking](docs/decisions/0008-monitor-evidence-and-request-bounded-retraining.md) | Locked. |
| [ADR 0009: Notebooks and shared checks](docs/decisions/0009-share-tested-operations-with-learning-notebooks.md) | Locked. |
| [ADR 0010: Dashboard and prediction history](docs/decisions/0010-publish-an-independent-dashboard-with-honest-history.md) | Locked. |
| [ADR 0011: Awards eligibility and validation](docs/decisions/0011-separate-award-standing-eligibility-and-release-evidence.md) | Locked. |
| [ADR 0012: Restricted artifact storage identity](docs/decisions/0012-restrict-runtime-artifact-storage-access.md) | Locked; authentication and hosted permissions remain execution gates. |
| [Coding agent guide](AGENTS.md) | Locked; 199 lines. |
| [Project skills and provenance](skills/README.md) | Locked; seven skills installed in `.agents/skills/` and discovered in this session on October 13. |
| [Known weaknesses and improvements](Weaknesses.md) | Locked v1.0; living register maintained through owner review. |
| [BOOT-001: Repository and PR checks](docs/issues/BOOT-001-repository-python-and-pr-ci.md) | [Issue #1](https://github.com/Bixzare/baseline/issues/1), merged [PR #2](https://github.com/Bixzare/baseline/pull/2). Local Windows install and automated checks verified October 15; interactive kernel selection remains pending. |
| [SOURCE-001: NBA source capability verification](docs/issues/SOURCE-001-verify-nba-capabilities-by-environment.md) | [Issue #3](https://github.com/Bixzare/baseline/issues/3); probes and failure evidence prepared for review. Local sources and capability acceptance remain gates. |
| [DATA-001: Local backfill and first notebook](docs/issues/DATA-001-local-seed-backfill-and-source-notebook.md) | Locked specification; requires accepted local historical source evidence during execution. |
| [DB-001: Migrations, roles, and connectivity](docs/issues/DB-001-migrations-roles-and-supabase-connectivity.md) | Locked specification; dedicated Supabase Free project setup remains an execution gate. |
| [DB-002: Private artifacts and source evidence](docs/issues/DB-002-private-artifacts-and-source-evidence.md) | Locked specification; hosted storage enforcement and evidence persistence remain execution gates. |
| [DB-003: History contracts and seed import](docs/issues/DB-003-history-contracts-and-seed-import.md) | Locked specification; seed acceptance, import, and cloud reference resolution remain execution gates. |
| [MODEL-001: Player baseline and feature snapshots](docs/issues/MODEL-001-player-baseline-and-feature-snapshots.md) | Locked specification; preparation, snapshot reproduction, and real-input rehearsal remain execution gates. |
| [LEDGER-001: Schema, permissions, and baseline registration](docs/issues/LEDGER-001-schema-permissions-and-baseline-registration.md) | Locked specification; migrations, baseline registration, and protected publication remain execution gates. |
| [LEDGER-002: Protected publication and commit confirmation](docs/issues/LEDGER-002-protected-publication-and-commit-confirmation.md) | Locked under batch approval; protected operations and receipts remain execution gates. |
| [COLLECT-001: Schedule/status/roster collection](docs/issues/COLLECT-001-schedule-status-rosters-and-occurrences.md) | Locked under batch approval; actual source routing/occurrence handling remain execution gates. |
| [OUTCOME-001: Final results and reconciliation](docs/issues/OUTCOME-001-final-results-and-versioned-reconciliation.md) | Locked under batch approval; trusted finals/DNP and revisions remain execution gates. |
| [EVAL-001: Errors and honest coverage](docs/issues/EVAL-001-live-errors-and-honest-coverage.md) | Locked under batch approval; report arithmetic/populations and persistence remain execution gates. |
| [OPS-001: Cloud nightly/dispatcher](docs/issues/OPS-001-cloud-nightly-and-dispatcher-jobs.md) | Locked under batch approval; actual workflow evidence and gated activation remain execution gates. |
| [OPS-002: Local recovery and health](docs/issues/OPS-002-local-watchdog-fallback-and-health-alerts.md) | Locked under batch approval; independent task/notification/recovery evidence remains an execution gate. |
| [BACKUP-001: Independent backup and restore](docs/issues/BACKUP-001-independent-backup-and-restore-drill.md) | Locked under batch approval; provider setup, remote verification, and isolated restore remain execution gates. |
| [LAUNCH-001: Integrated rehearsal and opening night](docs/issues/LAUNCH-001-integrated-rehearsal-and-opening-night.md) | Locked under batch approval; readiness and first official publication are not yet verified. |

All twelve ADRs, the agent guide, seven skills, and sixteen launch issue specifications are finalized. On October 14 the owner authorized batch locking of the remaining launch backlog. The coding agent still executes one assigned issue and one small PR at a time, with owner review of every diff. This approval does not claim implementation or deploy anything.

## Execution order and handoff

The owner confirmed launch-first planning on October 14, then approved finalizing its remaining issues without individual lock pauses. This changes planning order, not approved scope. Later model/MLOps/dashboard/awards issues are detailed before their implementation. All sixteen launch tasks are published as GitHub issues; see the [execution status and issue map](docs/execution-status.md). Current issue and board states are recorded in that execution status map; implementation, owner review and hosted readiness remain separate. When publishing, convert document links to actual repository URLs and map dependencies to real issue numbers without changing approved contracts.

| Order | Planning ID | Required implemented dependencies / gate |
| --- | --- | --- |
| 1 | [BOOT-001](https://github.com/Bixzare/baseline/issues/1) | No code prerequisite; verify owner-owned public repository destination and environment. |
| 2 | [SOURCE-001](https://github.com/Bixzare/baseline/issues/3) | BOOT-001; actual source capability/routing acceptance. |
| 3 | [DATA-001](https://github.com/Bixzare/baseline/issues/5) | BOOT-001, accepted SOURCE-001 historical adapter; report full-seed acceptance/gaps. |
| 4 | [DB-001](https://github.com/Bixzare/baseline/issues/6) | BOOT-001; dedicated Free project, actual connection/role/allowance verification. |
| 5 | [DB-002](https://github.com/Bixzare/baseline/issues/7) | DB-001, SOURCE-001; restricted private artifact authentication and evidence contracts. |
| 6 | [DB-003](https://github.com/Bixzare/baseline/issues/8) | DATA-001, DB-002; accepted seed and verified artifact references. |
| 7 | [MODEL-001](https://github.com/Bixzare/baseline/issues/9) | DB-003; fixture preparation may precede real fresh-input rehearsal. |
| 8 | [LEDGER-001](https://github.com/Bixzare/baseline/issues/10) | DB-003, MODEL-001; actual baseline descriptor for registration. |
| 9 | [LEDGER-002](https://github.com/Bixzare/baseline/issues/11) | LEDGER-001, MODEL-001; protected publication/receipt protocol. |
| 10 | [COLLECT-001](https://github.com/Bixzare/baseline/issues/12) | SOURCE-001, DB-003, LEDGER-002; actual fresh capability routing. |
| 11 | [OUTCOME-001](https://github.com/Bixzare/baseline/issues/13) | COLLECT-001, LEDGER-002, DB-003; accepted final-result adapter. |
| 12 | [EVAL-001](https://github.com/Bixzare/baseline/issues/14) | OUTCOME-001, COLLECT-001, LEDGER-002. |
| 13 | [OPS-001](https://github.com/Bixzare/baseline/issues/15) | COLLECT-001, OUTCOME-001, EVAL-001, LEDGER-002; production enable remains off. |
| 14 | [OPS-002](https://github.com/Bixzare/baseline/issues/16) | OPS-001 and shared source/ledger/report operations; actual Windows/notification checks. |
| 15 | [BACKUP-001](https://github.com/Bixzare/baseline/issues/17) | DB-001/002, LEDGER-002, OUTCOME-001, EVAL-001, OPS-002; provider/isolated target setup. |
| 16 | [LAUNCH-001](https://github.com/Bixzare/baseline/issues/18) | Every prior issue implemented/reviewed and required runtime gates verified. |

Dependencies mean implemented, tested, owner-reviewed interfaces, not that every later launch gate has already passed. An implementation PR may report a blocked real-input rehearsal honestly while delivering fixture-tested operations, if its issue allows that. COLLECT-001 then supplies fresh recurring inputs; LAUNCH-001 requires actual readiness before activation. OPS-002 can test/alert on an unverified backup before BACKUP-001 produces real evidence, so those tasks have no circular prerequisite.

The revised [critical path](docs/critical-path.md#updated-execution-plan-october-14-20) estimates about 44-51 agent hours plus review/setup/drills, conditional on rapid source/database verification. The original 28-hour calendar is not a reliable guarantee. At source/database checkpoints, reassess real duration and deadline risk. No optional later module or document may delay launch.

### Current execution assignment

BOOT-001 was owner-reviewed and merged in [PR #2](https://github.com/Bixzare/baseline/pull/2). On October 25 the owner authorized incorporating the [historical-data strategy](docs/PRD-data-source-amendment.md) and resuming sequential issue execution. SOURCE-001 is merged in PR #4. The next batch has review PRs #19 (DATA-001), #20 (DB-001), and #21 (DB-002), stacked in that order with shared dependency changes resolved. All 236 combined tests passed locally. The candidate seed remains incomplete and the dedicated Supabase project is not created. These three tasks remain In progress; eleven later tasks remain Backlog. No merge or deployment is authorized by resuming execution.

Prefer pinned Eoin version 525 basic files with quarantine, exact coverage cross-checks, and versioned targeted repairs. Retain prospective roster/outcome evidence; defer injury ingestion, historical injury reconstruction, and all-time comparisons. The [dataset comparison](docs/dataset-comparison.md) records observed gaps. ADR 0013 is a draft decision record for owner review. The original October 20 date is past; activate only for future games after readiness.

### Setup inputs and stop conditions

- Verify account ownership/name availability for `Bixzare/baseline`, Python 3.12/uv setup, and project skill discovery in the fresh session.
- SOURCE-001 supplies actual adapter/rate/coverage evidence and an explicit availability acceptance/deferral decision. No spoofing or undocumented source substitution.
- DB-001 supplies a dedicated Supabase Free project if an account slot exists, actual version/region/allowances, safe roles/TLS, and supported export connection. Credentials are configured through environments, never shared in chat or committed.
- BACKUP-001 setup supplies the existing cloud-sync provider/folder, a proven unattended remote verification route, and a safe isolated restore target. Until verified, backup status stays unverified.
- OPS-002 setup verifies Windows principal/session, actual notification delivery, local-only source duties, and awake/connected availability for opening day.
- Any missing required source, unsafe permission/restore route, unpaid-plan capacity issue, or failed pregame timing/coverage gate blocks readiness. Escalate the exact decision; do not fabricate results, loosen protections, buy resources, or mark the gate complete from this document.

## Agent guidance

`AGENTS.md` summarizes scope, architecture, invariants, conventions, skills, and the definition of done. The seven skills cover data quality, Python testing, Postgres, ML lifecycle, notebooks, frontend design, and browser testing.

The frontend direction is a clean analytics dashboard with filters, tooltips, and drilldowns, designed for desktop analysis and adapted for mobile. Learning walkthroughs use concise labeled notebook cells and shared tested package logic.

The owner confirmed TypeScript, Tailwind CSS v4, and shadcn/ui for core components, with selective free Magic UI or Aceternity additions for polish. Locked ADR 0010 records these choices, incorporated into technical design v1.1.

## Setup

Use Python **3.12.14** and uv **0.12.23**. `.python-version` pins the interpreter; `pyproject.toml` pins the bootstrap tools and nba_api **1.11.4**, and `uv.lock` records the full resolution and artifact hashes, including Windows dependencies. The installed distribution is `baseline-hoop`; imports remain `hoop`. nba_api brings requests, pandas, and NumPy for its supported interfaces. Database and model tools enter with their assigned features.

From the repository root, Linux commands verified on October 14, 2026:

```bash
# In this cloud environment, the default home cache is read-only.
export UV_CACHE_DIR=/workspace/.cache/uv
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

Bootstrap installation was verified in `.venv` and a second clean environment. The SOURCE-001 suite now has 153 passing offline tests, including five cutoff/leakage tests, command-level boundary regression coverage, 15 local notebook checks, and ten native client checks. The notebook executes in a fresh kernel with external network access blocked. No tests are skipped. The build produced an sdist and wheel. The kernel check launches a fresh registered `baseline` kernel, verifies its interpreter matches the active project environment, and imports the package and both subpackages from the expected checkout path. It does not claim interactive VS Code kernel selection has been verified.

In local VS Code, select the repository's `.venv` interpreter as the notebook kernel explicitly. The registration above writes into the project environment instead of global/user Jupyter settings; rerun it after recreating or moving the environment. On Windows, install the pinned Python/uv versions, run `uv sync --locked` from the repository root, and use the same `uv run` check and kernel commands in PowerShell. The Linux `export` line is specific to this cloud runner; a normal local Windows cache does not need that override. Local Windows locked installation, the 106 existing tests, lint, formatting, types, boundaries, and fresh-kernel imports passed on October 15. Interactive VS Code kernel selection remains unverified. Hosted Windows CI is separate evidence.

### Local environment and history access notebook

DATA-001 adds the [local seed workflow](docs/seed-backfill.md) and
`notebooks/01_sources_and_backfill.ipynb`, which defaults to offline fixtures.
Run `uv run --locked python -m hoop.cli seed --help` for the shared CLI.
The real 2025-26 run matched 1,230 game IDs against a separate local NBA inventory,
retained 32,176 player and 2,460 team rows, and quarantined 135 records. It remains
incomplete and unaccepted. Repair support does not automatically repair or accept
those records. Backup and production collection remain separate gates.

The [October 25 amendment](docs/PRD-data-source-amendment.md) resumes SOURCE-001 with a pinned-file assessment and repair report. The shared assessor also runs in `test.ipynb` on synthetic fixtures. A real assessment records unknown expected-game coverage and unresolved items honestly; it never repairs raw files or accepts a source automatically. See the [source report](docs/source-verification.md#october-25-resumed-execution) for the tested CLI command and the [execution status](docs/execution-status.md) for all sixteen published issues. The linked [execution board](https://github.com/users/Bixzare/projects/1/views/2) contains three Finished, eleven In progress, and two Backlog items, read back October 27. Required hosted gates keep the database issues open even if local implementation PRs merge first.

To activate the existing environment in a VS Code PowerShell terminal, from the repository root:

```powershell
# Only needed if PowerShell blocks Activate.ps1; affects this terminal process only.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
```

The interpreter should end in `Hoop\.venv\Scripts\python.exe`. Run `deactivate` to leave the environment. Activation changes terminal command lookup; a notebook separately needs **Select Kernel > Python Environments > .venv**. Using `uv run --locked` does not require activation.

Open [test.ipynb](test.ipynb) and select that project kernel. Run all cells with the defaults first: only synthetic fixtures are checked, with no NBA requests. To test real historical access on your own machine, set `RUN_LIVE = True` and `CONFIRM_LOCAL_MACHINE = True`, then restart the kernel and run all cells once. It checks a small 2025-26 player and team sample independently, with two requests at most, a 30 second timeout per request, and no retries. The revised notebook calls `nba_api.LeagueGameLog(...)` and `league_game_log.get_data_frame()` through the native client, as in the [maintainers' endpoint examples](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/examples.md). Its documented `headers` option retains Baseline's identity instead of the package's browser identity. No API key or added proxy is used. A temporary session retains responses before native parsing and is restored afterward; this diagnostic is sequential and uses the package's normal response buffering, not a production download limiter.

The notebook now also includes a separate **Stock client diagnostic** section, approved for one local diagnostic only. It uses unchanged nba_api 1.11.4 defaults, without header/proxy overrides, session replacement, hooks, or copied cookies. Both samples succeeded on October 15: 636 player rows and 60 team rows. Open the [executed result](artifacts/notebook-revisions/20261015T210943Z-stock-executed.ipynb) locally to inspect the outputs. Its decoded response text and verified hashes are under `artifacts/notebook-history-stock/ecb4ebeb757f4e459465e0d71c47d170/`. No rerun is needed. To deliberately repeat this diagnostic locally, leave `RUN_LIVE = False`, restart the kernel, and set `RUN_STOCK_DEFAULTS` and `STOCK_LOCAL_CONFIRMED` to `True`. It makes at most two endpoint calls with a 20 second connect/read timeout and stops on the first failure. Reset all live switches before committing. Ongoing collection with these defaults still needs owner review; this diagnostic does not change production policy.

Inspect the separate results and retained evidence under `artifacts/notebook-history-native/<run-id>/`. Earlier urllib results stay under `artifacts/notebook-history/`, and the owner's executed notebook was preserved under `artifacts/notebook-revisions/` before revision. Both samples must validate before historical route acceptance can be reviewed. A successful fixture run does not verify access; a small live sample does not establish full-season completeness. This notebook does not test schedules, rosters, or cloud collection. Keep those gates separate, and clear outputs and reset both switches before committing.

October 15 diagnosis narrowed the local failure: DNS, TCP, verified TLS, and a separate Python HTTPS control all pass. Standard Windows curl also receives no HTTP response for the history request over either IPv6 or IPv4. The [source report](docs/source-verification.md#layered-local-diagnosis-october-15) records timings, retained evidence, remaining hypotheses, and focused owner checks. No supported fix or accepted historical route has yet been established; dependencies and security settings were unchanged.

`.github/workflows/ci.yml` uses `uv python install 3.12.14` on Ubuntu 24.04 and Windows 2025 because the GitHub `setup-python` manifest does not supply that security-release version on Windows. uv's managed distribution is available on both platforms. The Linux job runs locked install, lint/format, strict types, boundary checks, tests, package build, and fresh-kernel imports on every PR. The minimal Windows job runs locked install, tests, and the same kernel/import/path checks. Both use pinned action revisions, a ten-minute timeout, and read-only repository permissions; routine PR checks use fixtures and no production credentials. SOURCE-001 adds source cutoff/leakage tests and the offline access notebook execution; Postgres integration and later workflow notebooks enter with their implementing issues. Live CDN probes run only through an explicit manual dispatch opt-in or the dedicated manual source workflow. The [source report](docs/source-verification.md) documents commands, retained evidence, failed/unverified gates, and local-machine prerequisites. No database, prediction, or production scheduler capability is claimed.

The boundary checker scans every Python file under `src/hoop/platform/`, including new nested modules and initializers. It rejects absolute/relative NBA imports, imports under `TYPE_CHECKING`, and wildcard imports from `hoop.domains`; permitted shared and synthetic-domain imports are fixture-tested. This is static import enforcement, not proof against arbitrary runtime import construction or proof that future shared contracts are domain-independent. Do not add dynamic plugin discovery. A forbidden import reports the file, line, and direction rule with exit code 1. An automated subprocess regression exercises the CI command against a new nested module: it verifies rejection and the diagnostic, then verifies success after the NBA dependency is moved into domain code and the platform uses shared imports. Temporary negative controls also demonstrated that Ruff rejects an unused import, mypy rejects a string assigned to an integer, and pytest rejects a failed assertion; those failures were removed and the required suite passed afterward.

All seven project skill files and six retained upstream licenses were checked against the planning seed. Automatic skill discovery is **unverified in this client**; the assigned Python testing skill was read explicitly. If a fresh client's catalog omits them, reopen the repository/restart the client and verify its catalog; no client restart was performed here.

Ignore rules exclude virtual environments, secrets, data, models, artifacts, caches, notebook checkpoints, and build outputs. Review the staged file list before publication. The reviewed planning documents, skills, and logos remain in Git.

Repository destination confirmed October 13, 2026: a new public `baseline` repository under the owner's personal account. On October 14, the authenticated GitHub account was verified as `Bixzare`, repository name availability was checked, local Git was initialized on `main`, and the public [Bixzare/baseline repository](https://github.com/Bixzare/baseline) was created. BOOT-001 reverified the authenticated owner, public repository, and unchanged main planning seed `cf6bcda14d0432dfbb49e8f48e19fb18836f16ec`; it uses the separate `boot-001-python-ci` branch and preserves existing history.

Database destination confirmed October 13, 2026: a new dedicated Supabase Free project named baseline, subject to account allowance. The dedicated Free project is now provisioned; actual runtime connectivity, configured identities, allowance measurements and backup/restore remain gates. No paid plan or add-on is approved.

### Database rehearsal

DB-001 adds [database setup and gates](docs/database-setup.md), ordered migrations,
restricted runtime provisioning and a manual hosted connection workflow. The
Supabase Free project is created; see the current hosted setup evidence. Local Postgres 17.11 passed migration and
role tests plus an isolated foundation export/restore. Postgres 17 in CI is
provisional until the project's actual version is verified.

`uv run --locked pytest` now requires `BASELINE_TEST_DSN` for a disposable local
Postgres service. Missing setup fails required integration checks. The Windows
compatibility job explicitly uses `pytest -m "not postgres"`; Linux runs the
complete suite against real Postgres. Migration commands are
`uv run --locked python -m hoop.platform.database inspect` and `apply`.
Configure migration/runtime credentials separately, outside tracked files.

DB-002 adds [private artifacts and evidence](docs/artifact-storage.md): immutable
run/source records, verified uploads, independent in-memory Auth sessions, a saved
probe bridge and a manual permission rehearsal. The shared platform supports a
synthetic second domain. Real Postgres checks use isolated provider fixtures;
mocked HTTP success does not establish hosted Supabase behavior. No project,
identity, bucket or production forecast is activated by this implementation.

DB-003 adds [compact history planning/import](docs/seed-import.md), eight history
tables and cutoff-aware revision reads. `uv run --locked python -m
hoop.domains.nba.history --help` documents the plan/apply entry point. The notebook
defaults to a fixture-only plan. The real seed remains blocked by quarantine,
source-date verification, acceptance and the original raw upload size.

MODEL-001 adds [baseline preparation](docs/baseline-preparation.md) and
`notebooks/02_baseline_and_ledger.ipynb`. The fixture CLI prepares five targets per
roster member with explicit abstentions and verified snapshot reuse. The separate
real-input operation remains gated; prepared values are not official forecasts.

LEDGER-001 adds [ledger integrity and controlled registration](docs/ledger-registration.md).
Runtime can inspect model/bundle identities but cannot insert forecasts or receipts.
Database constraints protect one decision per occurrence/subject/target; actual
publication, visibility confirmation and complete-cohort checks arrive next.

Protected publication and disposable rehearsal: [LEDGER-002 operations](docs/publication.md).
The command uses actual restricted SQL roles with fixture sources and mock Storage; production gates remain open.

Schedule/status/current roster commands and source gates: [collection](docs/collection.md).
No source is enabled by the default configuration.

Versioned finals, DNP/unknown handling, correction work and rehearsal: [outcomes](docs/outcomes.md).
Use `uv run --locked python -m scripts.rehearse_publication --outcomes` only with disposable local Postgres.

Per-target errors, coverage and immutable report reproduction: [evaluation](docs/evaluation.md).
Use `uv run --locked python -m scripts.rehearse_publication --reports` with disposable local Postgres for the complete walkthrough.

Default-off nightly/dispatcher stages, rehearsal and activation controls: [cloud operations](docs/cloud-operations.md).

Independent Windows health, disabled task definitions, offline behavior and actual rehearsal evidence: [local recovery](docs/local-recovery.md). Owner notification delivery, accepted sources, hosted setup and backup remain gates.

Actual Supabase project, migration progress and remaining setup gates: [hosted setup evidence](docs/supabase-setup-status.md). The owner-approved managed Auth correction is applied; publisher migration and runtime/Auth/Storage checks remain gated.

Independent snapshot backups, original-reference restoration and default-off OneDrive verification: [backup operations](docs/backups.md). For the next private setup step, follow [Supabase credentials](docs/private-supabase-setup.md); the local `.env` has public metadata only until you fill its private fields.

Database health checks report client TLS and Postgres backend TLS separately;
see [connection verification](docs/database-setup.md). Session-pooler setup uses
the downloaded CA and `sslmode=verify-full`.

Manual hosted rehearsals retain sanitized reports in Actions. The database
workflow carries the reviewed public CA; environment credentials remain separate
from fixture CI. See [database rehearsal](docs/database-setup.md).

Native backup tools receive the configured public CA while setup keys remain
excluded from subprocess environments. OneDrive remote readback and native
Postgres client provisioning remain explicit setup gates.

Controlled current-state export and independently downloaded restore are now
reproducible with `python -m scripts.rehearse_hosted_backup`; its default is a
no-write plan. Full launch archive coverage and daily backups remain pending.
