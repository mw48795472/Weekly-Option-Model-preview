"""Export a self-contained proposal-driven research PoC; no API access."""
from pathlib import Path
import argparse
import json
import sys
import base64

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nh_research.master import load_master, weekly_name_candidate
from plotly.offline import get_plotlyjs
import pandas as pd


def build(output=None):
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
    template=template.replace('__PLOTLY__',get_plotlyjs())
    output=Path(output) if output is not None else ROOT/'artifacts/private/dashboard/weekly_option_poc.html'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(template,encoding='utf-8')
    print(json.dumps({'html':str(output),'bytes':output.stat().st_size,'actual_data':data},ensure_ascii=False))
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Export path; defaults to the local dashboard directory.')
    build(parser.parse_args().output)
