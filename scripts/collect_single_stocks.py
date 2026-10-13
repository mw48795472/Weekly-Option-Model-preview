"""Bounded, cached official stock history; two hosts, one serial worker per host."""
from __future__ import annotations
import argparse,calendar,gzip,json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from collect_extended_markets import fetch
ROOT=Path(__file__).resolve().parents[1]
STOCKS=[('CA','1303','Nan Ya Plastics','南亞','2026-02-02'),('CC','2303','UMC','聯電','2026-02-02'),('CD','2330','TSMC','台積電','2025-12-08'),('CZ','2603','Evergreen Marine','長榮','2025-12-08'),('DH','2317','Hon Hai','鴻海','2025-12-08'),('DV','2454','MediaTek','聯發科','2025-12-08'),('DX','3231','Wistron','緯創','2025-12-08')]

def months(start,end):
 cursor=start.replace(day=1)
 while cursor<=end:
  yield max(cursor,start),min(end,date(cursor.year,cursor.month,calendar.monthrange(cursor.year,cursor.month)[1]))
  cursor=date(cursor.year+1,1,1) if cursor.month==12 else date(cursor.year,cursor.month+1,1)

def collect(output):
 start,end=date(2025,1,1),date(2026,10,8)
 def twse():
  entries=[]
  for first,last in months(start,end):
   for code,stock,*_ in STOCKS:
    entries.append(fetch(output,'stock_'+stock+'_'+first.strftime('%Y%m'),'https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?'+urlencode(dict(response='json',date=first.strftime('%Y%m01'),stockNo=stock)),pause=1.5))
  return entries
 def taifex():
  entries=[]
  for first,last in months(date(2025,12,1),end):
   key=first.strftime('%Y%m');fields=dict(queryStartDate=first.strftime('%Y/%m/%d'),queryEndDate=last.strftime('%Y/%m/%d'))
   meta=fetch(output,'catalog_'+key,'https://www.taifex.com.tw/cht/3/getOptcontractDl.do?'+urlencode(fields))
   entries.append(meta)
   if not meta['complete']:raise ValueError('Historical catalog unavailable')
   catalog=json.loads(gzip.decompress((output/meta['file']).read_bytes()))
   lookup={r['marketid'].strip():r for r in catalog['commodityList']}
   for code,stock,en,cn,launch in STOCKS:
    if last<date.fromisoformat(launch):continue
    item=lookup[code]
    entries.append(fetch(output,'options_'+code+'_'+key,'https://www.taifex.com.tw/cht/3/optDataDown',dict(**fields,down_type='1',commodity_id='specialid',commodity_id2=item['marketids'])))
  for code,stock,*_ in STOCKS:
   for year in [2025,2026]:
    entries.append(fetch(output,'settlements_'+code+'_'+str(year),'https://www.taifex.com.tw/cht/5/sSOFSP',dict(down_type='2',stockCode=stock,startYear=str(year),startMonth='01',endYear=str(year),endMonth='12' if year==2025 else '10')))
  return entries
 with ThreadPoolExecutor(max_workers=2) as pool:
  a,b=pool.submit(twse),pool.submit(taifex)
  entries=a.result()+b.result()
 manifest=dict(version='stocks-20261012',start=str(start),end=str(end),stocks=[dict(roster_code=c,stock_code=s,name_en=e,name_cn=n,weekly_launch=l) for c,s,e,n,l in STOCKS],requests=entries)
 (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if any(not e['complete'] for e in entries):raise SystemExit('Incomplete collection: rerun to resume failed requests')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'data/source/single_stocks/20261012');a=p.parse_args();collect(a.output)
