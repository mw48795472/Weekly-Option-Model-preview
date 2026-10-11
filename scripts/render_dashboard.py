"""Build an offline interactive dashboard and PNGs from observed master data."""
from pathlib import Path
import argparse
import html
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from nh_research.master import load_master, weekly_name_candidate
from nh_research.market_analysis import analyze_snapshot


def build(output, snapshot=None):
    output.mkdir(parents=True, exist_ok=True)
    rows = load_master(ROOT / 'vendor/nh/2026-10-11/masters/fut_opt.mst.gz')
    raw = pd.DataFrame([r for r in rows if weekly_name_candidate(r)])
    unique = raw.drop_duplicates('series').copy()
    unique['strike'] = pd.to_numeric(unique.strike_p, errors='coerce')
    unique['expiry'] = pd.to_datetime(unique.exp_ym, format='%Y%m%d').dt.strftime('%Y-%m-%d')
    cards, charts = [], []
    colors = ['#2563eb', '#0d9488', '#e99a20', '#8b5cf6']

    def chart(name, title, groups, kind='bar', xlabel='', ylabel='Contracts', note=''):
        fig = go.Figure()
        static, ax = plt.subplots(figsize=(10, 4.8), layout='constrained')
        for i, (label, xs, ys) in enumerate(groups):
            color = colors[i % len(colors)]
            if kind == 'bar':
                fig.add_trace(go.Bar(name=label, x=list(xs), y=list(ys), marker_color=color))
                # Grouped bars retain the same categories in PNG and HTML.
                import numpy as np
                width = .8 / len(groups)
                positions = np.arange(len(xs)) + (i - (len(groups)-1)/2) * width
                ax.bar(positions, ys, width=width, label=label, color=color)
                ax.set_xticks(range(len(xs)), xs)
            else:
                mode = 'markers' if kind == 'scatter' else 'lines'
                fig.add_trace(go.Scatter(name=label, x=list(xs), y=list(ys), mode=mode,
                                        marker_color=color))
                if kind == 'scatter':
                    ax.scatter(xs, ys, label=label, color=color, s=13, alpha=.55)
                else:
                    ax.plot(xs, ys, label=label, color=color)
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', alpha=.15)
        if len(groups) > 1:
            ax.legend()
        static.savefig(output / (name + '.png'), dpi=160)
        plt.close(static)
        fig.update_layout(template='plotly_white', height=390, margin=dict(l=60,r=25,t=30,b=65),
                          xaxis_title=xlabel, yaxis_title=ylabel, barmode='group',
                          legend=dict(orientation='h', y=1.12))
        if kind == 'bar':
            fig.update_xaxes(type='category')
        charts.append((name, title, fig, note))

    counts = unique.groupby('under_name').size()
    chart('weekly_products', 'Weekly candidates by product', [('Unique series', counts.index, counts.values)],
          note='종목명 기반 후보. 주간·야간의 동일 종목코드는 한 번만 집계합니다.')
    expiry = unique.groupby(['expiry', 'opt_tp']).size().unstack(fill_value=0)
    chart('weekly_expiries', 'Weekly candidates by expiry',
          [({'3':'Call (3)','4':'Put (4)'}.get(str(c),str(c)), expiry.index, expiry[c]) for c in expiry.columns],
          note='고유 종목코드 기준 만기 분포. 마스터의 C/P 종목명과 대조한 구분: 3=콜, 4=풋.')
    chart('strike_coverage', 'Strike coverage by expiry',
          [(u, pd.to_datetime(g.expiry), g.strike) for u,g in unique.groupby('under_name')], kind='scatter', ylabel='Strike',
          note='여러 기초자산이 포함됩니다. 범례를 클릭해 상품별로 비교하세요. 겹치는 콜·풋 점이 있습니다.')
    sessions = raw.groupby(['under_name','cme_tp']).size().unstack(fill_value=0)
    chart('session_coverage', 'Day / night master coverage',
          [(c, sessions.index, sessions[c]) for c in sessions.columns], ylabel='Master rows',
          note='세션별 행 수입니다. 합계는 고유 종목 수가 아니며, 모의 야간 시세 제공 여부를 뜻하지 않습니다.')
    counts_dict = {'master_rows':len(rows), 'weekly_rows':len(raw), 'unique_weekly_series':len(unique),
                   'expiry_count':len(expiry), 'unique_by_product':counts.to_dict(),
                   'unique_by_expiry':unique.groupby('expiry').size().to_dict()}
    cards = [('고유 위클리 후보',len(unique)), ('만기',len(expiry)), ('주간 후보 행',int((raw.cme_tp=='day').sum())),
             ('야간 후보 행',int((raw.cme_tp=='night').sum()))]
    status = '공개 마스터 분석 · 시세 미수집'
    auth_status = '인증 정보 없음'
    market = None
    if snapshot:
        market = analyze_snapshot(snapshot)
        auth_status = snapshot.get('auth',{}).get('status','unknown')
        if any(not market[key].empty for key in ('daily','minute','chain')):
            status = '공개 마스터 + 모의 관측 데이터'
        for key, column, title in [('daily','close','Observed daily close'),
                                    ('daily','rolling_vol_20d','20-observation historical volatility'),
                                    ('minute','close','Observed minute close')]:
            frame = market[key]
            if not frame.empty and frame[column].notna().any():
                chart(key+'_'+column,title,[('Observed', frame.timestamp,frame[column])],kind='line',
                      ylabel=column, note='수집된 관측치만 표시합니다. 누락 구간을 보간하지 않습니다.')
        (output/'market_summary.json').write_text(json.dumps(market['summary'],ensure_ascii=False,indent=2),encoding='utf-8')
    public_summary = {**counts_dict,'snapshot':'2026-10-11','method':'name-based candidates; deduplicated by series',
                      'limitations':['No prices, volume or open interest in this analysis',
                                     'Master is a saved snapshot, not proof of current tradability',
                                     'Day/night reference-date consistency remains unverified']}
    (output/'master_analysis.json').write_text(json.dumps(public_summary,ensure_ascii=False,indent=2),encoding='utf-8')
    unique[['series','under_name','expiry','opt_tp','strike']].to_csv(output/'weekly_contracts.csv',index=False,encoding='utf-8-sig')
    esc = lambda value: html.escape(str(value))
    sections = ''.join(f'<section><h2>{esc(title)}</h2><p>{esc(note)}</p><div id="{name}"></div><a href="{name}.png">PNG 다운로드</a></section>' for name,title,fig,note in charts)
    code = '\n'.join('Plotly.newPlot('+json.dumps(name)+','+fig.to_json().replace('<','\\u003c')+'.data,'+fig.to_json().replace('<','\\u003c')+'.layout,{responsive:true,displaylogo:false});' for name,title,fig,note in charts)
    records = ''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in unique[['series','under_name','expiry','opt_tp','strike']].itertuples(index=False,name=None))
    failures = snapshot.get('failures',[]) if snapshot else []
    failure_text = ' / '.join(dict.fromkeys(f.get('error','') for f in failures))
    if 'EGW016' in failure_text:
        failure_text = '국내 시세조회 권한 확인 대기 (EGW016). 현재가·차트·옵션 시세는 미수집 상태입니다.'
    auth_status = {'authenticated':'모의 인증 성공','not_attempted':'인증 미실행','failed':'인증 실패'}.get(auth_status,auth_status)
    document = '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Weekly Option | NH Research</title><style>
