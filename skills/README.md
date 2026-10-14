# Baseline project skills: review inventory

Status: LOCKED by the project owner on October 12, 2026. Installed in the repository discovery folder; session discovery confirmed October 13, 2026.

Prepared: October 12, 2026.

These seven skills support the coding agent's work on one issue at a time. Six are project adaptations of skills discovered through [Awesome Skills](https://awesomeskill.ai/); one is original guidance for the owner's notebook workflow. They contain instructions, not application implementation or bundled executable helpers.

The requested `awesomeskil.ai` address did not resolve during this review. The matching catalog at `awesomeskill.ai` was used. Discovery came from that catalog; source files were fetched from the linked upstream GitHub repositories at fixed commits, using the skill installer helper into a temporary review directory. Catalog security scores were not treated as proof of safety.

## Selection and scope

| Project skill | Catalog source | What it contributes |
| --- | --- | --- |
| [hoop-data-quality](../.agents/skills/hoop-data-quality/SKILL.md) | [data-quality-frameworks](https://awesomeskill.ai/skill/agents-data-quality-frameworks) | Source contracts, validation, freshness, provenance, and temporal correctness. |
| [hoop-python-testing](../.agents/skills/hoop-python-testing/SKILL.md) | [python-testing-patterns](https://awesomeskill.ai/skill/agents-python-testing-patterns) | Fixtures, failure cases, integration checks, and explicit leakage tests. |
| [hoop-postgres](../.agents/skills/hoop-postgres/SKILL.md) | [supabase-postgres-best-practices](https://awesomeskill.ai/skill/supabase-agent-skills-supabase-postgres-best-practices) | Migrations, least privilege, ledger integrity, query efficiency, and recovery. |
| [hoop-ml-lifecycle](../.agents/skills/hoop-ml-lifecycle/SKILL.md) | [ml-pipeline-workflow](https://awesomeskill.ai/skill/agents-ml-pipeline-workflow) | Reproducible stages, evaluation, tracking, promotion, and monitoring. |
| [hoop-notebooks](../.agents/skills/hoop-notebooks/SKILL.md) | Original project skill | Concise executable learning walkthroughs, EDA, shared logic, and rehearsal defaults. |
| [hoop-frontend-design](../.agents/skills/hoop-frontend-design/SKILL.md) | [frontend-design](https://awesomeskill.ai/skill/skills-frontend-design) | Layout, chart communication, responsive behavior, and honest data states. |
| [hoop-webapp-testing](../.agents/skills/hoop-webapp-testing/SKILL.md) | [webapp-testing](https://awesomeskill.ai/skill/skills-webapp-testing) | Browser interactions, accessibility, mobile checks, and public-read boundaries. |

The owner confirmed a clean analytics dashboard, filters/tooltips/drilldowns, and desktop analysis adapted for mobile. These choices are included in both frontend skills. The product name is Baseline, with supplied SVG logos and palette in `logos/`; see the [project README](../README.md). Existing `hoop-*` skill identifiers remain internal names. The frontend uses TypeScript and Tailwind CSS v4. [Locked ADR 0010](../docs/decisions/0010-publish-an-independent-dashboard-with-honest-history.md) records shadcn/ui as the primary component system with selective free Magic UI or Aceternity additions, incorporated into design v1.1. UI typography and the chart library remain choices for the dashboard issue. This package does not add Next.js, Figma, a design platform subscription, or another frontend framework.

## Provenance

All six upstream `SKILL.md` files were read. Relevant additional examples and license files were inspected. The project skills are substantially rewritten adaptations, not verbatim upstream installations. Project-specific rules come from the locked PRD v1.1, technical design v1.1, and owner-confirmed choices. The owner locked the guide and skills package together.

| Skill | Pinned upstream file | License |
| --- | --- | --- |
| Data quality | [wshobson/agents: plugins/data-engineering/skills/data-quality-frameworks/SKILL.md](https://github.com/wshobson/agents/blob/46891e7e60da0e52baf1050b7b6391b64e84c6d9/plugins/data-engineering/skills/data-quality-frameworks/SKILL.md) | MIT; notice retained in the skill directory. |
| Python testing | [wshobson/agents: plugins/python-development/skills/python-testing-patterns/SKILL.md](https://github.com/wshobson/agents/blob/46891e7e60da0e52baf1050b7b6391b64e84c6d9/plugins/python-development/skills/python-testing-patterns/SKILL.md) | MIT; notice retained in the skill directory. |
| ML lifecycle | [wshobson/agents: plugins/machine-learning-ops/skills/ml-pipeline-workflow/SKILL.md](https://github.com/wshobson/agents/blob/46891e7e60da0e52baf1050b7b6391b64e84c6d9/plugins/machine-learning-ops/skills/ml-pipeline-workflow/SKILL.md) | MIT; notice retained in the skill directory. |
| Postgres | [supabase/agent-skills: skills/supabase-postgres-best-practices/SKILL.md](https://github.com/supabase/agent-skills/blob/c9be0e931b7930f7d02126d04774d904c381e7d7/skills/supabase-postgres-best-practices/SKILL.md) | MIT; notice retained in the skill directory. |
| Frontend design | [anthropics/skills: skills/frontend-design/SKILL.md](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design/SKILL.md) | Apache-2.0; license retained in the skill directory. |
| Browser testing | [anthropics/skills: skills/webapp-testing/SKILL.md](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/webapp-testing/SKILL.md) | Apache-2.0; license retained in the skill directory. |

Original upstream `SKILL.md` SHA-256 checksums, before adaptation:

| Upstream skill | SHA-256 |
| --- | --- |
| data-quality-frameworks | `58e61444165ba7caa572fb7f1ba2d23cfd5038cfa6699f86b5648e7fcb71d34d` |
| python-testing-patterns | `a1020718f31629c2a5b20731cad1804dbb81b18800495c5cebdf16e6cac9c175` |
| ml-pipeline-workflow | `3049880901f70761137ef8818c6e0e5c357e5d108b82be48003e98c882a31c8b` |
| supabase-postgres-best-practices | `ad65e776f45e761bafc609d3f506c77c1032225aa65e0c4c02f241b8071e5855` |
| frontend-design | `d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3` |
| webapp-testing | `51b7349e77ec63b7744a6f63647e7566a0b4d2e301121cc10e8c2113af6556a2` |

These hashes identify source material, not the edited project files. A later update requires a new source review, recorded revision, and a focused diff.

## Adaptation decisions

- Data quality: kept validation dimensions, contracts, relationships, freshness, and reporting. Removed Great Expectations/dbt setup and generic code examples. Added source capability checks, historical availability limits, roster cohorts, and immutable revisions.
- Python testing: kept fixture isolation, parametrized boundaries, bounded retry checks, and meaningful assertions. Added leakage, real Postgres roles, publication races, and notebook checks. The catalog flags network and credential terms in examples; inspected examples included mocked requests and literal test credentials. Those examples and all helper code were omitted. This is a scoped content review, not a security certification of the upstream repository.
- ML lifecycle: kept staged reproducibility, lineage, tracking, and recovery. Removed unsupported references to absent bundled templates, cloud ML services, streaming, distributed training, and drift-triggered retraining. Added the approved evaluation/promotion constraints and owner-confirmed operating choices.
- Postgres: retained schema, privilege, transaction, performance, and recovery principles. Replaced generic user/tenant examples with the public read-only product boundary. Made immutable ledger behavior explicit so generic upsert advice cannot overwrite predictions. No upstream SQL examples or extensions are bundled.
- Frontend: retained intentional hierarchy, typography, tokens, responsive review, and restrained motion. Replaced the assumed design-studio persona and pressure for visual novelty with the owner's analytics brief. Selected the Apache-licensed `anthropics/skills` entry rather than the `anthropics/claude-code` variant whose repository license points to commercial terms.
- Browser testing: retained inspecting the rendered interface before acting, meaningful locators, screenshots, and console checks. Removed instructions to execute helpers without reading them, mandatory Python scripts, fixed sleeps, and mandatory network-idle waits. Use the project's chosen test stack and explicit visible-state assertions.
- Notebooks: authored for the owner's learning goals; no catalog provenance is claimed. This small skill covers a requirement that the selected general skills do not express adequately.

The tradeoff is maintaining seven short adaptations when upstream guidance changes. This is preferable here to importing broad workflows that can contradict the ledger, evaluation policy, or launch scope. No automatic updates are planned.

## Repository installation and discovery

The seven skill directories, including retained licenses, were moved into `.agents/skills/` within this repository. Their file hashes were verified before and after the move. This inventory remains at `skills/README.md` as the provenance record.

Codex supports repository skills in `.agents/skills/`. [Official skills documentation](https://learn.chatgpt.com/docs/build-skills). Installation here does not prove discovery in an already-running client.

All seven project skills appeared in this session's available-skills catalog on October 13, 2026, with paths under this repository's `.agents/skills/`. This verifies discovery here. Recheck when opening the separate execution session; restart the client if its skill list has not refreshed.

The owner's explicit "lock" covered AGENTS.md and all seven project skills, including their provenance, retained licenses, and repository activation. The design, both PRD amendments, and ADRs 0001 through 0011 are already locked. This approval does not start implementation or authorize changing global skills or user settings.

## Verification scope

Completed on October 12, 2026:

- All seven skills passed the skill-creator `quick_validate.py` check. Its missing PyYAML dependency was installed only in the temporary review directory, not in the project or a global environment.
- All local Markdown links in the new guide, README, inventory, and seven skills resolved.
- All skill names matched their directories; all six upstream license files were present.
- `AGENTS.md` contains 182 lines after the final contract review, below the required 200-line limit.
- Newly authored Markdown contained no em dashes. The instructions were reviewed against the locked PRD and confirmed frontend/notebook choices.
- No application code, upstream helper scripts, global skills, or automatic skill updates were introduced.

Final review corrected the notebook amendment's stale approval note and made timely visibility receipts, full-roster promotion evidence, initial rate-model inputs, awards release gates, and historical dashboard comparisons explicit in the relevant guidance. The approved skills are installed in the repository discovery folder and are discoverable in this session. The separate execution session must recheck its own catalog.

Installation rechecked October 13, 2026: all seven installed skills passed metadata validation; local document links, six retained licenses, the 182-line guide, and unchanged file hashes across the move were verified. No staged skill directories remain under `skills/`.

There is no application scaffold to lint, type-check, or test yet. These skills improve task guidance; their effectiveness still needs observation during the first assigned coding issues.
