"""Record research-source provenance without copying personal source documents."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    digest_to_files = {}
    for path in sorted(args.source.iterdir()):
        if path.is_file() and not path.name.startswith("~$"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            digest_to_files.setdefault(digest, []).append(path.name)
            rows.append({"name": path.name, "extension": path.suffix, "bytes": path.stat().st_size,
                         "sha256": digest})
    members = []
    for path in sorted(args.source.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                if not entry.is_dir():
                    digest = hashlib.sha256(archive.read(entry)).hexdigest()
                    members.append({"archive": path.name, "sha256": digest,
                                    "byte_identical_to": digest_to_files.get(digest, [])})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"source_label": "Weekly Option", "files": rows,
                                       "zip_members": members}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {len(rows)} source files and {len(members)} ZIP members; no originals copied.")


if __name__ == "__main__":
    main()
