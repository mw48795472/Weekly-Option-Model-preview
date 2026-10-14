"""Build public Nikkei readiness evidence; optional licensed cash CSV stays private."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from nh_research.nikkei import readiness,status_table,required_data,parse_cash_prices,cash_baseline,api_routes

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--prices',type=Path,help='User-supplied normalized, lawfully usable Nikkei cash CSV')
 p.add_argument('--identity',choices=['NIKKEI225_CASH'])
 args=p.parse_args()
 out=ROOT/'data/analysis/nikkei';out.mkdir(parents=True,exist_ok=True)
 (out/'summary.json').write_text(json.dumps(readiness(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 api_routes().to_csv(out/'api_routes.csv',index=False,encoding='utf-8-sig',lineterminator='\n')
 status_table().to_csv(out/'status.csv',index=False,encoding='utf-8-sig',lineterminator='\n')
 required_data().to_csv(out/'required_data.csv',index=False,encoding='utf-8-sig',lineterminator='\n')
 if args.prices:
  if not args.identity:p.error('--identity NIKKEI225_CASH is required')
  data,summary=cash_baseline(parse_cash_prices(args.prices.read_bytes(),args.identity))
  private=ROOT/'data/private/nikkei/local_analysis';private.mkdir(parents=True,exist_ok=True)
  data.to_csv(private/'cash_baseline.csv',index=False,encoding='utf-8-sig',lineterminator='\n')
  (private/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Public readiness updated. H5/H6 not executed; no Nikkei market rows published.')
if __name__=='__main__':main()
