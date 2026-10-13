"""Read-only frozen single-stock empirical research views."""
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from .empirical_dashboard import show,table_download
PROXIES={'parkinson':'고가·저가 분산 · 주 결과','close_squared_return':'비교불가일 제외 종가수익률 제곱','parkinson_clean':'비교불가일 제외 고가·저가 분산'}
FAMILIES={'matched':'주 검증 · 동일 계약 5일 OI 변화','level':'보조 검증 · 전체 OI 수준'}
MODELS={'HAR_calendar':'HAR + 달력 vs HAR','OI_lag1':'동일 계약 OI · 1일 지연','OI_lag2':'동일 계약 OI · 2일 지연','total_OI_lag1':'전체 체인 변화 · 1일 지연','OI_level_lag1':'전체 OI 수준 · 1일 지연','OI_level_lag2':'전체 OI 수준 · 2일 지연','HAR':'HAR','persistence':'직전 분산 지속'}

@st.cache_data
def load_stocks(root):
 folder=root/'data/analysis/single_stocks'
 names=['coverage','daily_panel','h5_coefficients','h5_diagnostics','h5_cells','h6_forecasts','h6_diagnostics','h6_comparison','h6_scores','price_events','expiry_audit','alias_map']
 return json.loads((folder/'summary.json').read_text(encoding='utf-8')),{name:pd.read_csv(folder/(name+'.csv'),dtype={'stock_code':str}) for name in names}

def interval_chart(frame,label,estimate,title,key):
 fig=go.Figure()
 for _,r in frame.iterrows():fig.add_trace(go.Scatter(x=[r.family_ci_low,r.family_ci_high],y=[r[label],r[label]],mode='lines',line=dict(color='#B2C9D6',width=7),showlegend=False,hovertemplate='다중비교 구간: %{x:.4f}<extra></extra>'))
 for _,r in frame.iterrows():fig.add_trace(go.Scatter(x=[r.ci_low,r.ci_high],y=[r[label],r[label]],mode='lines',line=dict(color='#087F8C',width=2),showlegend=False,hovertemplate='개별 95% 구간: %{x:.4f}<extra></extra>'))
 fig.add_trace(go.Scatter(x=frame[estimate],y=frame[label],mode='markers',marker=dict(color='#087F8C',size=8),showlegend=False))
 fig.add_vline(x=0,line_dash='dash',line_color='#888');fig.update_layout(title=title,xaxis_title='log 분산 계수' if estimate=='coefficient' else '추가모형 − 기준모형 QLIKE (음수 = 개선)');show(fig,key)


