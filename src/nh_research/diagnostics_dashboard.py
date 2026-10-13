"""Frozen H5/H6 diagnostics: uncertainty, design, attrition and data priorities."""
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from .empirical_dashboard import show, table_download

VIEWS = ["판단 요약", "H5 정밀도·설계", "H6 표본·변수", "추가 데이터"]
REPORT = "reports/H5 H6 불확실성과 닛케이 확장.md"


@st.cache_data
def load_diagnostics(root):
    result = {}
    for name in ["h5_diagnostics", "h6_diagnostics"]:
        directory = root / "data/analysis" / name
        result[name] = {p.stem: pd.read_csv(p, dtype={"asset_id": str, "unit": str})
                        for p in sorted(directory.glob("*.csv"))}
        result[name]["summary"] = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    return result


def intervals(frame, low, high, point, label, title, axis):
    """Draw literal endpoints, including percentile CIs outside the point estimate."""
    fig = go.Figure()
    for row in frame.to_dict("records"):
        fig.add_scatter(x=[row[low], row[high]], y=[row[label], row[label]],
                        mode="lines", line=dict(color="#91AFC4", width=5),
                        showlegend=False, hovertemplate="%{x:.3f}<extra></extra>")
    fig.add_scatter(x=frame[point], y=frame[label], mode="markers", showlegend=False,
                    marker=dict(color="#087F8C", size=9), hovertemplate="%{y}: %{x:.3f}<extra></extra>")
    fig.add_vline(x=0, line_dash="dash", line_color="#778899")
    fig.update_layout(title=title, xaxis_title=axis)
    return fig


