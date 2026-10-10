"""Offline CLI: inspect local configuration and build redacted market query plans."""
import argparse
import json
import os
from pathlib import Path

from .contracts import market_request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    plan = commands.add_parser("plan")
    plan.add_argument("--catalog", type=Path, default=Path("data/catalog/catalog.json"))
    plan.add_argument("--api", default="domestic/price")
    plan.add_argument("--params", type=Path, required=True)
    plan.add_argument("--environment", choices=["demo", "live"], default="demo")
    args = parser.parse_args()
    if args.command == "doctor":
        result = {"offline_only": True, "configured": {
            name: bool(os.environ.get(name, "").strip())
            for name in ("NH_APPKEY", "NH_APPSECRET")},
            "authenticated_call": "not_attempted"}
    else:
        records = json.loads(args.catalog.read_text(encoding="utf-8"))
        spec = next((r for r in records if r["metadata"]["document"] == args.api), None)
        if spec is None:
            parser.error("API not found in catalog")
        parameters = json.loads(args.params.read_text(encoding="utf-8-sig"))
        request = market_request(spec, parameters, "OFFLINE_PLACEHOLDER", args.environment)
        result = request.public_summary()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
