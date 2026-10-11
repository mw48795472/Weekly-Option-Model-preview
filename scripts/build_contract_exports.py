"""Export the preserved master into auditable contract CSVs and a download ZIP."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from nh_research.contract_exports import export_contracts

if __name__ == '__main__':
    result = export_contracts(ROOT)
    print(json.dumps(result['stats'],ensure_ascii=False,indent=2))
    print(result['archive'])
