"""Collect bounded official TAIFEX/TWSE history.
No credentials. Network is explicit, cached and paced; never run from Streamlit.
"""
from __future__ import annotations
import argparse, calendar, gzip, hashlib, json, time
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

def fetch(out, name, url, fields=None, pause=1.0):
    out.mkdir(parents=True, exist_ok=True)
    meta_file = out/(name+".json")
    if meta_file.exists():
        meta=json.loads(meta_file.read_text(encoding="utf-8"))
        if meta.get("complete"):
            if meta["url"]!=url or meta.get("request_fields")!=fields:
                raise ValueError("Cached request differs: use a new output directory")
            raw=gzip.decompress((out/meta["file"]).read_bytes())
            if hashlib.sha256(raw).hexdigest()!=meta["sha256"]: raise ValueError("Cache hash mismatch")
            return meta
    meta=dict(name=name,url=url,method="POST" if fields else "GET",request_fields=fields,
              retrieved_at=datetime.now(timezone.utc).isoformat(),complete=False)
    try:
        request=Request(url,data=urlencode(fields).encode() if fields else None,
                        headers={"User-Agent":"WeeklyOptionResearch/0.2",
                                 "Content-Type":"application/x-www-form-urlencoded"})
        with urlopen(request,timeout=50) as response:
            raw=response.read(40_000_001)
            meta.update(status=response.status,content_type=response.headers.get("Content-Type"))
        if len(raw)>40_000_000: raise ValueError("Response limit exceeded")
        meta.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),file=name+".raw.gz",complete=True)
        (out/meta["file"]).write_bytes(gzip.compress(raw,mtime=0))
    except Exception as exc:
        meta["error"]=f"{type(exc).__name__}: {exc}"
    meta_file.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(name,meta.get("status"),meta.get("bytes"),meta.get("error",""),flush=True)
    time.sleep(pause)
    return meta

def collect_taiwan(out, start, end):
    entries=[]
    cursor=start.replace(day=1)
    while cursor<=end:
        last=min(date(cursor.year,cursor.month,calendar.monthrange(cursor.year,cursor.month)[1]),end)
        first=max(cursor,start)
        key=cursor.strftime("%Y%m")
        entries.append(fetch(out,"txo_"+key,"https://www.taifex.com.tw/cht/3/optDataDown",
            {"queryStartDate":first.strftime("%Y/%m/%d"),"queryEndDate":last.strftime("%Y/%m/%d"),
             "down_type":"1","commodity_id":"TXO","commodity_id2":""}))
        entries.append(fetch(out,"taiex_"+key,"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?"+urlencode({"response":"json","date":cursor.strftime("%Y%m%d")})))
        cursor=date(cursor.year+1,1,1) if cursor.month==12 else date(cursor.year,cursor.month+1,1)
    for year in range(start.year,end.year+1):
        entries.append(fetch(out,"settlements_"+str(year),"https://www.taifex.com.tw/cht/5/optIndxFSP?"+urlencode(
            {"commodityIds":"2","start_year":year,"start_month":"01","end_year":year,"end_month":"12"})))
    return entries

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market",choices=["taiwan"],required=True)
    p.add_argument("--start",required=True);p.add_argument("--end",required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();start=date.fromisoformat(args.start);end=date.fromisoformat(args.end)
    if not start<=end<date.today(): p.error("Use completed dates only")
    if (end-start).days>800: p.error("At most 800 calendar days per explicit collection")
    entries=collect_taiwan(args.output,start,end)
    manifest=dict(market=args.market,start=str(start),end=str(end),requests=entries)
    (args.output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.market=="taiwan" and any(not r["complete"] for r in entries): raise SystemExit(1)
if __name__=="__main__": main()