def render_h5(data):
    primary = data["primary_diagnostics"]
    names = primary.drop_duplicates("asset_id").set_index("asset_id").asset_name.to_dict()
    asset = st.selectbox("H5 분석 자산", list(names), format_func=names.get, key="deep_h5_asset")
    lag = st.selectbox("H5 HAC 시차", [5, 20], key="deep_h5_lag")
    row = primary.loc[primary.asset_id.eq(asset) & primary.lags.eq(lag)].iloc[0]
    cols = st.columns(4)
    cols[0].metric("회귀에 남은 거래일", f"{int(row.model_days):,}")
    cols[1].metric("그중 만기일", f"{int(row.event_days):,}")
    cols[2].metric("만기가 있는 서로 다른 주", f"{int(row.unique_expiry_weeks):,}")
    cols[3].metric("통제 후 만기변수 변동 비중", f"{100*row.expiry_information_fraction:.1f}%")
    st.caption("주 수는 달력상의 수입니다. 독립 표본 수나 유효 표본 크기로 추정한 값이 아닙니다.")
    section = st.radio("H5 진단 상세", ["관측 구간·설계", "표본 계획 시나리오", "기존 사양 민감도"],
                       horizontal=True, key="deep_h5_view")
    if section == "관측 구간·설계":
        st.subheader("지금 자료는 어느 크기의 효과까지 허용하는가?")
        all_assets = primary.loc[primary.lags.eq(lag)].copy()
        show(intervals(all_assets, "variance_ci_low_pct", "variance_ci_high_pct", "variance_effect_pct",
                       "asset_name", "H5 만기 당일 · 개별 95% 구간", "조건부 범위 분산의 비율 변화 (%)"), "deep_h5_ci")
        st.write(f"{names[asset]}의 분산 비율 변화는 **{row.variance_effect_pct:+.1f}%**, "
                 f"개별 95% 구간은 **[{row.variance_ci_low_pct:+.1f}%, {row.variance_ci_high_pct:+.1f}%]**입니다. "
                 "0을 포함한다는 사실만으로 효과가 없다고 결론내릴 수 없습니다.")
        st.caption("100 × (exp(로그계수) − 1). 로그 분산 모형의 조건부 기하평균 비율이며 산술평균 RV·투자수익률의 변화가 아닙니다. 종목별 숫자의 순위도 효과의 우열을 검정하지 않습니다.")
        st.subheader("표본 수와 별도로, 만기를 구분할 정보가 있는가?")
        info = all_assets.assign(통제후_잔차변동_비중=100*all_assets.expiry_information_fraction)
        show(px.bar(info, x="asset_name", y="통제후_잔차변동_비중",
                    labels={"asset_name":"자산", "통제후_잔차변동_비중":"만기변수의 잔차 변동 / 원래 변동 (%)"},
                    title="요일·월물·과거 변동성 등을 제거한 만기변수의 변동"), "deep_h5_design")
        st.write(f"선택 자산의 설계행렬 rank는 **{int(row['rank'])}/{int(row['columns'])}**, "
                 f"만기변수 VIF는 **{row.expiry_vif:.1f}**입니다. "
                 "잔차 변동 비중이 작으면 다른 통제변수와 만기의 패턴이 많이 겹칩니다. full rank는 계산 가능하다는 뜻이며 인과효과의 식별을 보장하지 않습니다.")
        cells = data["design_cells"].loc[lambda x: x.asset_id.eq(asset)].copy()
        cells["요일"] = cells.weekday.map({0:"월", 1:"화", 2:"수", 3:"목", 4:"금"})
        st.dataframe(cells, hide_index=True, width="stretch")
        with st.expander("가격 결측·0범위·과거창 때문에 빠진 날짜"):
            audit = data["exclusion_audit"].loc[lambda x: x.asset_id.eq(asset)]
            st.write("한 날짜의 결측은 이후 22일 과거창에도 영향을 줄 수 있습니다. 아래 원인 플래그는 서로 겹칠 수 있어 합산하지 않습니다.")
            st.dataframe(audit, hide_index=True, width="stretch")
            table_download(audit, "H5 날짜별 제외 점검 CSV", "deep_h5_exclusions")
    elif section == "표본 계획 시나리오":
        st.warning("조건부 연구 계획용 계산입니다. 관측된 계수로 사후 검정력을 계산한 것이 아니며, 더 수집하면 효과가 확인된다는 약속도 아닙니다.")
        st.write("현재 HAC 표준오차와 설계·자기상관 구조가 유지되고 정보가 표본에 비례해 늘어난다고 가정합니다. "
                 "양측 5% 검정·80% 검출확률의 정규근사이며, 실제 추가 자료의 유효성은 확보 후 다시 평가해야 합니다.")
        a, b = st.columns(2)
        a.metric("현 설계 조건부 MDE · 분산 증가", f"{row.planning_mde80_variance_pct:.1f}%")
        b.metric("다중비교 고려 계획 MDE", f"{row.planning_family_mde80_variance_pct:.1f}%")
        st.caption(f"다중비교 계획은 {int(row.planning_comparisons)}개 이벤트·자산 비교 기준입니다. MDE는 연구자가 중요하다고 정한 효과 크기와 다릅니다.")
        scenarios = data["sample_scenarios"].loc[lambda x: x.asset_id.eq(asset) & x.lags.eq(lag)]
        fixed = scenarios.loc[scenarios.scenario.eq("fixed_sample_multiplier")]
        show(px.line(fixed, x="sample_multiplier", y="planning_mde80_variance_pct", markers=True,
                     labels={"sample_multiplier":"정보가 비례해 늘어나는 표본 배수", "planning_mde80_variance_pct":"조건부 최소 검출 분산 증가 (%)"},
                     title="기간을 늘리는 효과는 동일 설계가 유지된다는 조건에 달려 있음"), "deep_h5_planning")
        st.dataframe(scenarios, hide_index=True, width="stretch")
        st.caption("10·25·50%는 비교를 위한 예시입니다. 사전 합의된 최소 중요 효과(SESOI)나 동등성 검정의 경계가 아닙니다. 새 거래일 수를 달력상의 확보 완료일로 환산하지 않습니다.")
        table_download(scenarios, "조건부 표본 계획 CSV", "deep_h5_scenarios")
    else:
        sensitivity = data["specification_sensitivity"].loc[lambda x: x.asset_id.eq(asset) & x.lags.eq(lag)].copy()
        st.write("이미 고정한 모형의 만기 당일·전·후 결과를 모두 비교합니다. 구간이 좋아 보이는 모형을 골라 주 결과를 바꾸지 않습니다.")
        event = st.selectbox("이벤트", ["weekly_expiry", "before_weekly_expiry", "after_weekly_expiry"],
                             format_func={"weekly_expiry":"만기 당일", "before_weekly_expiry":"직전 거래일", "after_weekly_expiry":"직후 거래일"}.get, key="deep_h5_event")
        selected = sensitivity.loc[sensitivity.term.eq(event)]
        if not selected.empty:
            show(intervals(selected, "variance_ci_low_pct", "variance_ci_high_pct", "variance_effect_pct",
                           "variant", "기존 사양별 개별 95% 구간", "조건부 범위 분산의 비율 변화 (%)"), "deep_h5_sensitivity")
        st.dataframe(sensitivity, hide_index=True, width="stretch")
        st.caption("사양별 대상·평가 날짜가 달라질 수 있습니다. 위약 달력도 유효한 무작위 인과 대조군을 뜻하지 않습니다. 개별 구간은 전체 사양 탐색을 보정한 구간이 아닙니다.")
        designs = data["specification_design"].loc[lambda x: x.asset_id.eq(asset)]
        st.subheader("통제 방식을 바꾸면 식별 정보도 달라지는가?")
        st.dataframe(designs, hide_index=True, width="stretch")
        st.write("주식의 상장 후 전용 사양은 만기·요일·월물의 패턴을 구분하는 정보가 한 날짜에 크게 의존합니다. "
                 "7개 주식 모두 2026-02-23을 제외하면 해당 사양의 rank가 떨어져 만기계수를 분리하지 못합니다. "
                 "따라서 유의한 사양을 선택하는 것보다 대조 구조를 보완하는 것이 우선입니다.")
        table_download(sensitivity, "기존 H5 사양 전체 CSV", "deep_h5_sensitivity_csv")
    table_download(primary, "전체 H5 정밀도·설계 CSV", "deep_h5_primary")


