# Cloud repair-lineage verification

Status: APPROVED by the owner on October 29, 2026. The optional workflow step
is implemented for diff review. Its first cloud execution waits for owner merge
to main; no feature-branch execution or secrets allowlist change is authorized.

After owner review and merge, extend the existing manual artifact-check.yml job
with an optional UUID input `seed_lineage_root_id` and this read-only command:

```text
uv run --locked python -m hoop.domains.nba.history.lineage check --confirm-rehearsal --report artifacts/artifact-check/repair-lineage.json
```

Pass the UUID through `BASELINE_SEED_LINEAGE_ROOT_ID` as an environment value,
never interpolate it into shell code. The command validates the UUID and reads
only registered candidate/repair objects, comparing every reference with its
registry record and the exact immutable candidate inventory.

The step receives the same existing restricted BASELINE_RUNTIME_DSN and
backend Auth email/password, plus the existing public project/bucket settings.
It receives no migration DSN or administrator key. The existing
artifact-rehearsal environment and selected-branch policy stay unchanged.
Execution is from already allowed main only after the owner merges reviewed code.
The input defaults empty, so ordinary checks and all schedules are unchanged.

Acceptance: explicit owner permission, fixture/integration verification, PR CI,
then one manual main-branch check with the registered lineage UUID. The check
cannot accept a seed, import NBA facts, activate a model, publish predictions or
change privileges. Its sanitized report joins existing artifact-check output.
