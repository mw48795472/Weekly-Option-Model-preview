"""Export a self-contained proposal-driven research PoC; no API access."""
from pathlib import Path
import argparse
import json
import sys
import base64
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nh_research.master import load_master, weekly_name_candidate
from nh_research.contract_exports import export_contracts
from plotly.offline import get_plotlyjs
import pandas as pd


def build(output=None, zip_archive=False):
    rows=[r for r in load_master(ROOT/'vendor/nh/2026-10-11/masters/fut_opt.mst.gz') if weekly_name_candidate(r)]
    raw=pd.DataFrame(rows)
    unique=raw.drop_duplicates('series')
    products=sorted(unique.under_name.unique())
    expiries=sorted(unique.exp_ym.unique())
    matrix=[[int(((unique.under_name==p)&(unique.exp_ym==e)).sum()) for e in expiries] for p in products]
    coverage=[]
    for p in products:
        group=raw[raw.under_name==p]
        day=set(group[group.cme_tp=='day'].series)
        night=set(group[group.cme_tp=='night'].series)
        coverage.append({'product':p,'both':len(day&night),'day_only':len(day-night),'night_only':len(night-day)})
    data={'products':products,'expiries':[pd.to_datetime(e).strftime('%Y-%m-%d (%a)') for e in expiries],
          'matrix':matrix,'coverage':coverage}
    template=(ROOT/'templates/research_poc.html').read_text(encoding='utf-8')
    for name in ('weekly_products','weekly_expiries','strike_coverage','session_coverage'):
        payload=base64.b64encode((ROOT/'docs/images'/f'{name}.png').read_bytes()).decode()
        template=template.replace('__'+name.upper()+'__','data:image/png;base64,'+payload)
    template=template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c'))
    details=export_contracts(ROOT)
    archive=details.pop('archive')
    template=template.replace('__CONTRACT_DATA__',json.dumps(details,ensure_ascii=False).replace('<','\\u003c'))
    template=template.replace('__CSV_ZIP__',base64.b64encode(archive.read_bytes()).decode())
    template=template.replace('__PLOTLY__',get_plotlyjs())
    output=Path(output) if output is not None else ROOT/'artifacts/private/dashboard/weekly_option_poc.html'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(template,encoding='utf-8')
    if zip_archive:
        info=zipfile.ZipInfo('weekly_option_poc.html',date_time=(2026,10,11,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(output.with_suffix('.zip'),'w') as archive:
            archive.writestr(info,output.read_bytes())
    print(json.dumps({'html':str(output),'bytes':output.stat().st_size,'actual_data':data},ensure_ascii=False))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Export path; defaults to the local dashboard directory.')
    parser.add_argument('--zip',action='store_true',help='Also package the single HTML file for direct download.')
    args=parser.parse_args()
    build(args.output,args.zip)
