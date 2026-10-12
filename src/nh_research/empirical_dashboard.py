"""Streamlit views for frozen empirical daily-proxy research; no network or credentials."""
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

LABELS={"persistence":"직전 상태","HAR":"HAR 형태 기준","HAR_calendar":"HAR + 달력",
        "HAR_calendar_OI_lag1":"동일 계약 OI · 1일 지연",
        "HAR_calendar_OI_lag2":"동일 계약 OI · 2일 지연",
        "HAR_calendar_totalOI_lag1":"전체 체인 OI · 1일 지연"}
PROXIES={"parkinson":"고가·저가 Parkinson 분산 (주 결과)",
         "close_squared_return":"종가 수익률 제곱 (민감도)"}

@st.cache_data
def load_empirical(root):
    directory=root/"data/analysis/empirical"
    names=["daily_panel","h5_coefficients","h5_design_diagnostics","h5_weekday_comparison",
           "h6_forecasts","h6_scores","h6_loss_comparison","expiry_schedule_audit"]
    return (json.loads((directory/"summary.json").read_text(encoding="utf-8")),
            {n:pd.read_csv(directory/(n+".csv")) for n in names})

def show(fig,key):
    fig.update_layout(template="plotly_white",height=390,margin=dict(l=12,r=16,t=45,b=30),
                      font=dict(color="#344B63"),legend=dict(orientation="h",y=-.25))
    st.plotly_chart(fig,width="stretch",key=key,config={"displaylogo":False,
        "toImageButtonOptions":{"format":"png","filename":key,"scale":2}})

def table_download(frame,label,key):
    st.download_button(label,frame.to_csv(index=False).encode("utf-8-sig"),
                       file_name=key+".csv",mime="text/csv",key=key)

