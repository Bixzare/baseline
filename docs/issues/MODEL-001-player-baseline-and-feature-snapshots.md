# MODEL-001: Prepare player baselines and reproducible feature snapshots

Status: LOCKED by the project owner on October 14, 2026.

Prepared: October 14, 2026

Phase: 1. Priority: launch blocker. Dependencies: DB-003 and its DATA-001/DB-002 inputs implemented and owner-reviewed. Required execution gates are accepted seed/history, functioning restricted database/artifact access, and accepted schedule/current-roster mappings from SOURCE-001. Pure fixture work can proceed while a hosted gate is blocked, but a real preparation rehearsal requires verified input references.

Session estimate: about 3 focused hours plus owner review and a bounded real-input rehearsal. Scope is player feature selection, deterministic baseline preparation, saved input/output artifacts, and the first part of the baseline notebook. Ledger schema/publication, orchestration, and outcome scoring are separate issues.


## October 25 execution context

The owner resumed sequential execution with the [historical-data amendment](../PRD-data-source-amendment.md).
Use accepted pinned seed/repair artifacts, preserve quarantine and unknowns,
and never infer historical pregame cohorts from outcomes. Injury ingestion is
deferred for the first release. The original October 20 target is past;
all timing/readiness gates now apply to the first approved future slate.
This task is backlog until its implemented/reviewed dependencies pass.
No runtime source acceptance, merge, deployment, or retrospective publication
is established by this amendment. Required tests and contracts below remain.


## Goal and context

For a verified upcoming game roster, prepare minutes, points, rebounds, assists, and threes made for every player, or a reasoned target abstention. Save the exact cohort and history used so later publication and evaluation cannot silently change inputs. This produces prepared forecasts, not official ledger entries.

Opening-night publication must happen before October 20, 2026 at 19:00 UTC, targeting 17:00 UTC. Use the approved 2025-26 seed and subsequent prior 2026-27 regular-season observations. No trained model, injury adjustment, team score projection, player replacement model, or new data source is part of this task.

