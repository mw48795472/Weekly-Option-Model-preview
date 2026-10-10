"""Read vendor workbooks as data; never execute formulas or embedded examples."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import openpyxl

META = {
    "문서명": "document", "API 통신 방식": "transport", "API 명": "name",
    "HTTP Method": "method", "Content-Type": "content_type",
    "실전 Domain": "live_domain", "모의 Domain": "demo_domain",
    "URL 명": "path", "설명": "description", "API 요청 제한": "limit_category",
}
FIELD_KEYS = ["parent", "key", "label", "type", "length", "meta_type",
              "array_length", "sample", "description", "requirement", "default"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_workbook(path: Path) -> list[dict]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    records = []
    try:
        for sheet in workbook:
            record = {"sheet": sheet.title, "metadata": {}, "input": [], "output": []}
            section = None
            example = None
            for number, raw in enumerate(sheet.iter_rows(values_only=True), 1):
                row = list(raw) + [None] * max(0, 11 - len(raw))
                first = row[0]
                if isinstance(first, str) and first in META and section is None:
                    record["metadata"][META[first]] = row[1]
                elif first in ("INPUT", "OUTPUT"):
                    section = first.lower()
                    example = None
                elif first in ("Request JSON (Input)", "Response JSON (Output)"):
                    section = None
                    example = "request_example" if first.startswith("Request") else "response_example"
                elif example and first is not None:
                    # Keep text as text, including invalid/flattened vendor examples.
                    record[example] = first
                    example = None
                elif section and row[1] not in (None, "Key"):
                    field = dict(zip(FIELD_KEYS, row[:11]))
                    field["row"] = number
                    record[section].append(field)
            if "document" in record["metadata"]:
                records.append(record)
    finally:
        workbook.close()
    return records


def compare_specs(left: dict, right: dict) -> list[dict]:
    """Compare semantic data, ignoring export row offsets and sheet navigation."""
    differences = []
    for key in sorted(set(left["metadata"]) | set(right["metadata"])):
        a, b = left["metadata"].get(key), right["metadata"].get(key)
        if a != b:
            differences.append({"location": f"metadata.{key}", "uploaded": a, "downloaded": b})
    for section in ("input", "output"):
        def indexed(spec):
            result = {}
            for field in spec[section]:
                key = (field.get("parent") or "", field["key"])
                if key in result:
                    raise ValueError(f"Duplicate {section} field {key}")
                result[key] = {k: v for k, v in field.items() if k != "row"}
            return result
        a, b = indexed(left), indexed(right)
        for key in sorted(set(a) | set(b)):
            if a.get(key) != b.get(key):
                differences.append({"location": f"{section}.{key[0]}.{key[1]}",
                                    "uploaded": a.get(key), "downloaded": b.get(key)})
    for key in ("request_example", "response_example"):
        a, b = left.get(key), right.get(key)
        try:
            a = json.loads(a) if isinstance(a, str) else a
            b = json.loads(b) if isinstance(b, str) else b
        except (ValueError, TypeError):
            pass
        if a != b:
            differences.append({"location": key, "uploaded": a, "downloaded": b})
    return differences


def semantic_scope(spec: dict) -> str:
    name = spec["metadata"]["name"] or ""
    document = spec["metadata"]["document"]
    if document in ("token", "revoke", "web-socket-key"):
        return "authentication"
    if any(term in name for term in ("주문", "정정", "취소", "잔고", "예수금", "누적손익", "매도미청산", "보유포지션")):
        return "account_or_order"
    return "market_data"


def audit_spec(spec: dict) -> list[str]:
    issues = []
    if not spec["metadata"].get("content_type") and spec["metadata"].get("method") == "POST":
        issues.append("Export omits Content-Type; verify rendered HTTP headers.")
    output = spec["output"]
    try:
        sample = json.loads(spec.get("response_example", "{}"))
        for field in output:
            if "Array[" in str(field.get("description")) and not isinstance(sample.get(field["key"]), list):
                issues.append(f"{field['key']} is documented as an array but the example is not an array.")
    except (ValueError, TypeError, AttributeError):
        pass
    if spec["metadata"].get("document") == "token":
        issues.append("Token Content-Type requires form encoding despite the JSON-shaped request example.")
    if spec["metadata"].get("transport") == "WEBSOCKET":
        issues.append("Use metadata ws-stream URL; exported handshake example uses a different path.")
    if any(f.get("parent") for f in output):
        try:
            sample = json.loads(spec.get("response_example", "{}"))
            parents = {f["parent"] for f in output if f.get("parent")}
            if any(not isinstance(sample.get(parent), (list, dict)) for parent in parents):
                issues.append("Exported response example flattens documented objects/arrays.")
        except (ValueError, TypeError):
            issues.append("Response example is not valid JSON.")
    return issues


def summarize(records: list[dict]) -> dict:
    return {
        "api_count": len(records),
        "transports": dict(Counter(r["metadata"]["transport"] for r in records)),
        "methods": dict(Counter(r["metadata"]["method"] for r in records)),
        "scopes": dict(Counter(semantic_scope(r) for r in records)),
        "input_fields": sum(len(r["input"]) for r in records),
        "output_fields": sum(len(r["output"]) for r in records),
        "apis_with_export_warnings": sum(bool(audit_spec(r)) for r in records),
    }
