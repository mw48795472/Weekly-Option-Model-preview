"""Explicit, bounded, read-only TAIFEX collection. Never called by the dashboard."""
from __future__ import annotations
import argparse
import calendar
from datetime import date, datetime, timezone, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nh_research.taifex import API_NAMES, BASE_URL, decode_response

DEFAULT_APIS = [n for n in API_NAMES if n != "OptionsTimeAndSalesData"]


def collect(output, start=None, end=None, products=None, include_ticks=False, max_bytes=40_000_000):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new, empty output directory; previous snapshots are immutable")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"provider": "TAIFEX", "authentication": "none", "checked_date_kst": datetime.now(timezone(timedelta(hours=9))).date().isoformat(), "history_requested_start": start, "history_requested_end": end, "requests": []}
    def fetch(name, url, fields=None, object_response=False):
        meta = dict(name=name, url=url, method="POST" if fields is not None else "GET",
                    retrieved_at=datetime.now(timezone.utc).isoformat(), complete=False)
        if fields is not None:
            meta["request_fields"] = fields
        try:
            request = Request(url, data=urlencode(fields).encode() if fields is not None else None,
                              headers={"User-Agent": "WeeklyOptionResearch/0.1",
                                       "Content-Type": "application/x-www-form-urlencoded"})
            with urlopen(request, timeout=30) as response:
                meta["status"] = response.status
                meta["content_type"] = response.headers.get("Content-Type")
                raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ValueError(f"Response exceeds configured limit {max_bytes}")
            data, fmt = (json.loads(raw), "json") if object_response else decode_response(raw)
            meta.update(format=fmt, bytes=len(raw),
                        sha256=hashlib.sha256(raw).hexdigest(),
                        file=name+".raw.gz")
            if isinstance(data, list):
                meta["rows"] = len(data)
            (output/meta["file"]).write_bytes(gzip.compress(raw, mtime=0))
            meta["complete"] = True
            return data
        except Exception as exc:
            meta["error"] = f"{type(exc).__name__}: {exc}"
            return None
        finally:
            manifest["requests"].append(meta)
            (output/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            print(json.dumps(meta, ensure_ascii=False), flush=True)
    fetch("swagger", "https://openapi.taifex.com.tw/swagger.json", object_response=True)
    for name in DEFAULT_APIS + (["OptionsTimeAndSalesData"] if include_ticks else []):
        fetch(name, BASE_URL+"/"+name)
    if start:
        fields = {"queryStartDate": start.replace("-", "/"), "queryEndDate": end.replace("-", "/")}
        catalog = fetch("history_contracts", "https://www.taifex.com.tw/cht/3/getOptcontractDl.do?"+urlencode(fields), object_response=True)
        if not catalog:
            raise ValueError("Historical product catalog unavailable")
        lookup = {r["marketid"].strip(): r for r in catalog["commodityList"]}
        for code in products:
            if code not in lookup:
                raise ValueError(f"Product not in official historical catalog: {code}")
            item = lookup[code]
            fetch("history_"+code, "https://www.taifex.com.tw/cht/3/optDataDown",
                  {**fields, "down_type": "1",
                   "commodity_id": "specialid" if item["flag"] == 1 else code,
                   "commodity_id2": item["marketids"] if item["flag"] == 1 else ""})
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", help="YYYY-MM-DD, historical CSV path (not an OpenAPI query)")
    parser.add_argument("--end", help="YYYY-MM-DD, at most one calendar month after start")
    parser.add_argument("--products", default="CA,CC,CD,CZ,DH,DV,DX,TXO")
    parser.add_argument("--include-ticks", action="store_true", help="Large optional response; excluded by default")
    parser.add_argument("--max-bytes", type=int, default=40_000_000)
    args = parser.parse_args()
    if bool(args.start) != bool(args.end):
        parser.error("--start and --end must be supplied together")
    if args.max_bytes <= 0:
        parser.error("--max-bytes must be positive")
    if args.start:
        begin, finish = date.fromisoformat(args.start), date.fromisoformat(args.end)
        y, m = (begin.year+1, 1) if begin.month == 12 else (begin.year, begin.month+1)
        limit = date(y, m, min(begin.day, calendar.monthrange(y,m)[1]))
        if not begin <= finish <= limit:
            parser.error("Historical interval must fit within one calendar month")
    result = collect(args.output, args.start, args.end, args.products.split(","), args.include_ticks, args.max_bytes)
    if any(not r["complete"] for r in result["requests"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
