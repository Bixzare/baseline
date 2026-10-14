"""Enforce ADR 0002 against the checkout and temporary, independent fixtures."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_boundaries import boundary_violations


@pytest.fixture
def package_root(tmp_path: Path) -> Path:
    root = tmp_path / "hoop"
    (root / "platform" / "nested").mkdir(parents=True)
    (root / "platform" / "__init__.py").write_text("", encoding="utf-8")
    return root


def test_checkout_platform_is_independent() -> None:
    root = Path(__file__).resolve().parents[2] / "src" / "hoop"
    assert boundary_violations(root) == []


@pytest.mark.parametrize(
    "source",
    [
        "import hoop.domains.nba",
        "import hoop.domains.nba.adapters as adapters",
        "from hoop.domains.nba import adapters",
        "from hoop.domains import nba as basketball",
        "from hoop.domains import *",
        "from ...domains.nba import adapters",
        "from ...domains import nba",
        "if True:\n    import hoop.domains.nba",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import hoop.domains.nba",
    ],
)
def test_rejects_nba_imports_in_new_nested_modules(package_root: Path, source: str) -> None:
    path = package_root / "platform" / "nested" / "new_module.py"
    path.write_text(source + "\n", encoding="utf-8")
    violations = boundary_violations(package_root)
    assert violations
    assert all(str(path) + ":" in item for item in violations)
    assert all("platform must not import hoop.domains.nba" in item for item in violations)


@pytest.mark.parametrize(
    "source",
    [
        "import pathlib\nfrom hoop.platform import artifacts",
        "from .. import contracts",
        "from hoop.domains.synthetic import events",
        "import hoop.domains.nba_like",
        'description = "import hoop.domains.nba"\n# import hoop.domains.nba',
    ],
)
def test_allows_shared_and_non_nba_imports(package_root: Path, source: str) -> None:
    (package_root / "platform" / "nested" / "shared.py").write_text(source, encoding="utf-8")
    assert boundary_violations(package_root) == []


def test_checks_platform_package_initializer(package_root: Path) -> None:
    path = package_root / "platform" / "__init__.py"
    path.write_text("from ..domains import nba\n", encoding="utf-8")
    assert any(f"{path}:1:" in item for item in boundary_violations(package_root))


def test_ci_command_rejects_new_nested_nba_import_and_accepts_repair(package_root: Path) -> None:
    checker = Path(__file__).resolve().parents[2] / "scripts" / "check_boundaries.py"
    path = package_root / "platform" / "nested" / "new_module.py"
    path.write_text(
        "# Accidental domain coupling\nfrom hoop.domains import nba\n", encoding="utf-8"
    )
    command = [sys.executable, str(checker), "--package-root", str(package_root)]

    rejected = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    assert rejected.returncode == 1
    assert f"{path}:2: platform must not import hoop.domains.nba" in rejected.stderr
    assert "pass shared contracts from domain code instead" in rejected.stderr
    assert "Platform import boundary: OK" not in rejected.stdout

    # Keep the domain dependency in domain code; platform imports only shared code.
    domain = package_root / "domains" / "nba"
    domain.mkdir(parents=True)
    (domain / "new_module.py").write_text("from hoop.domains import nba\n", encoding="utf-8")
    path.write_text("from hoop.platform import contracts\n", encoding="utf-8")

    repaired = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    assert repaired.returncode == 0
    assert repaired.stderr == ""
    assert "Platform import boundary: OK" in repaired.stdout


def test_missing_platform_is_not_a_passing_check(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Platform directory does not exist"):
        boundary_violations(tmp_path / "hoop")


def test_empty_platform_is_not_a_passing_check(tmp_path: Path) -> None:
    (tmp_path / "hoop" / "platform").mkdir(parents=True)
    with pytest.raises(ValueError, match="No Python modules found"):
        boundary_violations(tmp_path / "hoop")