GATE_LABELS = {
    "pre_launch":"상장 이전", "history_initial_22":"초기 과거창",
    "history_missing_price":"과거창 가격 공란", "history_zero_range":"과거창 H=L",
    "history_non_comparable":"과거창 비교불가 가격", "history_other_proxy_missing":"기타 과거창 결측",
    "oi_warmup_or_source_missing":"OI 워밍업·자료 결측", "oi_zero_denominator_or_no_overlap":"OI 분모 0·교집합 없음",
    "oi_other_missing":"기타 OI 결측", "target_end_boundary":"말단 미래 5일 미완결",
    "target_missing_price":"미래창 가격 공란", "target_zero_range":"미래창 H=L",
    "target_non_comparable":"미래창 비교불가 가격", "target_other_missing":"기타 미래창 결측",
    "calendar_missing":"달력 결측", "initial_train_below_100":"초기 훈련 100개 미만",
    "purge_train_below_100":"겹친 미래창 제거 후 훈련 부족", "rank_unidentified":"예측 식별 불가",
    "evaluated":"최종 평가 날짜",
}
PROXIES = {"parkinson":"범위 분산 · 주 결과", "close_squared_return":"종가 수익률 제곱",
           "parkinson_clean":"비교불가일 제외 범위 분산"}
MODELS = {"matched_OI_lag1":"동일 계약 OI 변화율", "level_OI_lag1":"전체 OI 수준",
          "HAR_calendar":"HAR + 달력", "OI_lag1":"동일 계약 OI · 1일 지연",
          "OI_lag2":"동일 계약 OI · 2일 지연", "OI_total_lag1":"전체 체인 OI 변화율",
          "OI_level_lag1":"전체 OI 수준 · 1일 지연", "OI_level_lag2":"전체 OI 수준 · 2일 지연",
          "HAR_calendar_OI_lag1":"동일 계약 OI · 1일 지연",
          "HAR_calendar_OI_lag2":"동일 계약 OI · 2일 지연",
          "HAR_calendar_totalOI_lag1":"전체 체인 OI 변화율"}


