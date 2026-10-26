"""Privileged migration operations and a separate restricted connection check."""

import argparse
import json
import os
from pathlib import Path

from hoop.platform.database import (
    DatabaseError,
    apply,
    connection,
    health,
    inspect,
    migrations,
    provision_runtime,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inspect", "apply", "check", "provision-runtime"])
    parser.add_argument("--migrations", type=Path, default=Path("migrations"))
    args = parser.parse_args()
    variable = "BASELINE_RUNTIME_DSN" if args.operation == "check" else "BASELINE_MIGRATION_DSN"
    try:
        with connection(variable) as conn:
            if args.operation == "check":
                result = health(conn)
                if result["role"] != "baseline_runtime":
                    raise DatabaseError("Connection check did not use baseline_runtime")
                if os.environ.get("BASELINE_DB_LOCAL_TEST") != "1" and not result["tls"]:
                    raise DatabaseError("Hosted connection did not negotiate TLS")
            elif args.operation == "apply":
                result = {"applied": apply(conn, args.migrations)}
            elif args.operation == "inspect":
                result = {
                    "pending": [file.id for file in inspect(conn, migrations(args.migrations))]
                }
            else:
                provision_runtime(conn, os.environ.get("BASELINE_RUNTIME_PASSWORD", ""))
                result = {"runtime_provisioned": True}
        print(json.dumps(result))
        return 0
    except DatabaseError as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
