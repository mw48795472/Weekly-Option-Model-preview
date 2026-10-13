"""Read-only local research workspace. Launch with streamlit run streamlit_app.py."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from nh_research.analysis import oi_change
from nh_research.dashboard_data import (
    HYPOTHESES, csv_bytes, filter_contracts, gamma_curve, index_windows,
    markdown_for_browser, report_section,
)
from nh_research.reversal import rev_bp
from nh_research.taifex_dashboard import render_taifex
from nh_research.empirical_dashboard import render_empirical
from nh_research.single_stock_dashboard import render_single_stocks
from nh_research.diagnostics_dashboard import render_diagnostics
from nh_research.nikkei_dashboard import render_nikkei

DATA = ROOT / "data/analysis"
EVIDENCE = "https://github.com/mw48795472/Weekly-Option-Model-preview/blob/43ab2df8ed7c7821e91554acba51d0338a0e6033"
COLORS = ["#087F8C", "#426DAD", "#C88B37", "#7C6BAD"]
PAGES = ["연구 개요", "종목·변수 탐색", "TAIFEX 실측 분석", "H5·H6 실측 연구", "개별주식 H5·H6", "H5·H6 심화 진단", "닛케이225 확장", "가설 검토", "PoC 실험실", "진단·다운로드"]

st.set_page_config(page_title="Weekly Option · 연구 대시보드", page_icon="◈", layout="wide")
st.markdown("""<style>
 .block-container {max-width:1400px;padding-top:4.5rem;padding-bottom:3rem}
 h1,h2,h3 {letter-spacing:-.04em;color:#162D46}
 [data-testid="stMetric"] {background:white;border:1px solid #DDE5EC;border-radius:12px;padding:16px}
 [data-testid="stMetricLabel"] {color:#526579}
 [data-testid="stSidebar"] {border-right:1px solid #DDE5EC}
 .eyebrow {font-size:.72rem;letter-spacing:.17em;color:#087F8C;font-weight:700;margin-bottom:8px}
 .subtitle {color:#596D82;max-width:850px;margin:0 0 24px;line-height:1.65}
 </style>""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    contracts = pd.read_csv(DATA / "contracts/weekly_contracts.csv", dtype=str, keep_default_na=False)
    variables = pd.read_csv(DATA / "contracts/variable_dictionary.csv", dtype=str, keep_default_na=False)
    sessions = pd.read_csv(DATA / "contracts/weekly_contract_sessions.csv", dtype=str, keep_default_na=False)
    summary = json.loads((DATA / "contracts/summary.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((DATA / "hypotheses/forecast_diagnostics.json").read_text(encoding="utf-8"))
    return contracts, variables, sessions, summary, diagnostics


try:
    contracts, variables, sessions, summary, diag = load_data()
except (OSError, ValueError) as exc:
    st.error(f"저장된 연구자료를 읽지 못했습니다: {type(exc).__name__}. README의 오프라인 재현 단계를 확인하세요.")
    st.stop()


def header(title, description):
    st.markdown('<div class="eyebrow">WEEKLY OPTION / RESEARCH WORKSPACE</div>', unsafe_allow_html=True)
    st.title(title)
    st.write(description)


def chart(fig, key, title=None):
    fig.update_layout(template="plotly_white", colorway=COLORS, height=365,
                      margin=dict(l=12, r=16, t=44 if title else 20, b=20),
                      paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(family="Malgun Gothic, sans-serif", color="#344B63"),
                      title=dict(text=title, font_size=16) if title else None,
                      legend=dict(orientation="h", y=-0.22))
    st.plotly_chart(fig, width="stretch", key=key,
                    config={"displaylogo": False, "toImageButtonOptions": {"format": "png", "filename": key, "scale": 2}})


def download(label, relative, name=None, mime=None, key=None):
    path = ROOT / relative
    if path.is_file():
        st.download_button(label, path.read_bytes(), file_name=name or path.name, mime=mime,
                           key=key or relative, width="stretch")
    else:
        st.caption(f"{label}: 배포 파일이 아직 없습니다.")


with st.sidebar:
    st.markdown("## ◈ Weekly Option")
    st.caption("NH선물 · TAIFEX 연구실")
    page = st.radio("연구 탐색", PAGES, key="page")
    st.divider()
    st.caption(f"자료 기준 · {summary['snapshot_date']} KST")
    st.write("**국내 마스터 + TAIFEX 실측 자료**")
    st.caption("국내 마스터 기준일입니다. TAIFEX는 별도 화면에 실제 관측·수집일을 표시합니다. 실시간 시세가 아닙니다. H5·H6 메뉴는 일별 대용치의 사후 예측 검증입니다.")
    download("통합 보고서 Word", "docs/downloads/weekly_option_hypotheses_review.docx", key="sidebar_word")
    st.link_button("GitHub 저장소 ↗", "https://github.com/mw48795472/Weekly-Option-Model-preview", width="stretch")


def overview():
    header("위클리옵션 연구 대시보드", "국내 공개 마스터의 연구 준비 상태를 살펴봅니다. TAIFEX 실제 가격·OI는 TAIFEX 실측 분석, 장기 기초지수와 예측 검증은 H5·H6 실측 연구에서 확인하세요. H5·H6 심화 진단은 표본·변수·모형의 한계를, 닛케이225 확장은 OSE 자료 연결 조건을 보여줍니다.")
    cols = st.columns(4)
    for col, label, value, help_text in zip(cols,
            ["고유 계약", "후보 만기 사건", "완료 사건", "유효 가격·OI"],
            [f"{len(contracts):,}", str(diag["candidate_underlying_date_events"]), str(diag["completed_candidate_events"]), "0"],
            ["세션 중복 제거 후 계약 수", "기초자산×만기일 기준. 독립 관측 수가 아닙니다.", "보존된 기준일 이전 만기", "진단 시점의 확보 관측 수"]):
        col.metric(label, value, help=help_text)
    st.info("이 국내 마스터에서 가능한 분석은 표본 구성·자료 가용성·설계 오류 진단입니다. 아래 계약 수를 거래량이나 시장 활성도로 해석하지 않습니다.")
    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("만기별로 어떤 계약이 있는가")
        grouped = contracts.groupby(["expiry_date", "product_name"], sort=True).size().rename("계약 수").reset_index()
        fig = px.bar(grouped, x="expiry_date", y="계약 수", color="product_name",
                     labels={"expiry_date": "만기일", "product_name": "상품"}, color_discrete_sequence=COLORS)
        fig.update_xaxes(type="category")
        chart(fig, "actual_expiry_composition")
        st.caption("같은 만기에 많은 행사가가 있어도 현물 변동성 사건 수는 늘지 않습니다. 이 자료는 3개 날짜의 6개 기초자산·만기 후보로 축약됩니다.")
    with right:
        st.subheader("다음 연구 순서")
        for number, title, text in [
            ("01", "시각과 정답부터 고정", "거래일·가격 커버리지·공표시각을 확인하고 HAR 기준을 구축합니다."),
            ("02", "H5 만기 · H6 OI", "같은 미래 RV와 같은 테스트 날짜에서 추가 예측력을 비교합니다."),
            ("03", "수급과 유동성으로 확장", "집계 수급의 추가 가치와 호가 기반 H9b를 별도 실험으로 검증합니다.")]:
            with st.container(border=True):
                st.markdown(f"**{number}　{title}**")
                st.write(text)
    st.subheader("주간과 야간의 표본 차이")
    c1, c2 = st.columns([1, 1.3])
    with c1:
        fig = px.bar(x=["주간 포함", "야간 포함", "야간에만 존재"],
                     y=[summary["day_rows"], summary["night_rows"], summary["night_only_contracts"]],
                     labels={"x": "마스터 범위", "y": "계약 수"}, color_discrete_sequence=COLORS)
        chart(fig, "actual_session_coverage")
    with c2:
        st.write(f"야간 마스터에만 존재하는 계약은 **{summary['night_only_contracts']}개**입니다. 주간과 야간 집합은 겹치므로 막대 세 개를 합산하면 안 됩니다.")
        st.write("주간·야간 파일의 추정 기준일이 달라 표본 차이가 발생했을 수 있습니다. 누락 종목의 거래가 없었다는 의미는 아닙니다.")
        st.caption("주간 추정 기준일 2026-10-07 · 야간 추정 기준일 2026-10-11. 실제 시세 관측일이 아닙니다.")
        download("전체 종목 CSV 패키지", "docs/downloads/weekly_option_data.zip", key="overview_csv")


def explorer():
    header("종목과 변수 탐색", "상품명·종목명과 코드로 찾고, 관측값과 아직 확보하지 못한 변수를 확인합니다.")
    a, b, c = st.columns(3)
    names = contracts.set_index("under_name")["product_name"].to_dict()
    products = a.multiselect("상품군", sorted(names), default=sorted(names), format_func=lambda x: f"{names[x]} ({x})", key="products")
    expiries = b.multiselect("만기일", sorted(contracts.expiry_date.unique()), default=sorted(contracts.expiry_date.unique()), key="expiries")
    sides = c.multiselect("콜·풋", ["C", "P"], default=["C", "P"], format_func=lambda x: "콜" if x == "C" else "풋", key="sides")
    query = st.text_input("종목코드 또는 상품·종목명 검색", placeholder="예: 코스피위클리, B09FG925", key="contract_search")
    subset = filter_contracts(contracts, products, expiries, sides, query)
    st.caption(f"선택 {len(subset):,} / 전체 {len(contracts):,}계약 · 미확보 값은 공란으로 유지")
    if subset.empty:
        st.info("선택 조건에 해당하는 계약이 없습니다. 상품군·만기·콜풋 선택이나 검색어를 바꿔보세요.")
    else:
        display = subset[["series", "product_name", "name_kor", "option_side", "expiry_date", "strike_p", "sessions"]].rename(columns={
            "series": "종목코드", "product_name": "상품명", "name_kor": "종목명", "option_side": "콜풋", "expiry_date": "만기일", "strike_p": "행사가", "sessions": "세션"})
        st.dataframe(display, hide_index=True, width="stretch", height=315)
        st.download_button("선택 종목 CSV", csv_bytes(subset), "filtered_contracts.csv", "text/csv", key="filtered_csv")
        a, b = st.columns([1.2, 1])
        with a:
            chart_data = subset.assign(strike=pd.to_numeric(subset.strike_p))
            fig = px.histogram(chart_data, x="strike", color="product_name", facet_row="option_side",
                               labels={"strike": "행사가", "product_name": "상품"}, color_discrete_sequence=COLORS, barmode="overlay", opacity=.8)
            chart(fig, "filtered_strike_coverage")
            st.caption("행사가 분포는 상장 범위를 나타냅니다. 지수 수준이 다른 상품군을 비교할 때는 상품군을 하나씩 선택하세요. OI 집중이나 유동성 분포가 아닙니다.")
        with b:
            options = subset.series.tolist()
            label_map = subset.set_index("series").name_kor.to_dict()
            selected = st.selectbox("개별 계약", options, format_func=lambda x: f"{' '.join(label_map[x].split())} · {x}", key="selected_contract")
            row = subset.set_index("series").loc[selected]
            st.write(f"**{row['product_name']}** · {row['expiry_date']} 만기")
            st.caption(row["market_data_status"])
            contract_sessions = sessions.loc[sessions["series"] == selected]
            st.download_button("이 계약의 세션별 CSV", csv_bytes(contract_sessions), f"{selected}.csv", "text/csv", key="single_csv")
            st.dataframe(pd.DataFrame({"변수": ["종목코드", "행사가", "계약승수", "현재가", "OI", "IV"],
                                       "값": [selected, row.strike_p, row.ctrt_size, row.last_pric or "미확보", row.opint or "미확보", row.ivol or "미확보"]}), hide_index=True, width="stretch")
    st.divider()
    st.subheader("변수 사전과 관측 범위")
    var = st.selectbox("분석 변수", variables.variable.tolist(),
                       format_func=lambda x: f"{x} · {variables.set_index('variable').loc[x, 'label_ko']}", key="variable")
    item = variables.set_index("variable").loc[var]
    x, y, z = st.columns(3)
    x.metric("확보 상태", item["status"])
    y.metric("관측 행", item.observed_rows)
    z.metric("공란 행", item.blank_rows)
    st.write(f"**의미·단위:** {item.label_ko} / {item.unit_or_format}")
    st.write(f"**분석 용도:** {item.analysis_use}")
    st.caption(f"주의: {item.caution} · 분모 {item.denominator_rows}행. 계약 수와 세션 행 수를 구분하세요.")
    with st.expander("변수 사전 전체 보기"):
        st.dataframe(variables, hide_index=True, width="stretch")
        st.download_button("변수 사전 CSV", csv_bytes(variables), "variable_dictionary.csv", "text/csv", key="dictionary_csv")


def hypotheses():
    header("가설별 검증 설계", "원 가설, NH 자료로 가능한 대안, 검증을 시작하기 위한 조건을 구분합니다.")
    frame = pd.DataFrame(HYPOTHESES, columns=["가설", "주제", "착수 조건", "추정 대상", "필수 자료"])
    st.dataframe(frame, hide_index=True, width="stretch", height=390)
    selection = st.selectbox("자세히 볼 가설", frame["가설"].tolist(), index=4,
                             format_func=lambda x: f"{x} · {frame.set_index('가설').loc[x, '주제']}", key="hypothesis")
    selected = frame.set_index("가설").loc[selection]
    a, b = st.columns(2)
    with a:
        with st.container(border=True):
            st.caption("검증할 질문")
            st.write(selected["추정 대상"])
    with b:
        with st.container(border=True):
            st.caption("추가로 필요한 관측")
            st.write(selected["필수 자료"])
    if selection in ["H3", "H7", "H8"]:
        st.info("NH의 품목별 투자자 매매로 접근하면 공동 FLOW-PRED 실험입니다. 같은 수급 신호를 세 가지 원인 가설의 독립된 성공으로 세지 않습니다.")
    if selection == "H9b":
        st.info("H9b는 공개 호가의 유동성 경보입니다. RFQ 포지션 추정이나 가격 방향 예측과 구분합니다.")
    report = (ROOT / "docs/hypotheses-review.md").read_text(encoding="utf-8")
    st.markdown(markdown_for_browser(report_section(report, selection), EVIDENCE))


def lab():
    header("PoC 실험실", "가정을 바꾸며 수식과 연구 설계가 어떻게 반응하는지 확인합니다.")
    st.warning("이 화면은 직접 입력한 가정·정수 마커를 사용하는 실험입니다. 시장 관측, 예측 성능, 투자 수익을 추정한 결과가 아닙니다.")
    experiment = st.radio("실험 선택", ["H5 감마와 만기", "H6 OI와 미래창", "REV 가격회귀율", "H9b 비용과 실행"], horizontal=True, key="experiment")
    if experiment == "H5 감마와 만기":
        a, b, c = st.columns(3)
        spot = a.number_input("가정 기초가격", min_value=1.0, max_value=100000.0, value=400.0, key="spot")
        moneyness = b.slider("행사가 / 기초가격", 0.8, 1.2, 1.0, .01, key="moneyness")
        sigma = c.slider("가정 연율 변동성 (%)", 5, 100, 25, key="sigma")
        days = np.linspace(.25, 30, 150)
        curve = pd.DataFrame({"잔존 달력일": days, "감마": gamma_curve(spot, spot*moneyness, sigma, days)})
        fig = px.line(curve, x="잔존 달력일", y="감마", color_discrete_sequence=COLORS)
        fig.update_xaxes(autorange="reversed")
        chart(fig, "scenario_h5_gamma")
        st.write("ATM 부근에서는 만기가 짧을수록 감마가 커지는 경향을 확인할 수 있습니다. 행사가를 바꾸면 같은 패턴이 유지되지 않을 수 있습니다.")
        st.caption("유럽형 Black–Scholes · r=q=0 · 달력일/365 · 감마 단위 1/기초가격. 이론적 민감도이며 실제 딜러 순감마나 현물 변동성 증폭의 증거가 아닙니다.")
    elif experiment == "H6 OI와 미래창":
        a, b, c = st.columns(3)
        previous = a.number_input("가정 전기 OI", min_value=0, max_value=100000000, value=10000, key="previous_oi")
        current = b.number_input("가정 당기 OI", min_value=0, max_value=100000000, value=12000, key="current_oi")
        horizon = c.slider("수정 미래창 길이", 1, 10, 5, key="horizon")
        delta = oi_change(current, previous)
        x, y = st.columns(2)
        x.metric("부호 있는 OI 변화율", "정의 불가" if delta is None else f"{float(delta):+.1%}")
        y.metric("변화의 크기", "정의 불가" if delta is None else f"{abs(float(delta)):.1%}")
        if delta is None:
            st.info("전기 OI가 0이면 변화율 분모가 없어 결측으로 남깁니다.")
        st.caption("OI 증가는 순롱 포지션 증가가 아닙니다. 변화의 부호와 절댓값은 다른 피처이며 계약 롤과 공표지연을 따로 처리해야 합니다.")
        windows = index_windows(horizon)
        fig = go.Figure()
        for name, color in zip(windows.columns[1:3], ["#C88B37", "#087F8C"]):
            fig.add_scatter(x=windows.iloc[:,0], y=windows[name], name=name, mode="lines+markers", line_color=color, connectgaps=False)
        fig.update_layout(xaxis_title="결정 인덱스 t", yaxis_title="정수 마커 평균 (시장 RV 아님)")
        chart(fig, "index_label_windows")
        st.write(f"수정 창은 t+1…t+{horizon}이며 마지막 {horizon}개는 미완결로 남깁니다. 비교한 원본 H9 식은 고정 t+4…t+8 창입니다.")
        st.caption("인덱스 라벨 검증을 H6 미래 RV 설계에 적용한 예시입니다. 이 선의 상승은 시간 마커가 증가하기 때문이며 변동성 추세가 아닙니다.")
        with st.expander("미완결 라벨 확인"):
            st.dataframe(windows.tail(10), hide_index=True, width="stretch")
    elif experiment == "REV 가격회귀율":
        cols = st.columns(5)
        labels = ["마감 30분 전", "만기일 종가", "다음 시가", "다음 +1분", "다음 +30분"]
        defaults = [400.0, 404.0, 403.0, 402.0, 401.0]
        prices = [col.number_input(label, min_value=.01, max_value=100000.0, value=value, step=.1, key=f"rev_{i}") for i, (col, label, value) in enumerate(zip(cols, labels, defaults))]
        values = [rev_bp(prices[0], prices[1], value) for value in prices[2:]]
        for col, name, value in zip(st.columns(3), ["REV1 · 시가", "REV2 · 1분", "REV3 · 30분"], values):
            col.metric(name, "정의 불가" if value is None else f"{value:+.2f} bp")
        a, b = st.columns(2)
        with a:
            chart(px.line(x=labels, y=prices, markers=True, labels={"x": "가격 시점", "y": "가정 가격"}, color_discrete_sequence=[COLORS[2]]), "scenario_rev_prices")
        with b:
            chart(px.bar(x=["REV1", "REV2", "REV3"], y=values, labels={"x": "평가 지평", "y": "가정 REV (bp)"}, color_discrete_sequence=COLORS), "scenario_rev_values")
        st.write("양수는 마지막 30분 움직임의 반전, 음수는 지속입니다. 기준 움직임이 0이면 방향을 정의할 수 없어 REV도 결측입니다.")
        st.caption("REV는 방향을 조정한 다음 구간 수익률이며, 만기 직전 움직임의 몇 %를 되돌렸는지 나타내는 비율이 아닙니다. 실제 REV 표본은 0개입니다.")
    else:
        a, b, c = st.columns(3)
        move = a.slider("가정 mid 가격 변화 (bp)", -50, 100, 20, key="move_bp")
        spread = b.slider("진입·청산 각각의 전체 스프레드 (bp)", 0, 80, 12, key="spread_bp")
        fees = c.slider("왕복 수수료·추가 슬리피지 (bp)", 0, 30, 4, key="fees_bp")
        cost = spread + fees
        st.metric("가정 롱 순손익", f"{move-cost:+.1f} bp")
        scenarios = np.arange(-50, 101)
        fig = px.line(x=scenarios, y=scenarios-cost, labels={"x": "가정 mid 변화 (bp)", "y": "가정 롱 순손익 (bp)"}, color_discrete_sequence=COLORS)
        fig.add_hline(y=0, line_dash="dash", line_color="#7B8DA1")
        fig.add_vline(x=cost, line_dash="dot", line_color=COLORS[2])
        chart(fig, "scenario_liquidity_cost")
        st.write(f"이 대칭 스프레드 가정에서는 mid 변화가 {cost:.1f}bp를 넘어야 비용을 상쇄합니다. 유동성 경보가 유용하더라도 거래 수익을 보장하지 않습니다.")
        st.caption("진입 ask·청산 bid에서 각각 반 스프레드를 부담하므로 동일 전체 스프레드 한 번을 차감합니다. 모두 동일 기준가격 bp의 1차 근사이며 체결·시장충격·옵션 승수는 별도 검증 대상입니다. H9b 목표는 다음 5분 스트레스 확률입니다.")


def diagnostics():
    header("진단과 연구자료 다운로드", "숫자의 출처를 확인하고 보고서·CSV·PNG를 연구에 활용합니다.")
    a, b = st.columns(2)
    a.metric("만기 설계행렬 rank", "1 / 2")
    b.metric("상품·요일 설계행렬 rank", "4 / 5")
    st.write("현재 후보 사건에는 비만기 대조가 없어 상수와 만기 더미가 겹칩니다. 상품군과 월요일에도 정확한 선형 관계가 있습니다. 역사자료를 확보하면 설계를 다시 검사해야 합니다.")
    matrix = pd.read_csv(DATA / "hypotheses/forecast_design_matrix.csv", keep_default_na=False)
    st.dataframe(matrix[["product", "expiry_date", "contracts", "intercept", "monday", "WKM", "WQI", "WQM"]], hide_index=True, width="stretch")
    st.code("monday = WKM + WQM", language="text")
    with st.expander("실행한 진단 JSON"):
        st.json(diag)
    st.subheader("보고서와 데이터")
    a, b, c = st.columns(3)
    with a:
        download("Word 통합보고서", "docs/downloads/weekly_option_hypotheses_review.docx", key="word")
        download("Markdown 통합보고서", "docs/hypotheses-review.md", key="md")
        download("오프라인 HTML mock ZIP", "docs/downloads/weekly_option_poc.zip", key="mock")
    with b:
        download("전체·상품별·종목별 CSV ZIP", "docs/downloads/weekly_option_data.zip", key="csv_zip")
        download("진단 결과 JSON", "data/analysis/hypotheses/forecast_diagnostics.json", key="diag")
        download("설계행렬 CSV", "data/analysis/hypotheses/forecast_design_matrix.csv", key="matrix")
    with c:
        download("H1·H2·H4 검토 노트", "docs/research/hypotheses/causality_transfer.md", key="causal")
        download("H3·H7·H8 검토 노트", "docs/research/hypotheses/position_mechanisms.md", key="positions")
        download("H5·H6·H9 검토 노트", "docs/research/hypotheses/forecast_execution.md", key="forecast")
    st.subheader("저장된 PNG 그래프")
    images = sorted((ROOT / "docs/images").glob("*.png"))
    image = st.selectbox("그래프 선택", images, format_func=lambda x: x.stem, key="png")
    if image:
        st.image(str(image), width="stretch")
        st.download_button("이 그래프 PNG", image.read_bytes(), image.name, "image/png", key="png_download")
    st.caption("이 앱의 대화형 그래프는 오른쪽 위 카메라 아이콘으로 PNG를 저장할 수 있습니다. PoC 그래프에는 가정 또는 인덱스라는 축 설명을 함께 보존합니다.")


{"연구 개요": overview, "종목·변수 탐색": explorer, "TAIFEX 실측 분석": lambda: render_taifex(ROOT), "H5·H6 실측 연구": lambda: render_empirical(ROOT), "개별주식 H5·H6": lambda: render_single_stocks(ROOT), "H5·H6 심화 진단": lambda: render_diagnostics(ROOT), "닛케이225 확장": lambda: render_nikkei(ROOT), "가설 검토": hypotheses,
 "PoC 실험실": lab, "진단·다운로드": diagnostics}[page]()