*{box-sizing:border-box}body{margin:0;background:#f2f5fa;color:#17243b;font:16px/1.6 'Malgun Gothic',sans-serif}main{max-width:1250px;margin:auto;padding:35px 24px}header{background:#142a4e;color:white;padding:36px;border-radius:18px}h1{font-size:34px;margin:10px 0}h2{font-size:20px;margin:0}p{color:#5c6c82}header p{color:#c8d8ef}.badge{color:#8de2d0;font-size:13px;letter-spacing:2px}.cards,.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin:24px 0}.cards{grid-template-columns:repeat(4,1fr)}section,.card,.notice{background:white;border-radius:14px;padding:24px;box-shadow:0 3px 20px #142a4e08}.card strong{display:block;font-size:32px}.notice{border-left:4px solid #e99a20;margin-top:24px}.notice p{overflow-wrap:anywhere}a{color:#2563eb}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:9px;border-bottom:1px solid #e7edf5}th{position:sticky;top:0;background:#edf2fa}.tablewrap{max-height:450px;overflow:auto}input{padding:12px;width:100%;margin:16px 0;border:1px solid #b7c5d8;border-radius:7px}footer{padding:24px;color:#63738b}@media(max-width:800px){.grid{grid-template-columns:1fr}.cards{grid-template-columns:repeat(2,1fr)}main{padding:15px}header{padding:24px}h1{font-size:26px}}
</style><main><header><span class="badge">NH FUTURES / RESEARCH NOTEBOOK</span><h1>Weekly Option Observatory</h1><p>공개 종목 마스터로 살펴보는 위클리옵션의 계약 구조</p><div>SNAPSHOT 2026-10-11 · __STATUS__</div></header>
<div class="cards">__CARDS__</div><div class="notice"><h2>데이터 상태와 분석 범위</h2><p>인증: __AUTH__. 가격·거래량·미결제약정이 없는 마스터만으로 수익률, IV, 유동성, 예측 성능을 추정하지 않습니다. 이름 기반 후보이며 현재 거래 가능 종목을 확정한 결과가 아닙니다. 주간·야간 마스터 기준일 정합성도 추가 확인이 필요합니다.</p><p>__FAILURES__</p></div>
<div class="grid">__SECTIONS__</div><section><h2>계약 탐색</h2><p>주간·야간 중복 제거 · <a href="weekly_contracts.csv">CSV 다운로드</a> · <a href="master_analysis.json">분석 JSON</a></p><input id="search" aria-label="계약 검색" placeholder="상품 코드, 만기 또는 종목코드 검색"><div class="tablewrap"><table><thead><tr><th>종목코드</th><th>상품</th><th>만기</th><th>옵션 구분</th><th>행사가</th></tr></thead><tbody>__ROWS__</tbody></table></div></section><footer>출처: NH선물 공개 지수선물옵션 마스터 · 추정·합성 시세 없음 · 모델 성능 평가 미실시</footer></main><script>__PLOTLY__</script><script>__CODE__
document.getElementById('search').addEventListener('input',function(){const q=this.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script></html>'''
    for key,value in {'STATUS':esc(status),'CARDS':''.join(f'<div class="card">{esc(k)}<strong>{v:,}</strong></div>' for k,v in cards),
                      'AUTH':esc(auth_status),'FAILURES':esc(failure_text),'SECTIONS':sections,'ROWS':records,
                      'PLOTLY':get_plotlyjs(),'CODE':code}.items():
        document = document.replace('__'+key+'__',value)
    (output/'index.html').write_text(document,encoding='utf-8')
    print(json.dumps(public_summary,ensure_ascii=False))
    return public_summary


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/private/dashboard')
    parser.add_argument('--snapshot',type=Path)
    args=parser.parse_args()
    snapshot=json.loads(args.snapshot.read_text(encoding='utf-8')) if args.snapshot else None
    build(args.output,snapshot)