def render_h6(data):
    information = data["information"]
    names = information.set_index("unit")["name"].to_dict()
    unit = st.selectbox("H6 분석 자산", list(names), format_func=names.get, key="deep_h6_asset")
    info = information.loc[information.unit.eq(unit)].iloc[0]
    part = data["sample_attrition"].loc[lambda x: x.unit.eq(unit)]
    proxy = st.selectbox("H6 결과 변수", part.proxy.unique().tolist(), format_func=PROXIES.get, key="deep_h6_proxy")
    family = st.selectbox("기존 분석 계열", part.loc[part.proxy.eq(proxy), "family"].unique().tolist(),
                          format_func={"matched":"동일 계약 변화율 · 주 계열", "level":"OI 수준 · 보조 계열"}.get, key="deep_h6_family")
    gates = part.loc[part.proxy.eq(proxy) & part.family.eq(family)].sort_values("order").copy()
    evaluated = int(gates.loc[gates.gate.eq("evaluated"), "count"].iloc[0])
    a, b, c = st.columns(3)
    a.metric("상장 후 옵션 거래일", str(int(info.option_days)))
    b.metric("실제 평가 날짜", str(evaluated))
    c.metric("계속된 계약의 전기 OI 비중 중앙값", f"{100*info.coverage_median:.1f}%")
    section = st.radio("H6 진단 상세", ["표본 탈락·OI 정보", "평가창·정밀도", "같은 훈련·평가 날짜 비교"],
                       horizontal=True, key="deep_h6_view")
    if section == "표본 탈락·OI 정보":
        st.subheader("428일 중 어떤 날짜가 왜 빠졌는가?")
        gates["단계"] = gates.gate.map(GATE_LABELS)
        shown = gates.loc[gates["count"].gt(0)]
        show(px.bar(shown, x="count", y="단계", orientation="h", color="단계",
                    labels={"count":"거래일 수"}, title="첫 번째 탈락 원인에만 배정 · 마지막 행은 남은 평가 날짜").update_layout(showlegend=False), "deep_h6_attrition")
        st.caption("위에서 아래의 고정 순서로 한 날짜를 한 번만 배정했습니다. 원인별 합계는 배정 순서에 의존하며 인과적 기여도 분해가 아닙니다. 마지막 평가 행을 포함하면 전체 달력과 일치합니다.")
        st.dataframe(gates[["단계", "count", "remaining"]].rename(columns={"count":"이 단계 날짜", "remaining":"단계 후 남은 날짜"}), hide_index=True, width="stretch")
        st.write(f"OI 변화율은 상장 후 **{int(info.matched_undefined_days)}일**에 정의되지 않습니다. "
                 "단순한 결측 보간으로 복구할 수 있는 관측이라고 가정하지 않습니다. 만기 소멸·신규 상장과 작은 분모를 먼저 구분해야 합니다.")
        st.dataframe(information.loc[information.unit.eq(unit)].T.rename(columns={info.name:"값"}).astype(str), width="stretch")
        st.caption("전기 OI 비중은 계속 관측되는 계약의 범위입니다. OI가 작을 때 변화율이 극단적일 수 있으며 OI 총량은 딜러 순감마·순롱 포지션을 의미하지 않습니다.")
        with st.expander("서로 겹치는 장애까지 날짜별 확인"):
            origins = data["origin_audit"].loc[lambda x: x.unit.eq(unit) & x.proxy.eq(proxy) & x.family.eq(family)]
            st.dataframe(origins, hide_index=True, width="stretch")
            table_download(origins, "H6 예측일별 탈락 점검 CSV", "deep_h6_origins")
        table_download(gates, "선택 표본 탈락 CSV", "deep_h6_gates")
    elif section == "평가창·정밀도":
        block = st.selectbox("H6 블록 길이", [10, 5, 20], key="deep_h6_block")
        rows = data["precision"].loc[lambda x: x.unit.eq(unit) & x.proxy.eq(proxy) & x.family.eq(family) & x.block.eq(block)].copy()
        if rows.empty:
            st.warning("이 분기에는 평가 표본이 없습니다. 성과가 0인 것이 아니며, 신뢰구간도 계산하지 않습니다.")
        else:
            r = rows.iloc[0]
            a, b = st.columns(2)
            a.metric("겹치지 않게 고를 수 있는 5일 타깃창", f"{int(r.disjoint_target_windows)}개")
            b.metric("평가 날짜 사이 달력 공백", f"{int(r.calendar_gaps)}일")
            st.write("매일 예측해도 다음 5일의 결과가 서로 겹칩니다. 위 창 개수는 달력에서 세어 본 최대 비중첩 구간 수로, 독립 표본 수나 유효 표본 크기가 아닙니다.")
            rows["모형"] = rows.model.map(MODELS).fillna(rows.model)
            show(intervals(rows, "ci_low", "ci_high", "qlike_difference", "모형",
                           "기존 모형 · 쌍별 QLIKE 차이의 95% 구간", "추가 모형 − 기준모형 손실 · 음수면 개선"), "deep_h6_precision")
            st.dataframe(rows.drop(columns=["disjoint_dates"]), hide_index=True, width="stretch")
            if rows.short_span_for_block.any():
                st.warning("평가 기간이 블록 길이에 비해 짧습니다. 가능한 블록 시작점이 적어 좁은 구간도 안정적인 정밀도 근거가 아닙니다.")
            st.caption("손실 차이의 불확실성입니다. 미래 변동성 예측구간이나 수익률 %가 아닙니다. 5·10·20일 블록 간 결과를 함께 읽으며 짧은 표본의 구간을 확증으로 보지 않습니다.")
            table_download(rows, "평가창·손실 불확실성 CSV", "deep_h6_precision_csv")
    else:
        st.warning("사후 탐색 진단입니다. 같은 훈련행·평가행에서 OI 정의만 바꿔 보았으며, 새 검증 기간에서 재현되기 전에는 주 가설의 성공으로 채택하지 않습니다.")
        st.write("이 비교는 **주 범위 분산(Parkinson)·동일 계약 계열의 적격 날짜**에 고정되어 있습니다. "
                 "위 결과 변수·기존 계열 선택과 별개입니다. 최소 100개 완결 라벨과 미래창 겹침 제거를 유지합니다.")
        block = st.selectbox("공통 날짜 비교 블록 길이", [10, 5, 20], key="deep_h6_refit_block")
        rows = data["common_refit_comparison"].loc[lambda x: x.unit.eq(unit) & x.block.eq(block)].copy()
        if rows.empty:
            st.info("주 계열에서 평가 가능한 날짜가 없어 이 비교도 실행하지 못했습니다.")
        else:
            rows["모형"] = rows.model.map(MODELS).fillna(rows.model)
            show(intervals(rows, "ci_low", "ci_high", "qlike_difference", "모형",
                           "동일 훈련·테스트 표본 · 주 범위 분산", "OI 추가 − HAR+달력 QLIKE · 음수면 개선"), "deep_h6_refit")
            st.dataframe(rows.drop(columns=["disjoint_dates"]), hide_index=True, width="stretch")
            st.write("Hon Hai와 Wistron의 OI 수준 사양에는 개선 신호가 나타났지만 각각 비중첩 5일 창이 7개·4개뿐입니다. "
                     "전체 대용치·사양 탐색을 보정하지 않았으므로 다음 수집 구간에서 고정 모형으로 재검증할 후보입니다.")
            table_download(rows, "공통 훈련·평가 비교 CSV", "deep_h6_refit_csv")


