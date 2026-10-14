# BOOT-001: Establish the repository, Python environment, and PR checks

Status: LOCKED by the project owner on October 13, 2026.

Prepared: October 13, 2026

Phase: 0. Priority: launch blocker. Dependencies: none of the other implementation issues.

Session estimate: 1.5 to 2 hours plus owner review, assuming GitHub authentication and Python installation work. This is a planning estimate, not measured execution time. Access or installation failures must be reported promptly so source verification is not delayed silently.

GitHub destination: new public `Bixzare/baseline`, chosen by the owner. The connected profile identifies Bixzare; verify the execution session's authenticated account and repository name availability before any publication. This local specification is not a published GitHub issue and its ID is not a GitHub issue number.

## Goal and context

Give the next source-verification task a reproducible Python 3.12 environment, a reviewable GitHub workflow, and required lint, type, and test checks. Baseline forecasts NBA player minutes, points, rebounds, assists, and threes made at launch. Its collectors and immutable pregame ledger are later tasks; this issue provides their foundation only.

The deadline is October 20, 2026 at 19:00 UTC, with first publication targeted at 17:00 UTC. Execution has not started as of October 13. Keep this bootstrap small and run the source-verification issue immediately afterward. Do not add frontend, model training, or infrastructure features here.

Required guidance: AGENTS.md and `.agents/skills/hoop-python-testing/SKILL.md`. The next coding session must verify discovery of all seven installed project skills, recording any client restart needed. Read the assigned skill explicitly if automatic discovery has not refreshed.

## Contracts to preserve

- Public product name: Baseline. Internal Python paths remain `src/hoop/`.
- Platform code under `src/hoop/platform/` must not import NBA code under `src/hoop/domains/nba/`. Use a small package structure, not a plugin framework.
- Use Python 3.12, uv, a committed dependency lockfile, Ruff, mypy, pytest, and a project Jupyter kernel. Lock exact compatible versions after verifying installation on Windows and Linux.
- CI runs on every PR. No routine PR check may call live NBA services, production Supabase, or require secrets, full history, or model training.
- No application schema or manually created production tables. SQL migrations and real Postgres behavior tests enter with the first database task; do not claim database correctness from this bootstrap.
- Learning notebooks and later scheduled jobs will share tested package operations. Do not create empty walkthrough notebooks or placeholder success outputs here.
- Small PRs reference one real GitHub issue; the owner reviews every diff. Passing checks do not authorize merge or deployment.

## Scope and execution sequence

1. Inspect this checkout, preserve existing planning files and logos, and verify GitHub identity, name availability, and the intended remote. If the repository already exists or belongs to another account, stop publication and ask the owner how to proceed. Never overwrite an existing remote or history.
2. Initialize Git and create the chosen public repository only when this issue is assigned for execution. Seed `main` with the owner-reviewed planning documents, AGENTS.md, installed project skills with licenses, and logo assets. This initial planning commit establishes the PR base; implementation belongs on a separate branch. Inspect the exact publication file list for secrets, private files, and unrelated work before pushing.
3. Publish this locked issue specification as the bootstrap issue, or reuse its existing issue if already published. Record its actual number and URL. Open one implementation branch and PR linked to that issue; do not invent a number or create duplicates on retry.
4. Create the installable `hoop` package structure, Python/dependency configuration, and ignore rules for environments, secrets, local data, models, caches, and notebook checkpoints. Include only bootstrap dependencies; source collection and ML tools enter with their own tasks.
5. Add meaningful package-boundary validation and configure Ruff, mypy, and pytest. Establish the Linux PR check job and a minimal Windows job for locked installation, package imports, paths, and project-kernel compatibility.
6. Verify installation and the selected Jupyter kernel locally. Document the actual commands, expected successful checks, and any environment prerequisite in README and AGENTS.md.
7. Provide the PR URL, CI run links, exact checks, discovery status, and one failure scenario for owner review. Do not merge the PR or start the next issue automatically.

## Acceptance criteria

- [ ] The intended repository is public and owned by Bixzare; the local remote matches it. The planning seed preserves approved documents, skills, retained licenses, and original logos.
- [ ] Bootstrap changes are isolated in one PR linked to the actual issue. No source probes, data ingestion, schema, training, or dashboard feature is included.
- [ ] A fresh Python 3.12 project environment installs from the committed lockfile on Windows and Linux. The package imports without depending on global Python packages or an unrelated Conda environment.
- [ ] The selected project Jupyter kernel uses that environment. Record kernel identity; a globally available notebook executable is not sufficient evidence.
- [ ] Ruff lint/format, mypy, and pytest run on every PR and pass for the submitted commit. The minimal Windows checks pass as well.
- [ ] The boundary check rejects a platform import of an NBA module and covers newly added platform modules automatically. Do not add a fabricated model function solely to make a test pass.
- [ ] CI needs no NBA connection, production database, or private credentials. Integration and notebook execution checks are added by their first implementing issues, using real Postgres and deterministic fixtures respectively.
- [ ] README and AGENTS.md contain verified setup/check commands and accurate implementation status. AGENTS.md remains under 200 lines. Record project-skill discovery as verified or explicitly unverified.

## Required tests and verification

- Exercise package-boundary validation with permitted shared imports and an intentionally forbidden NBA import in a temporary fixture. A violation must produce an actionable failure without modifying committed package code.
- Verify locked installation and imports from a clean environment on both supported operating systems. Check that the Jupyter kernel points to the project Python.
- In a temporary local change or disposable branch, demonstrate that a lint violation, type error, and failed assertion each cause the corresponding check to fail. Remove these deliberate failures before handing off the PR; report the evidence rather than committing broken examples.
- Review ignore behavior and the staged publication file list. Verify no environment, secrets, datasets, or generated model files are tracked.
- Data validation and leakage tests are not applicable to this issue because it adds no data transformations or predictions. They become mandatory in each later data/model issue; do not claim they were exercised here.

## Files likely affected

- `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`.
- Package initialization under `src/hoop/`, `src/hoop/platform/`, and `src/hoop/domains/nba/`.
- `tests/unit/` for package-boundary checks and their fixtures; test configuration as needed.
- `.github/workflows/ci.yml`, `.github/PULL_REQUEST_TEMPLATE.md`.
- README.md and AGENTS.md for verified commands and status; this issue file for the GitHub issue reference.
- Existing planning documents, `.agents/skills/`, and `logos/` enter the planning seed without unrelated content changes.

## Handoff and next dependency

Explain the environment flow from locked dependencies to installed package, notebook kernel, and CI. State why platform/domain separation matters, the cost of the Windows compatibility check, exact failures caught, and remaining unverified infrastructure. The immediate next issue verifies NBA source capabilities from the actual GitHub Actions runner and local machine. If this task exceeds its estimate, report the specific blocker and remaining work before expanding scope.

Approval: the owner explicitly said "lock" on October 13, 2026. This finalizes the specification; a separate assignment to the coding agent starts execution. No repository or GitHub issue has been created by this planning record.