def render_empirical(root):
    summary,data=load_empirical(root)
    panel=data["daily_panel"]
    st.title("H5·H6 실측 연구")
    st.caption(f"TAIFEX TXO × TWSE TAIEX · {summary['start']}–{summary['end']} · 수집 2026-10-12 · {summary['version']}")
    st.info("실제 옵션 OI와 기초지수 일별 가격으로 검증했습니다. 결과 변수는 일별 고가·저가의 분산 대용치이며 장중 실현변동성(RV)이 아닙니다.")
    cols=st.columns(3)
    cols[0].metric("기초자산 거래일",f"{summary['trading_days']:,}",f"기존 {summary['previous_trading_days']}일에서 확대")
    cols[1].metric("위클리 만기일",str(summary["weekly_expiry_days"]))
    cols[2].metric("시간순 테스트",f"{summary['test_days']}일")
    st.write("**현재 판단:** H5 만기 효과와 H6 OI의 추가 예측력 모두 확정할 근거가 부족합니다. 점추정치와 불확실성, 계약 구성 변화, 시각 가정을 함께 확인하세요.")
    view=st.radio("실측 분석 보기",["기초자산·데이터","H5 만기 검토","H6 예측 검증","HKEX 확보 현황"],horizontal=True,key="empirical_view")
    if view=="기초자산·데이터":
        st.subheader("가격 경로와 실제 만기")
        st.write(f"정규장 위클리 {summary['regular_weekly_rows']:,}행, 고유 계약 {summary['unique_weekly_contracts']:,}개를 거래일 단위로 합쳤습니다. 164만 계약·세션 행을 독립적인 현물 수익률 표본으로 세지 않습니다.")
        prices=panel.copy()
        prices["일별 범위 변동성 (%)"]=100*np.sqrt(prices.parkinson)
        show(px.line(prices,x="date",y="close",labels={"date":"거래일","close":"TAIEX 지수"},title="공식 기초자산 종가"),"empirical_underlying")
        fig=px.line(prices,x="date",y="일별 범위 변동성 (%)",labels={"date":"거래일"},title="고가·저가 기반 일별 변동성 대용치")
        exp=prices.loc[prices.weekly_expiry.eq(1)]
        fig.add_trace(go.Scatter(x=exp.date,y=exp["일별 범위 변동성 (%)"],mode="markers",name="실제 위클리 만기",marker=dict(color="#C88B37",size=5)))
        show(fig,"empirical_range")
        st.caption("선이 높을수록 당일 고가·저가 범위가 넓었습니다. 주황색 만기일과 높은 값이 겹치는 것만으로 만기의 인과효과가 입증되지는 않습니다.")
        st.subheader("OI 변화율의 표본 범위")
        st.write("5거래일 전과 오늘 모두 관측된 계약끼리 합계를 비교합니다. 신규 상장과 만기 소멸을 제외하는 대신, 전체 시장의 작은 일부만 남을 수 있습니다.")
        coverage=panel.assign(동일계약_전기OI비중=panel.continuing_previous_coverage*100)
        show(px.line(coverage,x="date",y="동일계약_전기OI비중",labels={"date":"거래일","동일계약_전기OI비중":"전기 OI 대비 비중 (%)"},title="계속 존재한 계약의 전기 OI 비중"),"empirical_oi_coverage")
        st.warning(f"동일 계약의 전기 OI 비중 중앙값은 {100*panel.continuing_previous_coverage.median():.1f}%입니다. 5일 변화율 {int(panel.oi_matched_5d.isna().sum())}일은 워밍업 또는 분모 0으로 정의되지 않습니다. 이 날짜를 0으로 채우지 않았습니다.")
        st.write("예정 만기와 실제 최종결제일이 다른 사례는 아래와 같습니다. 실제 결제일로 설명 분석을 수행했지만 당시 공지 판본을 복원한 운영 백테스트는 아닙니다.")
        st.dataframe(data["expiry_schedule_audit"],hide_index=True,width="stretch")
        table_download(panel,"결합 일별 데이터 CSV","empirical_daily_panel")
        path=root/"data/analysis/empirical/txo_weekly_history.csv.gz"
        st.download_button("확장 TXO 개별 계약 이력 CSV.gz",path.read_bytes(),file_name=path.name,mime="application/gzip")
    elif view=="H5 만기 검토":
        st.subheader("만기 전후 변동성이 높은가?")
        st.write("일별 Parkinson 분산의 로그를 과거 변동성·요일·금요일 위클리 도입기간·월물만기와 함께 회귀했습니다. 계수가 0보다 높으면 조건부 범위 분산이 큰 방향이며, 가로선은 HAC 95% 구간입니다.")
        variants={"primary":"기본 모형","weekday_by_regime":"요일 × 도입기간 통제","exclude_monthly":"월물만기 제외","placebo_shift2":"2세션 이동 위약 달력"}
        variant=st.selectbox("설명 모형",list(variants),format_func=variants.get,key="empirical_h5_variant")
        lag=st.selectbox("HAC 시차",[5,20],key="empirical_h5_hac")
        diagnostic=data["h5_design_diagnostics"].query("variant == @variant and lags == @lag").iloc[0]
        st.caption(f"관측 {int(diagnostic['n'])}거래일 · 설계행렬 rank {int(diagnostic['rank'])}/{int(diagnostic['columns'])}")
        coeff=data["h5_coefficients"].query("variant == @variant and lags == @lag").copy()
        labels={"weekly_expiry":"만기 당일","before_weekly_expiry":"직전 거래일","after_weekly_expiry":"직후 거래일"}
        coeff=coeff.loc[coeff.term.isin(labels)].copy()
        if coeff.empty: st.warning("설계행렬이 식별되지 않아 개별 만기 계수를 표시하지 않습니다.")
        else:
            coeff["구간"]=coeff.term.map(labels)
            fig=go.Figure(go.Scatter(x=coeff.coefficient,y=coeff["구간"],mode="markers",
                error_x=dict(type="data",symmetric=False,array=coeff.ci_high-coeff.coefficient,arrayminus=coeff.coefficient-coeff.ci_low)))
            fig.add_vline(x=0,line_dash="dash",line_color="#888")
            fig.update_layout(title="H5 계수와 95% 구간",xaxis_title="log 분산 계수")
            show(fig,"empirical_h5")
            st.dataframe(coeff[["구간","coefficient","ci_low","ci_high"]],hide_index=True,width="stretch")
        st.write("**해석:** 기본 모형 만기 당일 계수는 약 +0.280이지만 구간은 −0.099~+0.659로 0을 포함합니다. 만기 전·후와 민감도 모형에서도 상승 효과를 확정하지 못했습니다. full rank가 인과 식별을 보장하지 않으며 휴일·제도변경에 따른 소수 대조 관측의 영향이 남습니다.")
        st.subheader("요일별 대조 관측 수")
        cells=data["h5_weekday_comparison"].copy()
        cells["요일"]=cells.weekday.map({0:"월",1:"화",2:"수",3:"목",4:"금"})
        cells["만기 여부"]=cells.weekly_expiry.map({0:"비위클리만기",1:"위클리만기"})
        show(px.bar(cells,x="요일",y="days",color="만기 여부",barmode="group",labels={"days":"거래일 수"}),"empirical_weekday")
        st.caption("수요일의 비위클리만기에는 월물만기가 포함됩니다. 휴일 이동 만기는 외생적인 실험으로 간주하지 않습니다.")
        table_download(data["h5_coefficients"],"전체 H5 계수·불확실성 CSV","empirical_h5_coefficients")
    elif view=="H6 예측 검증":
        st.subheader("OI가 기준모형에 예측 정보를 더하는가?")
        st.write(f"테스트 {summary['test_start']}–{summary['test_end']}, 동일한 {summary['test_days']}개 날짜를 비교했습니다. 최소 100개 완결 라벨로 시작해 매일 훈련창을 늘리고, 훈련 라벨 종료일이 예측일보다 앞서도록 겹치는 미래 구간을 제거했습니다.")
        proxy=st.selectbox("변동성 대용치",list(PROXIES),format_func=PROXIES.get,key="empirical_proxy")
        block=st.selectbox("블록 길이 (거래일)",[10,5,20],key="empirical_bootstrap")
        losses=data["h6_loss_comparison"].query("proxy == @proxy and block == @block").copy()
        losses["모형"]=losses.model.map(LABELS)
        fig=go.Figure(go.Scatter(x=losses.qlike_difference,y=losses["모형"],mode="markers",
            error_x=dict(type="data",symmetric=False,array=np.maximum(losses.ci_high-losses.qlike_difference,0),
                         arrayminus=np.maximum(losses.qlike_difference-losses.ci_low,0))))
        fig.add_vline(x=0,line_dash="dash",line_color="#888")
        fig.update_layout(title="평균 QLIKE 차이와 블록 부트스트랩 95% 구간",xaxis_title="추가 모형 − 기준모형 손실 · 음수면 개선")
        show(fig,"empirical_h6_ci")
        st.caption("‘HAR + 달력’ 행은 HAR과 비교합니다. OI 행은 HAR + 달력과 비교합니다. QLIKE 절대값은 음수일 수 있고 대용치 사이에 직접 비교하지 않습니다.")
        primary=losses.loc[losses.model.eq("HAR_calendar_OI_lag1")].iloc[0]
        st.warning(f"OI 1일 지연의 평균 손실차 {primary.qlike_difference:+.5f}, 95% 구간 [{primary.ci_low:+.5f}, {primary.ci_high:+.5f}]. 이번 표본에서는 추가 예측력의 개선을 확인하지 못했습니다.")
        pred=data["h6_forecasts"].query("proxy == @proxy")
        pivot=pred.pivot(index="date",columns="model",values="qlike")
        cumulative=pd.DataFrame({LABELS[c]:(pivot[c]-pivot.HAR_calendar).cumsum() for c in
            ["HAR_calendar_OI_lag1","HAR_calendar_OI_lag2","HAR_calendar_totalOI_lag1"]}).reset_index()
        show(px.line(cumulative,x="date",y=list(cumulative.columns[1:]),title="날짜별 누적 손실차 · 아래로 갈수록 개선",color_discrete_sequence=["#087F8C","#426DAD","#C88B37"],labels={"date":"예측일","value":"누적 QLIKE 차이","variable":"모형"}),"empirical_h6_cumulative")
        st.write("**읽는 방법:** 어느 시기에는 개선돼도 뒤의 시기에 사라질 수 있습니다. 동일 계약 OI · 2일 지연 선이 2025년 말에 내려갔다가 2026년에 올라오는 것처럼, 일부 구간의 개선만으로 채택하지 않습니다.")
        scores=data["h6_scores"].query("proxy == @proxy").copy()
        scores["모형"]=scores.model.map(LABELS)
        st.dataframe(scores[["모형","n","qlike","mae","log_mse"]],hide_index=True,width="stretch")
        st.caption("HAR은 여기서 일별 분산 대용치의 1·5·22일 성분을 쓰는 HAR 형태 회귀입니다. OI 공표·수정 시각은 확보되지 않았으며 1일·2일 지연은 가정입니다. 결과는 사후 확정 자료의 연구 검증이며 실시간 예측 성과나 투자 수익률이 아닙니다.")
        table_download(pred,"예측값·실제값·훈련 종료일 CSV","empirical_h6_predictions")
        table_download(losses,"모형 비교·신뢰구간 CSV","empirical_h6_comparison")
    else:
        st.subheader("홍콩 HKEX: 무료 열람과 공개 활용 권한")
        st.write("위클리 Hang Seng Index 옵션의 공개 일별 보고서 접근과 샘플 필드를 확인했습니다. 그러나 HKEX 약관 5절은 자동 접근·파생 데이터베이스·제3자 배포에 별도 허락을 요구합니다. 사용 가능한 별도 권한이 없어 홍콩 시세·파생 시계열의 공개와 H5/H6 분석은 보류했습니다.")
        st.dataframe(pd.DataFrame([
            ["상품 식별","HSI 위클리 지수옵션","만기일 + 콜풋 + 행사가; 연구용 ID와 주문 코드는 구분"],
            ["가격","OQP / 주간 open·high·low / 야간 close","OQP는 공식 호가가격이며 체결 종가가 아님"],
            ["거래량·OI","주간·야간 거래량 / 결합 OI·OI 증감","세션 거래량 합계와 보고서 총계를 대사하는 파서 구현"],
            ["기초자산","HSI 현물 OHLC·장중 이력 필요","옵션 OQP로 현물 변동성을 대신 계산하지 않음"],
            ["개별주식 위클리","기존 54개 클래스 명부는 별도 유지","이번 HSI 보고서에 주식옵션이 포함됐다고 보지 않음"],
            ["공개 배포 상태","시세·원문·파생 시계열 미포함","권한 있는 파일 확보 후 오프라인 파서 연결 가능"],
        ],columns=["영역","확인 내용","해석·조건"]),hide_index=True,width="stretch")
        st.link_button("HKEX 공식 일별 보고서","https://www.hkex.com.hk/Market-Data/Statistics/Derivatives-Market/Daily-Market-Report-(Latest)?sc_lang=en")
        st.link_button("HKEX 이용약관 5절","https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en")
        st.link_button("HKEX Data Marketplace","https://data.hkex.com.hk/")
        st.caption("문의 시 필요한 권한: 자동 조회, 연구·모형 학습, 파생 통계 공개, 공개 Streamlit 표시, GitHub 원자료 배포를 각각 확인해야 합니다.")
    with st.expander("재현·다운로드·연구 범위"):
        st.write("본 분석은 대만 지수옵션의 일별 대용치 연구입니다. 개별주식 인과효과, 국내 전이, 장중 RV, REV 가격반전, 매매 수익 검증을 완료했다는 뜻은 아닙니다.")
        st.code("python scripts/analyze_empirical.py",language="bash")
        st.link_button("전체 실측 보고서","https://github.com/mw48795472/Weekly-Option-Model-preview/blob/codex/streamlit-public-deployment/docs/empirical-analysis.md")
        package=root/"docs/downloads/empirical_h5_h6.zip"
        if package.exists():
            st.download_button("분석 결과·그래프 ZIP",package.read_bytes(),file_name=package.name,mime="application/zip",key="empirical_zip")
