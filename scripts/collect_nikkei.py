"""Audit Nikkei availability without inventing a TAIFEX product.
Default downloads TAIFEX product evidence only. Optional Nikkei/JPX files stay private.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from collect_extended_markets import fetch
ROOT=Path(__file__).resolve().parents[1]

def collect(output,private=False):
 entries=[]
 for name,url in [('DailyMarketReportFut','https://openapi.taifex.com.tw/v1/DailyMarketReportFut'),('IndexFuturesAndOptionsMargining','https://openapi.taifex.com.tw/v1/IndexFuturesAndOptionsMargining')]:
  meta=fetch(output,name,url,pause=1.5)
  if not meta.get('complete'):
   private_failure=ROOT/'data/private/nikkei/20261013';private_failure.mkdir(parents=True,exist_ok=True)
   (private_failure/(name+'_failure.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
   meta['error_class']=str(meta.get('error','UnknownError')).split(':',1)[0]
   meta['error']='Request failed before a validated response; details retained privately'
   (output/(name+'.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  entries.append(meta)
 (output/'manifest.json').write_text(json.dumps(dict(version='nikkei-audit-20261013',requests=entries),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if any(not e['complete'] for e in entries):raise SystemExit('Incomplete TAIFEX audit')
 if private:
  folder=ROOT/'data/private/nikkei/20261013'
  entries=[]
  for name,url in [('nikkei_download_page','https://indexes.nikkei.co.jp/en/nkave/index?type=download'),('jpx_option_page','https://www.jpx.co.jp/english/markets/derivatives/option-price/index.html')]:
   entries.append(fetch(folder,name,url,pause=1.5))
  (folder/'manifest.json').write_text(json.dumps(dict(version='nikkei-private-20261013',requests=entries),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'data/source/nikkei/20261013');p.add_argument('--private-inspection',action='store_true');a=p.parse_args();collect(a.output,a.private_inspection)
