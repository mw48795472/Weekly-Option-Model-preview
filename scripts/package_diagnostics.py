"""Bundle public diagnostic results only; no private Nikkei price files."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'reports/H5 H6 불확실성과 닛케이 확장.md'
DIRECTORIES = [
    'data/analysis/h5_diagnostics', 'data/analysis/h6_diagnostics',
    'data/analysis/nikkei', 'data/analysis/research_diagnostics',
    'docs/images/h5_diagnostics', 'docs/images/h6_diagnostics', 'docs/images/nikkei',
]


def build():
    if not REPORT.exists():
        raise FileNotFoundError(REPORT)
    paths = [REPORT]
    for directory in DIRECTORIES:
        folder = ROOT / directory
        paths.extend(p for p in folder.rglob('*') if p.is_file() and p.suffix in {'.csv', '.json', '.png'})
    paths = sorted(set(paths))
    output = ROOT / 'docs/downloads/h5_h6_diagnostics.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            name = path.relative_to(ROOT).as_posix()
            payload = path.read_bytes()
            if path.suffix in {'.csv', '.json', '.md'}:
                payload = payload.replace(b'\r\n', b'\n')
            item = zipfile.ZipInfo(name, date_time=(2026, 10, 13, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            archive.writestr(item, payload)
            records.append(dict(path=name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))
    index = dict(package=output.name, bytes=output.stat().st_size,
                 sha256=hashlib.sha256(output.read_bytes()).hexdigest(), files=records,
                 scope='Public derived diagnostics and metadata; no private source prices or credentials')
    output.with_suffix('.manifest.json').write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in index.items() if k != 'files'}, ensure_ascii=False))
    return index


if __name__ == '__main__':
    build()
