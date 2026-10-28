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