Required guidance: AGENTS.md and `.agents/skills/hoop-data-quality/SKILL.md`, `hoop-python-testing`, and `hoop-notebooks`. Locked references: [ADR 0006](../decisions/0006-start-with-baselines-and-model-minutes-first.md), [PRD PLAYER-01](../PRD.md#player-01-launch-baseline), [design player features](../design.md#91-player-baselines), and [freshness/missing facts](../design.md#82-freshness-and-missing-facts). The contract below stands alone without chat history.

## Inputs and cohort contract

- Inputs: a game occurrence and its NBA source game identity, one explicit UTC feature cutoff, accepted schedule/status observation, verified current roster snapshots for both teams, versioned baseline policy, and cutoff-eligible history/evidence. Keep generation time separate from feature cutoff and from future database publication times.
- Read relevant database rows from a consistent snapshot. Resolve and hash-check referenced immutable artifacts outside database transactions. Keep a record of the selected IDs rather than requerying latest data after preparation.
- Require schedule/status and roster evidence collected and successfully validated by the cutoff. Essential schedule/status evidence must be at most 30 minutes old and roster evidence at most 24 hours old for preparation readiness. Detect stale source-generation evidence and identity mismatch. These preliminary checks do not replace ledger checks at actual publication time.
- Build the cohort from the saved current roster, including rookies, reserves, unavailable players, and players without history. Conflicting dual-team membership, a missing/invalid roster, unknown essential schedule, or a started game blocks the affected game preparation. Report uncovered games and unknown denominators; do not manufacture an empty successful cohort.
- Availability can remain unknown under the approved launch policy. Preserve supported availability flags as descriptive metadata, without inventing future status or adjusting baseline values. Target-game final box-score membership and eventual starters never define the cohort.

## History selection contract

1. Filter evidence by the cutoff before selecting the latest accepted fact revision. Require source receipt, successful validation, and fact observation no later than cutoff, plus no later known source publication time. Use DB-002's source eligibility helper and DB-003's revision readers; do not add a second competing timing implementation.
2. Select up to 10 prior completed regular-season appearances for the player across teams and seasons. Exclude the target occurrence and equivalent source game identity, future/unresolved events, preseason, playoffs, and confirmed nonappearances. Use supported participation semantics; absence from a source is not DNP evidence.
3. Order by supported game chronology, never collection order. Date-only historical records retain the accepted source-calendar convention and do not become fabricated midnight starts. If ambiguity affects which appearances enter the window, abstain and report it rather than ordering by a game ID as if it were a timestamp.
4. Preserve the chosen appearance window before assessing target completeness. Do not replace a recent missing value with an older complete row or silently calculate different target windows. Show selected fact/check IDs, history count, last appearance date, and all required values/units.
5. A known unresolved prior roster opportunity or coverage gap that could affect this window must remain visible. Request reconciliation through a clear preparation result for the later orchestrator; if unresolved, abstain for affected players. A gap outside the window need not block unaffected history. Do not infer past roster opportunities by crossing current players with old games.

## Formula, precision, and abstention contract

Let n be the selected appearance count and convert source seconds consistently to minutes. For the same selected appearances:

| Target | Formula and unit |
| --- | --- |
| Minutes | Sum of minutes divided by n; minutes. |
| Each counting-stat rate | Sum of that stat divided by sum of minutes; stat per minute. |
| Points, rebounds, assists, threes made | Predicted minutes multiplied by the corresponding pooled rate; expected stat count. |

Use full internal precision, finite nonnegative outputs, and deterministic serialization; display rounding does not change saved values. Expected counts may be fractional. Do not round individual rates before composition, use an unweighted mean of individual game rates, or cap valid overtime minutes at 48. The baseline does not normalize independent player projections to a team minute budget or claim lineup coherence.

- No selected appearances, ambiguous/unknown participation affecting the window, invalid/missing minutes, or a nonpositive/nonfinite total-minute denominator produces abstentions for all five targets with stable versioned reason codes. Never turn insufficient evidence into zero projections.
- Missing/invalid values for one counting stat produce an abstention for that target while otherwise supported targets remain prepared. Do not use a smaller target-specific window. The selected history count remains visible; target completeness is reported separately.
- Fewer than 10 supported appearances are allowed, including one, with a short-history flag. Confirmed historical DNPs are excluded from this appearance window; their zero outcomes enter later all-roster evaluation, not the rolling appearance average.
- Each player has exactly five target entries. Each entry is either a numeric value with unit or an abstention with null value and reason. Prepared cohort coverage includes abstentions and has no official-publication claim.

Hand-calculated test example: two appearances of 10 and 30 minutes with points 4 and 20, rebounds 3 and 7, assists 1 and 5, and threes 1 and 3. Expected minutes are 20, points 12, rebounds 5, assists 3, and threes 2. With complete common windows, composition must equal the ordinary mean of each counting stat within the documented numerical tolerance. This is a baseline identity, not evidence of improved accuracy.

## Output and execution contract

- Save a versioned cohort artifact, feature/history artifact, and prepared-output manifest using existing artifact helpers. Record occurrence/source identity, roster/schedule/check/fact IDs, cutoff, generation time, baseline family/target/configuration versions, code/dependency/configuration hashes, ordered inputs, history counts, completeness/availability flags, and target values or abstention reasons. Record environment and a platform run ID. Reuse only when all input/configuration identities match.
- Keep source references and normalized values sufficient to reproduce the forecast even when newer source revisions appear. Changed inputs create a new prepared version; they do not alter an earlier saved snapshot. Artifact failure leaves preparation incomplete and never produces a usable publication candidate.
- Provide thin fixture/rehearsal and explicit real-input preparation commands. Default paths cannot publish official predictions, activate models, change database schemas, or contact live NBA sources. A controlled real-input rehearsal may read accepted hosted facts and retain prepared artifacts; label it honestly without an official receipt.
- Use shared platform contracts for generic run/artifact/output handling, with NBA cohort/history/formulas in `src/hoop/domains/nba/`. Do not create prediction tables or activation functions here. The later ledger issue registers baseline model/bundle IDs and maps the versioned descriptor to those persisted records before publication.

## Execution sequence and notebook

1. Inspect DB-003's actual read interfaces and accepted source/seed metadata. Add cutoff-aware cohort/history preparation and clear game/player/target failure results, reusing existing evidence checks.
2. Implement the deterministic minutes/rate composition and versioned output manifest, with tests for common-window arithmetic and target-specific missingness.
3. Add `notebooks/02_baseline_and_ledger.ipynb` with concise purpose, inputs, run, inspect, and interpretation cells. For now, cover saved roster selection, prior history, formulas, values, abstentions, and reproducible artifact readback. State explicitly that publication and outcome reconciliation are delivered by later issues; do not fake those sections or create empty future notebooks.
4. Default fresh-kernel execution uses small fixed fixtures with no live transport or production writes. Compare semantic feature/projection outputs with the CLI for the same inputs, display whether work ran or reused a verified artifact, and invalidate stale cache identity. Keep large data/logs outside notebook outputs.
5. Run a bounded real preparation rehearsal only when source/history gates pass, using actual accepted inputs for a verified upcoming occurrence. Save the coverage/artifact report and disclose limitations. Preseason preparation cannot establish regular-season accuracy or official publication.
6. Update README and AGENTS.md under 200 lines with verified commands, notebook behavior, prepared versus official distinctions, and remaining gates. Record evidenced limitations in Weaknesses.md without waiving launch criteria.

## Acceptance criteria

- [ ] Every player in the valid saved roster receives five prepared entries, including explicit abstentions, flags, and denominator coverage. Invalid essential cohorts block the affected game rather than disappear.
- [ ] History uses the latest eligible revision selected after applying the cutoff, crosses teams/seasons, and retains missingness and unresolved opportunities. Future facts and target-game membership cannot enter inputs.
- [ ] Formulas match independent hand calculations and the common-window mean identity. Values are finite, nonnegative, precise, and uncapped for valid overtime.
- [ ] Missing minutes/history/participation and target-specific missing stats follow the documented abstention policy without silent older-row substitution or fabricated zeros.
- [ ] Saved cohort/features/output artifacts and version metadata reproduce the prepared values after later facts are appended. Stale/corrupt artifacts cannot be reused or handed to publication.
- [ ] The notebook and CLI agree on fixtures, fresh-kernel execution passes, and default operations cannot publish, activate, collect live data, or mutate production state.
- [ ] PR lint/type/tests, database revision-reader integration, explicit leakage tests, and notebook checks pass. Real preparation evidence is separately recorded or its blocked gate is reported truthfully.

## Required tests

- Independent expected-value fixtures for one, fewer/exactly/more than 10 appearances; unequal minutes; zero/nonfinite denominators; missing minutes; missing one stat; fractional minutes/count forecasts; valid overtime; and trades/season rollover. Compare composition to plain means without mirroring only the implementation.
- Real Postgres revision-reader fixtures with an eligible older revision and a late correction. Apply cutoffs before latest selection and verify the late revision cannot erase eligible history or contaminate it. Handle deterministic equivalent ties and conflicting ambiguous revisions visibly.
- Leakage fixtures for future games, later collection/validation/publication, target-game final membership/starters, late roster changes, imported historical assumptions, and date-only/ambiguous chronology. Exactly-at-feature-cutoff source evidence may qualify; later ledger publication cutoff rules remain separate.
- Cohort fixtures containing rookies, reserves, unknown availability, absent historical rows, duplicate/conflicting memberships, invalid artifact references, stale schedule/roster, and a started game. Preserve all valid roster opportunities and separate prepared numeric coverage from official coverage.
- Test unresolved recent opportunities versus gaps outside the selected window, source failures, target-specific abstentions, artifact upload/read/hash failure, configuration changes, and attempts to reuse mismatched snapshots.
- Execute the notebook from a fresh kernel with live transport/production publication blocked and compare semantic outputs with CLI fixtures. Exercise a synthetic second-domain prepared-output contract to ensure shared platform handling does not require basketball fields.

## Failure decision, likely files, and handoff

Missing essential schedule/roster/artifact evidence blocks preparation. Missing player history produces visible abstentions under the fixed policy. Do not improve apparent coverage by removing players, imputing unsupported numbers, adding an injury model, or using eventual participants. A fixture-only implementation does not establish a usable hosted preparation path.

Likely files: `src/hoop/domains/nba/features/`, `baselines/`, and existing history/roster readers; small shared snapshot/output contracts under `src/hoop/platform/`; thin CLI commands; versioned baseline configuration; `tests/unit/`, `tests/integration/`, `tests/leakage/`, `tests/notebooks/`, and fixtures; `notebooks/02_baseline_and_ledger.ipynb`; README.md, AGENTS.md, feature-preparation notes, and Weaknesses.md. No forecast-table migration, schedule workflow, trained-model dependency, or public dashboard code is included.

Return the PR, exact checks/results, notebook walkthrough, fixture arithmetic report, real rehearsal or gate-failure report, snapshot IDs/hashes and version descriptor, coverage/abstention counts, and a late-correction reproduction example. Explain why minutes/rate decomposition equals a recent average here, appearance history differs from full-roster evaluation, and a prepared artifact is not an official ledger forecast.

Approval: the owner explicitly said "lock" on October 14, 2026. This finalizes the specification; a separate coding-agent assignment starts execution. No baseline calculation, feature artifact, notebook execution, or official prediction has been implemented by this planning record.
