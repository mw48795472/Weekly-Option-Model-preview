"""Deterministic download of reproducible stock research outputs."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def package():
 output=ROOT/'docs/downloads/single_stock_h5_h6.zip'
 files=sorted((ROOT/'data/analysis/single_stocks').glob('*'))+sorted((ROOT/'docs/images/single-stocks').glob('*.png'))+[ROOT/'docs/single-stock-analysis.md',ROOT/'docs/single-stock-protocol.md',ROOT/'data/source/single_stocks/README.md']
 with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for path in files:
   info=zipfile.ZipInfo(path.relative_to(ROOT).as_posix(),date_time=(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,path.read_bytes())
 print(output.name,output.stat().st_size)
if __name__=='__main__':package()