def render_summary(root, data):
    st.subheader("지금 구분할 수 있는 것")
    primary = data["h5_diagnostics"]["primary_diagnostics"].query("lags == 5")
    precision = data["h6_diagnostics"]["precision"]
    first = primary.loc[primary.asset_id.eq("TXO_TAIEX")].iloc[0]
    txo = precision.loc[precision.unit.eq("TXO") & precision.proxy.eq("parkinson") & precision.family.eq("matched") & precision.block.eq(10)].iloc[0]
    a, b, c = st.columns(3)
    a.metric("H5 수치적으로 추정 가능한 자산", f"{int(primary.identified.sum())} / {len(primary)}")
    b.metric("개별주식 H5 만기일", f"{int(primary.loc[primary.asset_kind.eq('stock'), 'event_days'].min())}–{int(primary.loc[primary.asset_kind.eq('stock'), 'event_days'].max())}일")
    c.metric("TXO H6 평가 / 비중첩 타깃창", f"{int(txo.n)} / {int(txo.disjoint_target_windows)}")
    st.write(f"**H5:** 행렬의 식별 실패가 주된 장애는 아닙니다. 그러나 TAIEX 만기 효과의 분산 비율 구간은 "
             f"{first.variance_ci_low_pct:+.1f}%~{first.variance_ci_high_pct:+.1f}%로 넓고, 만기와 요일의 패턴도 겹칩니다. "
             "상장 후만 분석한 주식 사양은 한 대조 날짜를 빼면 만기계수가 식별되지 않아 비교 설계도 보완해야 합니다.")
    st.write("**H6:** 총 거래일과 평가에 쓰이는 날짜는 다릅니다. 상장 후 이력이 짧고 OI 교집합·분모가 불안정하며, H=L 날짜의 제외가 과거·미래창까지 전파됩니다. "
             "같은 표본에서 OI 정의를 바꾸면 일부 신호가 생겨 변수·모형 의존성도 남습니다.")
    st.warning("‘표본만 늘리면 된다’와 ‘효과가 없다’는 모두 현재 자료보다 강한 주장입니다. 더 긴 관측과 함께 장중 가격, 기업행동, 계약 생애·OI 공표시각을 보완해야 합니다.")
    chart = root / "docs/images/h5_diagnostics/h5_precision_design.png"
    if chart.exists():
        st.image(str(chart), width="stretch")
    st.caption("관측 신뢰구간과 통제 후 만기변수 변동은 별개 진단입니다. 필요한 추가 자료와 사전에 고정할 검증 규칙은 ‘추가 데이터’에서 확인할 수 있습니다.")


