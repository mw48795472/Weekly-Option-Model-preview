"""Rebuild normalized API definitions from the preserved vendor workbooks."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nh_research.catalog import read_workbook, sha256, compare_specs, semantic_scope, audit_spec, summarize


def build(source_root: Path, output: Path):
    uploaded_path = source_root / "uploaded" / "전체_API_문서.xlsx"
    uploaded = {r["metadata"]["document"]: r for r in read_workbook(uploaded_path)}
    page_manifest_path = source_root / "web_manifest.json"
    pages = json.loads(page_manifest_path.read_text(encoding="utf-8")) if page_manifest_path.exists() else {}
    records, changes, sources = [], [], []
    seen = set()
    for path in sorted((source_root / "individual").rglob("*.xlsx")):
        specs = read_workbook(path)
        if len(specs) != 1:
            raise ValueError(f"Expected one API per downloaded workbook: {path.name}")
        spec = specs[0]
        identifier = spec["metadata"]["document"]
        if identifier in seen:
            raise ValueError(f"Duplicate downloaded document: {identifier}")
        seen.add(identifier)
        relative = path.relative_to(ROOT).as_posix()
        spec["source"] = {"file": relative, "sha256": sha256(path),
                          "page": pages.get(identifier), "retrieved_date_kst": "2026-10-11"}
        spec["scope"] = semantic_scope(spec)
        spec["export_warnings"] = audit_spec(spec)
        records.append(spec)
        sources.append(spec["source"] | {"document": identifier})
        if identifier in uploaded:
            diff = compare_specs(uploaded[identifier], spec)
            if diff:
                changes.append({"document": identifier, "differences": diff})
    missing = sorted(set(uploaded) - seen)
    extra = sorted(seen - set(uploaded))
    definition_changes = sum(any(not d["location"].endswith("_example") for d in c["differences"]) for c in changes)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in {
        "catalog.json": records,
        "source_manifest.json": {"uploaded": {"file": uploaded_path.relative_to(ROOT).as_posix(),
                                              "sha256": sha256(uploaded_path)}, "individual": sources},
        "audit.json": {"summary": summarize(records), "uploaded_api_count": len(uploaded),
                       "missing_individual": missing, "additional_individual": extra,
                       "changed_api_count": len(changes), "definition_changed_api_count": definition_changes,
                       "example_changed_api_count": sum(any(d["location"].endswith("_example") for d in c["differences"]) for c in changes),
                       "differences": changes},
    }.items():
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summarize(records), "missing_individual": missing,
                      "additional_individual": extra, "changed_api_count": len(changes)}, ensure_ascii=False))
    lines = ["# NH선물 API 49종 색인", "", "수집일: 2026-10-11 (KST). 원본 Excel은 바이트 변경 없이 보존했습니다.", "",
             "필드 단위 정의·원본 행 번호는 `data/catalog/catalog.json`, 해시는 `source_manifest.json`, 업로드본 비교는 `audit.json`을 참조합니다.", "",
             "| API | 명칭 | 방식 | 호출 분류 | Excel | 공식 문서 |", "|---|---|---|---|---|---|"]
    for record in records:
        m, source = record["metadata"], record["source"]
        lines.append(f"| `{m['document']}` | {m['name']} | {m['method']} | {m['limit_category']} | "
                     f"[다운로드 원본](../{source['file']}) | [페이지]({source['page']}) |")
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "api-catalog.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if missing:
        raise SystemExit("Some APIs in uploaded workbook are not downloaded individually yet.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=ROOT / "vendor" / "nh" / "2026-10-11")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "catalog")
    args = parser.parse_args()
    build(args.source_root.resolve(), args.output.resolve())
