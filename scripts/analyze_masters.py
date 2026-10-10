"""Reproduce descriptive analysis of the downloaded public masters, offline."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nh_research.catalog import sha256
from nh_research.master import load_master, summarize_master, weekly_name_candidate

SOURCE = "https://apidev.futures.co.kr/#/api/info/market-master"


def main():
    source = ROOT / "vendor/nh/2026-10-11/masters"
    output = ROOT / "data/analysis"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    candidates = []
    for path in sorted(source.glob("*.mst.gz")):
        rows = load_master(path)
        summary = summarize_master(rows)
        results.append({"file": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                        "retrieved_date_kst": "2026-10-11", "source_page": SOURCE, **summary})
        candidates += [dict(source_file=path.name, **r) for r in rows if weekly_name_candidate(r)]
    if len(results) != 3:
        raise ValueError("Expected three domestic master files")
    (output / "master_summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["source_file", "cme_tp", "under_name", "series", "real_Code", "opt_tp",
              "exp_ym", "strike_p", "ctrt_size", "rem_cnt", "name_kor"]
    with (output / "weekly_candidates.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
