import re
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_production_jobs_require_main_and_explicit_enable_without_admin_credentials() -> None:
    for name, cron in [("nightly", "17 7 * * *"), ("dispatcher", "7,22,37,52 * * * *")]:
        body = (ROOT / f".github/workflows/{name}.yml").read_text()
        assert cron in body
        assert "vars.BASELINE_PRODUCTION_ENABLE == 'true'" in body
        assert "github.ref == 'refs/heads/main' && !inputs.fixture_rehearsal" in body
        assert "environment: baseline-production" in body
        assert "cancel-in-progress: false" in body
        assert "default: true" in body
        assert "pull_request_target" not in body
        for forbidden in ["MIGRATION_DSN", "ADMIN_KEY", "SERVICE_ROLE", "SUPABASE_PUBLIC_KEY"]:
            assert forbidden not in body
        assert "BASELINE_SUPABASE_PUBLISHABLE_KEY" in body
        for action in re.findall(r"uses: ([^\n]+)", body):
            if not action.startswith("./"):
                assert re.search(r"@[0-9a-f]{40}", action)


def test_reusable_fixture_workflow_has_no_production_secret_path() -> None:
    body = (ROOT / ".github/workflows/operations-rehearsal.yml").read_text()
    assert "secrets." not in body
    assert "BASELINE_TEST_DSN:" in body
    assert '"$OPERATION"' in body
    assert '"${arguments[@]}"' in body


def test_hosted_rehearsals_keep_privileged_secrets_out_and_retain_failures() -> None:
    for workflow, environment in [
        ("database-check", "database-rehearsal"),
        ("artifact-check", "artifact-rehearsal"),
    ]:
        body = (ROOT / f".github/workflows/{workflow}.yml").read_text()
        assert "workflow_dispatch:" in body
        assert "pull_request" not in body and "schedule:" not in body
        assert f"environment: {environment}" in body
        assert "cancel-in-progress: false" in body
        assert "if: always()" in body and "report.json" in body
        for name in ["BASELINE_MIGRATION_DSN", "BASELINE_SUPABASE_ADMIN_KEY", "SERVICE_ROLE"]:
            assert name not in body
    database = (ROOT / ".github/workflows/database-check.yml").read_text()
    assert "PGSSLROOTCERT:" in database
    assert "certificates/supabase-ca-2021.crt" in database
    certificate = (ROOT / "certificates/supabase-ca-2021.crt").read_text()
    assert "BEGIN CERTIFICATE" in certificate and "PRIVATE KEY" not in certificate


def test_repair_lineage_cloud_step_is_manual_main_only_and_uses_data_not_shell_input() -> None:
    body = (ROOT / ".github/workflows/artifact-check.yml").read_text()
    input_section = body.split("      seed_lineage_root_id:\n", 1)[1].split("permissions:", 1)[0]
    assert "required: false" in input_section and 'default: ""' in input_section
    step = next(
        block
        for block in body.split("      - name: ")
        if "hoop.domains.nba.history.lineage check" in block
    )
    assert "if: inputs.seed_lineage_root_id != '' && github.ref == 'refs/heads/main'" in step
    command = next(
        line.strip()[5:] for line in step.splitlines() if line.strip().startswith("run: ")
    )
    assert "${{" not in command and "--confirm-rehearsal" in command
    assert "repair-lineage.json" in command and " stage " not in command
    assert "BASELINE_SEED_LINEAGE_ROOT_ID: ${{ inputs.seed_lineage_root_id }}" in step
    assert set(re.findall(r"secrets\.([A-Z_]+)", step)) == {
        "BASELINE_RUNTIME_DSN",
        "BASELINE_ARTIFACT_EMAIL",
        "BASELINE_ARTIFACT_PASSWORD",
    }
    assert "schedule:" not in body and "pull_request" not in body