def render_additional(root):
    st.subheader("다음 수집이 어떤 제약을 해소하는가?")
    path = root / "data/analysis/research_diagnostics/additional_data.csv"
    if not path.exists():
        path = root / "data/analysis/h6_diagnostics/additional_data.csv"
    frame = pd.read_csv(path)
    st.dataframe(frame, hide_index=True, width="stretch", column_config={"url":st.column_config.LinkColumn("공식 출처")})
    table_download(frame, "추가 데이터 우선순위 CSV", "deep_additional_data")
    st.write("다음 검증에서는 주 결과변수·OI 정의·대조군·평가기간·실무적으로 중요한 최소 효과를 먼저 고정합니다. "
             "장중 자료 확보 전까지는 일별 대용치 결과로 표시하고, 현재 탐색에서 보인 신호는 별도의 미래 평가로 확인합니다.")


def render_diagnostics(root):
    data = load_diagnostics(root)
    st.title("H5·H6 심화 진단")
    st.caption("표본 부족 · 변수 정보 · 모형 설정을 나눠 점검 | 기존 주 검증 결과 보존")
    st.info("효과 미확인은 ‘효과 없음’이나 ‘표본 부족 때문’ 중 하나로 자동 분류되지 않습니다. "
            "신뢰구간, 설계, 표본 탈락, 같은 날짜의 모형 비교를 함께 읽습니다.")
    view = st.radio("심화 진단 보기", VIEWS, horizontal=True, key="deep_view")
    if view == "H5 정밀도·설계":
        render_h5(data["h5_diagnostics"])
    elif view == "H6 표본·변수":
        render_h6(data["h6_diagnostics"])
    elif view == "추가 데이터":
        render_additional(root)
    else:
        render_summary(root, data)
    with st.expander("근거 자료·전체 보고서"):
        report = root / REPORT
        if report.exists():
            st.download_button("심화 진단 전체 보고서 Markdown", report.read_bytes(), report.name,
                               "text/markdown", key="deep_report")
        package = root / "docs/downloads/h5_h6_diagnostics.zip"
        if package.exists():
            st.download_button("심화 진단 CSV·PNG·보고서 ZIP", package.read_bytes(), package.name,
                               "application/zip", key="deep_zip")
        st.code("python scripts/analyze_h5_diagnostics.py\npython scripts/analyze_h6_diagnostics.py", language="bash")
