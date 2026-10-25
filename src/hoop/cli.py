"""Thin operation entry points shared with learning notebooks."""

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed")
    seed.add_argument("--source", required=True, type=Path)
    seed.add_argument("--manifest", required=True, type=Path)
    seed.add_argument("--archive", required=True, type=Path)
    seed.add_argument("--season", default="2025-26")
    seed.add_argument("--inventory", type=Path)
    seed.add_argument("--repair", action="append", type=Path, default=[])
    args = parser.parse_args()
    from hoop.domains.nba.sources.seed import build_seed

    report = build_seed(
        args.source,
        json.loads(args.manifest.read_text(encoding="utf-8")),
        args.archive,
        season=args.season,
        inventory=json.loads(args.inventory.read_text(encoding="utf-8"))
        if args.inventory
        else None,
        repair_paths=tuple(args.repair),
    )
    print(
        json.dumps(
            {
                "unit_id": report["unit_id"],
                "reused": report["reused"],
                "rows": report["row_counts"],
                "quarantine": len(report["quarantine"]),
                "seed_status": report["seed_status"],
            }
        )
    )
    return 0 if report["seed_status"] == "candidate_pending_owner_acceptance" else 1


if __name__ == "__main__":
    raise SystemExit(main())
