# Final outcomes and corrections

OUTCOME-001 implements parsing, retained-source reconciliation and immutable
outcome revisions. Default final routes are empty. No live final-source access,
hosted migration or production reconciliation was performed in this batch.

## Resolution and provenance

Both game/team identities, season, final status, non-tied scores, available player
totals, duplicate identities and numeric types are validated. ISO minutes retain
decimal seconds, including overtime. A missing statistic stays unresolved for
that target. A missing player row or zero displayed minutes cannot establish DNP.
`played=0` with a reason resolves zeros only when that interpretation is explicitly
accepted in the route and policy. Otherwise participation and values stay unknown.

The saved pregame cohort comes from the original batch artifact. Later final or
roster lists cannot replace it. Players outside that cohort may supply normalized
history facts, but cannot enter that forecast's coverage denominator. Without a
saved cohort, outcome entries describe team results only; they do not claim a
complete player forecast evaluation population. Accuracy aggregation is EVAL-001.

Before a transaction, ingestion reads/hash-checks the retained raw body, reparses
it and compares normalized content, then verifies the saved cohort and uploads
the outcome artifact. The short locked transaction appends player/team facts,
final status, the outcome version and reconciliation observation checkpoint.
Parser/config revisions receive new normalization hashes and current database
observation times after uploads/lock waits. They cannot become earlier features.
Legacy history rows retain their original identities and `legacy` normalization.

Semantic version identity covers normalized facts, saved cohort, parser and policy.
Exact repeats preserve original IDs/times; a genuinely new observation is linked
to that version through `outcome_observations`. Changed facts/parser/config append
a new version. Raw metadata-only changes retain separate raw/source observations
without creating another numerical outcome version. Previous artifacts/facts
remain available. Runtime can insert/read the permitted records and cannot edit,
delete or truncate them. An administrator remains outside runtime immutability.

## Work discovery and source policy

Pending work comes from persisted occurrences and reconciliation history.
Automatically revisit seven days of completed games plus unresolved known live
IDs. Already imported seed-only games without a live cohort/checkpoint are not
silently scheduled for another full historical backfill. Explicit IDs/ranges can
include older games. Excluded predecessors and unsupported suspensions stay out
of processing; absent scoreboard entries never erase saved work.

Routes bind parser/environment/owner acceptance like collection. A reviewed exact
NBA live-boxscore URL template can substitute only saved game IDs, teams and
allowed seasons; arbitrary URL templates or supplied teams are rejected. This
avoids requiring a new adapter acceptance for every game while keeping the source
and identity contract fixed. No template is accepted by the default config.
The same sequential three-second gap, 30-second timeout, two temporary retries
and 16-request/180-second budget applies. Denial stops the source. Each genuine
attempt has raw/check/run evidence, including sanitized failure reasons.

## Commands

```powershell
uv run --locked python -m hoop.domains.nba.outcomes work --environment local --output artifacts/outcome-work
uv run --locked python -m hoop.domains.nba.outcomes work --environment local --event EVENT_UUID --output artifacts/outcome-work
uv run --locked python -m hoop.domains.nba.outcomes reconcile --environment local --output artifacts/outcomes --confirm-source-gates
uv run --locked python -m scripts.rehearse_publication --outcomes
```

`--from-time` / `--to-time` accept explicit UTC timestamps for older correction
checks. Work reads need the restricted database; reconciliation also needs the
separate private Storage identity and accepted routes. The default reconciliation
command refuses before connecting. A failed database/audit write leaves a
sanitized local report with no claim of durable recording.

The last command is local synthetic rehearsal only, using `BASELINE_TEST_DSN`.
Its disposable database is created and removed by the verified rehearsal path.
The notebook has offline partial/DNP/comparison cells and an opt-in fresh-kernel
Postgres section calling those same operations. Its compressed timing scenario
deliberately supplies an earlier final-source start, which invalidates the fixture
forecast while preserving all predictions/receipts. It cannot supply live accuracy.

October 27 rehearsal: outcome `e1e6c6c3-4c31-510b-a088-f81aaaa7d3e1` had 18 resolved
and five unknown targets; correction `ee3f248c-d93b-53bd-a3d5-bf2709871e9a` had 23
resolved and zero unknown. Forecast values were unchanged. These counts include
eight team targets and fifteen saved-cohort player targets, not a live sample.

Actual final-source semantics, calendar mapping, regular-season/DNP coverage,
request/runtime measurements, hosted roles and independent recovery remain release
gates. Seven days is a workload policy, not a guarantee about NBA corrections.

The combined local suite passed 383 tests. After the final shared source-health
metadata update, 16 affected collection/outcome/fresh-kernel checks also passed.
Ruff lint/format, strict mypy, platform boundaries, wheel/sdist build and standalone
fresh-kernel identity passed. PR Linux/Windows checks are separate evidence.