def render_single_stocks(root):
 summary,data=load_stocks(root);coverage=data['coverage']
 st.title('개별주식 H5·H6')
 st.caption(f"TAIFEX 주식 위클리옵션 × TWSE 기초주가 · {summary['start']}–{summary['end']} · {summary['version']}")
 st.info('7개 기초주식의 실제 가격·OI 연구입니다. 고가·저가의 일별 분산 대용치를 사용하며 장중 RV, 매매 수익률, 인과효과를 검증한 결과는 아닙니다.')
 labels={r.stock_code:f'{r.name_en} / {r.name_cn} · {r.stock_code} · {r.roster_code}O 계열' for r in coverage.itertuples()}
 sid=st.selectbox('기초주식 · 옵션 상품명',list(labels),format_func=labels.get,key='stock_code')
 c=coverage.loc[coverage.stock_code.eq(sid)].iloc[0];panel=data['daily_panel'].loc[data['daily_panel'].stock_code.eq(sid)].copy()
 cols=st.columns(3);cols[0].metric('기초주가 관측',f"{int(c.price_days)}일");cols[1].metric('상장 후 옵션 이력',f"{int(c.option_days)}일");cols[2].metric('주 H6 테스트',f"{int(c.matched_test_days)}일")
 st.caption(f"위클리 상장 {c.weekly_launch} · 실제 원장 {c.weekly_start}–{c.weekly_end} · 만기 {int(c.weekly_expiry_days)}회. 상장 전 OI는 결측이며 0으로 채우지 않았습니다.")
 view=st.radio('주식 분석 보기',['종목·데이터','H5 만기 검토','H6 예측 검증','비교·다운로드'],horizontal=True,key='stock_view')
 if view=='종목·데이터':
  st.subheader('기초주가와 변동성')
  show(px.line(panel,x='date',y='close',title=labels[sid]+' · 공식 종가',labels={'date':'거래일','close':'주가 (TWD, 수정 전)'}),'stock_price')
  panel['범위 변동성 (%)']=100*np.sqrt(panel.parkinson)
  fig=px.line(panel,x='date',y='범위 변동성 (%)',labels={'date':'거래일'},title='일별 고가·저가 범위와 실제 만기')
  ex=panel.loc[panel.weekly_expiry.eq(1)];fig.add_trace(go.Scatter(x=ex.date,y=ex['범위 변동성 (%)'],mode='markers',name='위클리 만기',marker=dict(color='#C88B37',size=6)));show(fig,'stock_volatility')
  st.warning(f"고가=저가인 {int(c.zero_range_days)}일은 가격 누락과 별도로 기록하고 양의 범위 모형에서 제외했습니다. 이후 22일 과거창·5일 미래창의 가용성에도 영향을 줍니다.")
  st.caption('만기일의 높은 값만으로 만기가 원인이라고 판단할 수 없습니다. 원주가 그래프는 배당·분할을 소급 조정한 총수익률이 아닙니다.')
  st.subheader('OI의 희소성과 계약 구성 변화')
  show(px.line(panel,x='date',y='weekly_oi',labels={'date':'거래일','weekly_oi':'위클리 OI (계약 수)'},title='표준·조정 계약을 별도 ID로 보존한 전체 OI'),'stock_oi')
  st.write(f"동일 계약의 전기 OI 비중 중앙값 **{100*c.matched_coverage_median:.1f}%**, 5일 변화율 미정의 **{int(c.undefined_matched_days)}일**입니다. 분모 0과 신규·만기 소멸을 단순한 유입·유출로 바꾸지 않습니다.")
  events=data['price_events'].query('stock_code == @sid');st.write(f'비교불가·결측·0범위 점검 날짜: {len(events)}개')
  st.dataframe(events,hide_index=True,width='stretch')
  st.caption('TWSE X·주석 및 공표 가격차와 실제 종가차의 불일치를 표시했습니다. 종가수익률 민감도에서는 비교불가일 수익률을 제외합니다. 배당 재투자 수익률은 아닙니다.')
  table_download(panel,'선택 주식 일별 분석 CSV','stock_daily')
  path=root/'data/analysis/single_stocks'/f'{sid}_weekly_contracts.csv.gz';st.download_button('선택 주식 개별 옵션 가격·OI CSV.gz',path.read_bytes(),file_name=path.name,mime='application/gzip',key='stock_contract_download')
 elif view=='H5 만기 검토':
  st.subheader('만기 전후의 조건부 변동성 차이')
  variants={'primary':'장기 주가 표본 · 기본','weekday_by_launch':'요일 × 상장 이후 통제','post_launch_only':'위클리 상장 이후만','exclude_non_comparable':'비교불가일 제외'}
  variant=st.selectbox('H5 모형',list(variants),format_func=variants.get,key='stock_h5_variant');lag=st.selectbox('HAC 시차',[5,20],key='stock_h5_lag')
  d=data['h5_diagnostics'].query('stock_code == @sid and variant == @variant and lags == @lag').iloc[0]
  st.caption(f"관측 {int(d['n'])}일 · 설계행렬 rank {int(d['rank'])}/{int(d['columns'])}")
  coeff=data['h5_coefficients'].query('stock_code == @sid and variant == @variant and lags == @lag').copy()
  terms={'weekly_expiry':'만기 당일','before_weekly_expiry':'직전 거래일','after_weekly_expiry':'직후 거래일'};coeff=coeff.loc[coeff.term.isin(terms)];coeff['구간']=coeff.term.map(terms)
  if coeff.empty:st.warning('요일·월물·위클리 효과를 이 표본에서 각각 분리할 수 없어 계수를 발표하지 않습니다. 임의로 통제를 삭제해 유의한 결과를 만들지 않았습니다.')
  else:
   interval_chart(coeff,'구간','coefficient','H5 · 점추정과 불확실성','stock_h5_chart');st.dataframe(coeff[['구간','coefficient','ci_low','ci_high','family_ci_low','family_ci_high']],hide_index=True,width='stretch')
  st.write('얇은 구간은 개별 95% HAC, 넓은 옅은 구간은 7종목 × 당일·전·후 21개 비교를 고려한 구간입니다. 전체 기간 모형에는 상장 전 주가도 포함되며 상장 이후 여부·요일·자기 과거 변동성·전일 시장 변동성을 통제합니다. 기업별 뉴스와 상장 선정 효과를 제거한 인과 분석은 아닙니다.')
  cells=data['h5_cells'].query('stock_code == @sid');st.dataframe(cells,hide_index=True,width='stretch');st.caption('post_launch=0은 위클리 상장 전, weekday=0~4는 월~금. 달력 효과가 겹치는 정도를 확인하는 표입니다.')
 elif view=='H6 예측 검증':
  st.subheader('OI가 미래 5거래일 분산 예측에 도움이 되는가?')
  family=st.selectbox('H6 검증 종류',list(FAMILIES),format_func=FAMILIES.get,key='stock_family');proxy=st.selectbox('H6 분산 대용치',list(PROXIES),format_func=PROXIES.get,key='stock_proxy');block=st.selectbox('이동블록 길이',[10,5,20],key='stock_block')
  d=data['h6_diagnostics'].query('stock_code == @sid and proxy == @proxy and family == @family').iloc[0]
  st.caption(f"가용 라벨 {int(d.eligible_days)}일 · 최소 훈련 100개 · 테스트 {int(d.test_days)}일 · 새로운 독립 피처 방향 때문에 예측 보류 {int(d.unidentified_forecast_origins)}일")
  losses=data['h6_comparison'].query('stock_code == @sid and proxy == @proxy and family == @family and block == @block').copy()
  if losses.empty:st.warning('최소 100개 완결 훈련 라벨을 충족하는 시간순 테스트를 만들지 못했습니다. 분석 불가를 성과 0으로 표시하지 않습니다.')
  else:
   losses['모형']=losses.model.map(MODELS);interval_chart(losses,'모형','qlike_difference','H6 · 모델별 같은 날짜의 예측 손실 차이','stock_h6_chart')
   primary_model='OI_lag1' if family=='matched' else 'OI_level_lag1';r=losses.loc[losses.model.eq(primary_model)].iloc[0]
   st.write(f"테스트 **{r.test_start}–{r.test_end}, {int(r['n'])}일**. 주 비교 평균 손실차 **{r.qlike_difference:+.5f}**, 개별 95% 구간 **[{r.ci_low:+.5f}, {r.ci_high:+.5f}]**, 7종목 고려 구간 **[{r.family_ci_low:+.5f}, {r.family_ci_high:+.5f}]**.")
   if r['n']<30:st.warning('테스트가 30일 미만인 단기 탐색 결과입니다. 겹치는 미래 라벨과 적은 독립 블록으로 불확실성 추정도 불안정합니다.')
   elif r.family_ci_high<0:st.info('해당 사양·표본에서 개선 신호가 있습니다. 별도 미래 표본에서 재검증하기 전 운영 성능으로 일반화하지 않습니다.')
   else:st.info('이 사양에서는 종목 수를 고려한 구간으로 추가 예측력 개선을 확정할 수 없습니다.')
   pred=data['h6_forecasts'].query('stock_code == @sid and proxy == @proxy and family == @family');pivot=pred.pivot(index='date',columns='model',values='qlike');cum=pd.DataFrame({MODELS[c]:(pivot[c]-pivot.HAR_calendar).cumsum() for c in pivot if c not in ['HAR','HAR_calendar','persistence']}).reset_index()
   show(px.line(cum,x='date',y=list(cum.columns[1:]),labels={'date':'예측일','value':'누적 QLIKE 차이','variable':'모형'},title='구간에 따라 개선이 지속되는가'),'stock_h6_cumulative')
   st.dataframe(data['h6_scores'].query('stock_code == @sid and proxy == @proxy and family == @family'),hide_index=True,width='stretch');table_download(pred,'예측값·실제값·훈련 종료일 CSV','stock_forecasts')
  st.caption('7종목 구간은 대용치·시차·블록을 바꾼 모든 탐색을 보정한 결과가 아닙니다. 민감도의 개선 신호를 주 가설 성공으로 바꾸지 않습니다.')
  st.caption('OI 행의 기준은 HAR + 달력입니다. HAR + 달력 행만 HAR과 비교합니다. 훈련 라벨 종료일 < 예측일; 1·2일 OI 지연은 공표 시각 가정입니다. 주 검증과 보조 검증의 날짜는 다를 수 있어 서로 우승 모델을 고르지 않습니다. QLIKE는 수익률이 아닙니다.')
 else:
  st.subheader('7개 주식의 확보 범위와 검증 가능성')
  cols=['name_en','name_cn','stock_code','weekly_launch','price_days','option_days','weekly_expiry_days','matched_test_days','level_test_days','matched_coverage_median']
  st.dataframe(coverage[cols],hide_index=True,width='stretch')
  st.write('표본 기간과 거래량이 다른 종목의 손실 숫자를 단순 순위로 해석하지 않습니다. 같은 만기일과 시장 충격을 공유하므로 7개를 독립적인 성공 사례로 더하지 않습니다.')
  st.image(str(root/'docs/images/single-stocks/stock_h6.png'))
  table_download(coverage,'7개 주식 분석 범위 CSV','stock_coverage');table_download(data['h6_comparison'],'전체 H6 비교 CSV','stock_all_h6')
  table_download(data['alias_map'],'종목명·조정계약 매핑 CSV','stock_aliases')
  st.dataframe(data['expiry_audit'].loc[data['expiry_audit'].mismatch.eq(True)],hide_index=True,width='stretch')
 with st.expander('전체 보고서·재현·다운로드'):
  st.link_button('개별주식 전체 분석 보고서','https://github.com/mw48795472/Weekly-Option-Model-preview/blob/codex/streamlit-public-deployment/docs/single-stock-analysis.md')
  st.code('python scripts/analyze_single_stocks.py',language='bash')
  p=root/'docs/downloads/single_stock_h5_h6.zip'
  if p.exists():st.download_button('개별주식 CSV·PNG·보고서 ZIP',p.read_bytes(),file_name=p.name,mime='application/zip',key='stock_zip')
