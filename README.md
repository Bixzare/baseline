# Baseline

NBA season prediction platform and public ML analytics dashboard for 2026-27.

Status: launch planning complete. The public [Bixzare/baseline repository](https://github.com/Bixzare/baseline) is initialized. Sixteen local issue specifications are finalized; application implementation, service provisioning, source verification, and launch readiness remain outstanding.

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
| [Coding agent guide](AGENTS.md) | Locked; 184 lines. |
| [Project skills and provenance](skills/README.md) | Locked; seven skills installed in `.agents/skills/` and discovered in this session on October 13. |
| [Known weaknesses and improvements](Weaknesses.md) | Locked v1.0; living register maintained through owner review. |
| [BOOT-001: Repository and PR checks](docs/issues/BOOT-001-repository-python-and-pr-ci.md) | Locked specification; not yet implemented or published to GitHub. |
| [SOURCE-001: NBA source capability verification](docs/issues/SOURCE-001-verify-nba-capabilities-by-environment.md) | Locked specification; observed access and source acceptance remain execution gates. |
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

The owner confirmed launch-first planning on October 14, then approved finalizing its remaining issues without individual lock pauses. This changes planning order, not approved scope. Later model/MLOps/dashboard/awards issues are detailed before their implementation. IDs below are planning IDs, not published GitHub issue numbers. The repository and local Git checkout are initialized; BOOT-001 still publishes the first issue and establishes the implementation branch and PR. Subsequent assigned tasks publish/reuse their actual issue before the linked PR. When publishing, convert document links to the actual repository/default-branch URLs and map dependencies to real issue numbers without changing approved contracts. No issue has been published yet.

| Order | Planning ID | Required implemented dependencies / gate |
| --- | --- | --- |
| 1 | BOOT-001 | No code prerequisite; verify owner-owned public repository destination and environment. |
| 2 | SOURCE-001 | BOOT-001; actual source capability/routing acceptance. |
| 3 | DATA-001 | BOOT-001, accepted SOURCE-001 historical adapter; report full-seed acceptance/gaps. |
| 4 | DB-001 | BOOT-001; dedicated Free project, actual connection/role/allowance verification. |
| 5 | DB-002 | DB-001, SOURCE-001; restricted private artifact authentication and evidence contracts. |
| 6 | DB-003 | DATA-001, DB-002; accepted seed and verified artifact references. |
| 7 | MODEL-001 | DB-003; fixture preparation may precede real fresh-input rehearsal. |
| 8 | LEDGER-001 | DB-003, MODEL-001; actual baseline descriptor for registration. |
| 9 | LEDGER-002 | LEDGER-001, MODEL-001; protected publication/receipt protocol. |
| 10 | COLLECT-001 | SOURCE-001, DB-003, LEDGER-002; actual fresh capability routing. |
| 11 | OUTCOME-001 | COLLECT-001, LEDGER-002, DB-003; accepted final-result adapter. |
| 12 | EVAL-001 | OUTCOME-001, COLLECT-001, LEDGER-002. |
| 13 | OPS-001 | COLLECT-001, OUTCOME-001, EVAL-001, LEDGER-002; production enable remains off. |
| 14 | OPS-002 | OPS-001 and shared source/ledger/report operations; actual Windows/notification checks. |
| 15 | BACKUP-001 | DB-001/002, LEDGER-002, OUTCOME-001, EVAL-001, OPS-002; provider/isolated target setup. |
| 16 | LAUNCH-001 | Every prior issue implemented/reviewed and required runtime gates verified. |

Dependencies mean implemented, tested, owner-reviewed interfaces, not that every later launch gate has already passed. An implementation PR may report a blocked real-input rehearsal honestly while delivering fixture-tested operations, if its issue allows that. COLLECT-001 then supplies fresh recurring inputs; LAUNCH-001 requires actual readiness before activation. OPS-002 can test/alert on an unverified backup before BACKUP-001 produces real evidence, so those tasks have no circular prerequisite.

The revised [critical path](docs/critical-path.md#updated-execution-plan-october-14-20) estimates about 44-51 agent hours plus review/setup/drills, conditional on rapid source/database verification. The original 28-hour calendar is not a reliable guarantee. At source/database checkpoints, reassess real duration and deadline risk. No optional later module or document may delay launch.

### First execution assignment

Start a fresh coding session and assign only [BOOT-001](docs/issues/BOOT-001-repository-python-and-pr-ci.md): read AGENTS.md and that issue, implement its scope, create/reuse the real linked GitHub issue and reviewable PR as specified, run its required checks, and return exact evidence plus a short explanation of the decisions. Do not merge or begin SOURCE-001 until the owner reviews the bootstrap diff. This planning chat has not validated application commands; update AGENTS.md only after commands work.

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

No application setup commands have been validated. The bootstrap issue will establish Python 3.12 with uv, dependency locking, lint/type/test configuration, and CI. Dashboard commands follow when its React/Vite package exists. Proposed checks in `AGENTS.md` must not be read as a passing build.

Repository destination confirmed October 13, 2026: a new public `baseline` repository under the owner's personal account. On October 14, the authenticated GitHub account was verified as `Bixzare`, repository name availability was checked, local Git was initialized on `main`, and the public [Bixzare/baseline repository](https://github.com/Bixzare/baseline) was created. The initial publication contains approved planning documents, repository skills with licenses, and original logos. Application implementation remains outstanding and belongs on a separate branch and PR under BOOT-001.

Database destination confirmed October 13, 2026: a new dedicated Supabase Free project named baseline, subject to account allowance. No project has been provisioned; connectivity, roles, actual limits, and backup/restore remain verification gates. No paid plan or add-on is approved.
