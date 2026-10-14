"""Reject static imports of NBA modules from every platform Python file."""

import argparse
import ast
import sys
from importlib.util import resolve_name
from pathlib import Path


def boundary_violations(package_root: Path) -> list[str]:
    """Scan nested modules too; report filename, line, and forbidden import."""
    platform_root = package_root / "platform"
    if not platform_root.is_dir():
        raise ValueError(f"Platform directory does not exist: {platform_root}")
    files = sorted(platform_root.rglob("*.py"))
    if not files:
        raise ValueError(f"No Python modules found in {platform_root}")
    violations = []
    for path in files:
        parts = path.relative_to(package_root.parent).with_suffix("").parts
        package = ".".join(parts[:-1])
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imports: list[str] = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    module = resolve_name("." * node.level + module, package)
                imports = [module, *(f"{module}.{alias.name}" for alias in node.names)]
                if module == "hoop.domains" and any(a.name == "*" for a in node.names):
                    imports.append("hoop.domains.nba")
            else:
                continue
            for module in imports:
                if module == "hoop.domains.nba" or module.startswith("hoop.domains.nba."):
                    violations.append(
                        f"{path}:{node.lineno}: platform must not import {module}; "
                        "pass shared contracts from domain code instead"
                    )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path("src/hoop"))
    args = parser.parse_args()
    try:
        violations = boundary_violations(args.package_root)
    except (ValueError, SyntaxError, ImportError) as error:
        print(error, file=sys.stderr)
        return 1
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1
    print(f"Platform import boundary: OK ({args.package_root / 'platform'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
