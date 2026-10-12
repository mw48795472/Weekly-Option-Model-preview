"""Build a deterministic downloadable empirical evidence package, without private data."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def build():
    files=sorted((ROOT/"data/analysis/empirical").glob("*"))
    files+=sorted((ROOT/"docs/images/empirical").glob("*.png"))
    files += [ROOT/"docs/empirical-analysis.md",ROOT/"docs/empirical-protocol.md",
              ROOT/"data/source/extended_taiwan/README.md"]
    path=ROOT/"docs/downloads/empirical_h5_h6.zip"
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in files:
            if not file.is_file():raise ValueError("Missing package input: "+str(file))
            info=zipfile.ZipInfo(file.relative_to(ROOT).as_posix(),(2026,10,12,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,file.read_bytes())
    print(path.name,path.stat().st_size)
if __name__=="__main__":build()
