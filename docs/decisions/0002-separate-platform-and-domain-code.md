# ADR 0002: Separate platform operations from NBA code

Status: LOCKED by the project owner on October 12, 2026.

Date: October 12, 2026

Decision basis: [PRD v1.1, PLATFORM-01](../PRD.md#platform-01-domain-boundary) and [design Section 3](../design.md#3-repository-and-boundaries). This record documents the approved architecture; implementation remains outstanding.

## Context

Baseline's first deployment serves NBA predictions. A later Clash Royale model should reuse the prediction record, evaluation, monitoring, and model lifecycle work. NBA source formats, basketball features, and award rules have different responsibilities from those platform operations.

The project is maintained by one owner with limited time after launch. The boundary must support reuse without requiring a general framework or a second real deployment before opening night.

## Decision

- Keep one source repository. Place shared operations in `src/hoop/platform/` and NBA logic in `src/hoop/domains/nba/`.
- Platform responsibilities are run tracking, artifact manifests, source contracts, database access, ledger lifecycle, evaluation interfaces, monitoring, training requests, and promotion records.
- NBA responsibilities are source adapters, identities, schedules and rosters, normalization, basketball features, baselines and model specifications, outcome interpretation, evaluation groups, and awards eligibility.
- Platform modules must not import NBA modules or require basketball columns. NBA modules supply explicit events, subjects, targets, feature manifests, outcomes, and metric definitions through the shared contracts.
- Use a small set of explicit contracts for source fetch/validate/normalize, feature construction at a cutoff, prediction from a model bundle, outcome extraction, and evaluation. Do not add dynamic plugin discovery.
- Keep CLI entry points thin. Notebooks and schedulers call the same tested operations. Keep `dashboard/` independently buildable and deployable within the repository.
- Exercise shared prediction, outcome, and evaluation contracts with a small synthetic non-NBA fixture. Implement the real Clash Royale deployment later.

The `hoop` paths are existing internal planning names. Public branding uses Baseline; this ADR does not introduce a package rename.

## Reason and alternatives

Explicit boundaries let NBA work evolve while preserving the shared evidence and lifecycle controls. One repository keeps changes to contracts, callers, tests, and documentation reviewable together. The synthetic fixture provides an early check for basketball assumptions without expanding launch scope.

Mixing NBA logic into shared operations would make the first implementation quicker to organize but increase the later cost of reuse. Separate service repositories would add deployment and coordination work before there is a demonstrated need. A plugin framework would add discovery and configuration machinery for a project with one implemented domain. Those alternatives are not selected.

## Consequences

Some domain operations must translate into explicit platform objects. This adds a small amount of interface work and requires contract tests. New fields and contracts must be justified by the current task rather than an imagined future feature.

The synthetic fixture demonstrates limited independence; it cannot prove that all Clash Royale requirements are supported. Track that limitation in [W-13](../../Weaknesses.md#w-13-reuse-outside-nba-is-designed-but-not-yet-demonstrated) until a real second deployment is implemented.

## Verification required during implementation

- Enforce the dependency direction in CI: platform modules cannot depend on NBA modules.
- Run the synthetic fixture through shared prediction, outcome, and evaluation contracts without NBA columns or award rules.
- Verify notebook and CLI paths match on the same fixed inputs and configuration; scheduler entry points use the shared operations.
- When the dashboard exists, verify its own build and deployment can complete independently of collection and training jobs.

Approval: the owner explicitly said "lock" on October 12, 2026. This record does not authorize the Clash Royale implementation or application development in this planning chat.
