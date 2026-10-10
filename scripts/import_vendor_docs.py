"""Copy vendor exports without altering bytes; paths are supplied explicitly."""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nh_research.catalog import read_workbook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uploaded", type=Path, required=True)
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    expected = {r["metadata"]["document"] for r in read_workbook(args.uploaded)}
    candidates = {}
    for path in args.downloads.glob("*API 명세포맷정보*.xlsx"):
        records = read_workbook(path)
        if len(records) != 1:
            continue
        record = records[0]
        identifier = record["metadata"]["document"]
        if identifier in expected and (identifier not in candidates or
                path.stat().st_mtime_ns > candidates[identifier][0].stat().st_mtime_ns):
            candidates[identifier] = (path, record)
    if expected - candidates.keys():
        raise SystemExit(f"Missing exports: {sorted(expected - candidates.keys())}")
    uploaded = args.destination / "uploaded"
    uploaded.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.uploaded, uploaded / "전체_API_문서.xlsx")
    for identifier, (source, record) in candidates.items():
        group = (identifier.split("/")[0] if "/" in identifier else
                 "auth" if identifier in {"token", "revoke", "web-socket-key"} else "websocket")
        target = args.destination / "individual" / group / (record["sheet"] + ".xlsx")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f"Copied {len(candidates)} individual API exports and one uploaded workbook.")


if __name__ == "__main__":
    main()
