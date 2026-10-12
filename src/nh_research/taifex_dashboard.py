"""TAIFEX saved-data page. UI performs no network requests."""
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from nh_research.dashboard_data import csv_bytes


@st.cache_data
def load_taifex(root):
    folder=Path(root)/"data/analysis/taifex"
    text_types={"product":str,"underlying_code":str,"expiry_code":str,"contract_id":str,"strike_text":str}
    return {
        "summary":json.loads((folder/"summary.json").read_text(encoding="utf-8")),
        "history":pd.read_csv(folder/"weekly_history.csv.gz",dtype=text_types),
        "latest":pd.read_csv(folder/"latest_weekly.csv",dtype=text_types),
        "groups":pd.read_csv(folder/"expiry_summary.csv",dtype=text_types),
        "changes":pd.read_csv(folder/"oi_decomposition.csv",dtype=text_types),
        "pcr":pd.read_csv(folder/"put_call_history.csv"),
        "tickers":pd.read_csv(folder/"ticker_catalog.csv",dtype=text_types,keep_default_na=False),
        "products":pd.read_csv(folder/"product_tickers.csv",dtype=text_types,keep_default_na=False),
        "coverage":pd.read_csv(folder/"api_coverage.csv",dtype=str,keep_default_na=False),
    }


def render_taifex(root):
    root=Path(root)
    st.title("TAIFEX · 실제 가격과 OI")
    try:
        data=load_taifex(str(root))
    except (OSError,ValueError) as exc:
        st.error(f"저장된 TAIFEX 자료를 읽지 못했습니다: {type(exc).__name__}")
        return
    summary=data["summary"]
    st.caption(f"수집 {summary['collected_date_kst']} KST · 가격 API 기준 {summary['api_market_date']} · "
               f"역사 CSV {summary['history_start']}–{summary['history_end']} / {summary['history_dates']}개 관측 거래일")
    st.info("공식 API·과거 CSV에서 실제 수집한 고정 스냅샷입니다. 화면을 열어도 새 시세를 호출하지 않습니다. "
            "이 화면은 20일 계약 기술통계입니다. 428일 기초자산·예측 검증은 사이드바 H5·H6 실측 연구에서 확인하세요.")
    a,b,c,d=st.columns(4)
    a.metric("API 계약·세션 행",f"{summary['api_rows']:,}")
    b.metric("최신 자료 위클리 계약",f"{summary['latest_weekly_contracts']:,}",help="주간 세션, 개별주식 7개와 TXO. 행사가·콜풋별 계약 수")
    c.metric("역사 관측 거래일",str(summary["history_dates"]))
    d.metric("가격·OI 대사 행",f"{summary['api_csv_overlap_rows']:,}",help="API와 CSV가 겹치는 동일 날짜·계약·세션. 호가 차이는 별도 표시")
    view=st.radio("TAIFEX 화면",["시장·OI 분석","개별 계약·티커","API 확인·다운로드"],horizontal=True,key="taifex_view")

    def plot(fig,key):
        fig.update_layout(template="plotly_white",height=370,margin=dict(l=20,r=20,t=35,b=30),
                          legend=dict(orientation="h"),font=dict(family="Malgun Gothic, sans-serif"))
        st.plotly_chart(fig,width="stretch",key=key,config={"displaylogo":False,"toImageButtonOptions":{"format":"png","scale":2}})

    if view=="시장·OI 분석":
        history=data["history"]
        names=history.groupby("product")["name"].first().to_dict()
        products=sorted(names)
        product=st.selectbox("분석 상품",products,index=products.index("CDO") if "CDO" in products else 0,
                             format_func=lambda code:f"{names[code]} ({code})",key="taifex_product")
        regular=history.loc[history["product"].eq(product)&history.session.eq("regular")]
        dates=sorted(regular.date.unique())
        day=st.selectbox("관측 거래일",dates,index=len(dates)-1,key="taifex_date")
        observed=regular.loc[regular.date.eq(day)]
        expiries=sorted(observed.expiry_code.unique())
        expiry=st.selectbox("주간 만기 코드",expiries,key="taifex_expiry")
        selected=observed.loc[observed.expiry_code.eq(expiry)]
        group=data["groups"].loc[lambda x:x["product"].eq(product)&x.date.eq(day)&x.expiry_code.eq(expiry)].iloc[0]
        a,b,c,d=st.columns(4)
        a.metric("선택 만기 OI",f"{group.oi:,.0f}")
        b.metric("체결가 관측 계약",f"{group.traded_contracts:.0f} / {group.contracts:.0f}")
        c.metric("풋 / 콜 OI", "정의 불가" if pd.isna(group.put_call_oi_ratio) else f"{group.put_call_oi_ratio:.2f}배")
        d.metric("상위 3개 행사가 OI", "정의 불가" if pd.isna(group.top3_strike_oi_share) else f"{group.top3_strike_oi_share:.1%}")
        st.write(f"계약 만기일 필드: **{str(group.expiry_date)[:10]}**. 주차 코드로 날짜를 계산하지 않고 공식 자료의 만기일을 사용합니다.")
        st.caption("OI는 주간 행만 사용합니다. 풋/콜 비율은 방향성 전망이나 순매도 포지션을 뜻하지 않으며, 행사가 집중도는 투자자 보유 집중도가 아닙니다.")
        left,right=st.columns(2)
        with left:
            st.subheader("어느 행사가에 OI가 모이는가")
            plot(px.bar(selected,x="strike",y="oi",color="side",barmode="group",
                        labels={"strike":"행사가","oi":"OI (계약)","side":"콜풋"},
                        color_discrete_map={"C":"#087F8C","P":"#C88B37"}),"tai_strike_oi")
        with right:
            st.subheader("정산가와 실제 마지막 체결가")
            fig=go.Figure()
            for side,color in (("C","#087F8C"),("P","#C88B37")):
                part=selected.loc[selected.side.eq(side)].sort_values("strike")
                fig.add_scatter(x=part.strike,y=part.settlement,mode="lines",name=f"{side} 정산가",line_color=color)
                traded=part.loc[part.has_trade_price]
                fig.add_scatter(x=traded.strike,y=traded.close,mode="markers",name=f"{side} 마지막 체결가",marker=dict(color=color,symbol="x",size=7))
            fig.update_layout(xaxis_title="행사가",yaxis_title="옵션 프리미엄 (원시 호가 단위)")
            plot(fig,"tai_price_curve")
        st.write(f"선택 계약의 **{group.trade_price_coverage_pct:.1f}%**에만 거래량>0인 마지막 체결가가 있습니다. "
                 "정산가는 마지막 체결가를 대체하지 않습니다. 서로 다른 시각의 마지막 거래 가격으로 차익거래 기회를 단정하지 않습니다.")
        st.subheader("OI 변화: 같은 계약의 변화와 표본 진입·이탈 구분")
        daily=regular.groupby("date").oi.sum().reset_index()
        plot(px.line(daily,x="date",y="oi",markers=True,labels={"date":"관측 거래일","oi":"상품 전체 위클리 OI (계약)"}),"tai_oi_history")
        change=data["changes"].loc[data["changes"]["product"].eq(product)]
        fig=go.Figure()
        for column,label,color,sign in [("matched_change","동일 계약 변화","#087F8C",1),("entering_oi","표본 진입 OI","#426DAD",1),("exiting_oi","표본 이탈 OI","#C88B37",-1)]:
            fig.add_bar(x=change.date,y=sign*change[column],name=label,marker_color=color)
        fig.add_scatter(x=change.date,y=change.total_change,name="총 OI 변화",mode="lines+markers",line_color="#23374D")
        fig.update_layout(barmode="relative",yaxis_title="직전 관측 거래일 대비 계약 수",xaxis_title="관측 거래일")
        plot(fig,"tai_oi_change")
        st.caption("총 변화 = 동일 계약 변화 + 새로 관측된 계약 OI − 사라진 계약 OI. 이 그래프는 선택 상품의 모든 위클리 만기를 포함합니다. "
                   "진입·이탈에는 상장·만기 및 자료 범위 변화가 포함될 수 있어 투자자 자금 유입·유출로 해석하지 않습니다.")
        with st.expander("TXO 전체 만기 Put/Call 이력"):
            pcr=data["pcr"].melt(id_vars="date",value_vars=["put_call_oi_ratio","put_call_volume_ratio"],var_name="measure",value_name="ratio")
            plot(px.line(pcr,x="date",y="ratio",color="measure",markers=True,
                         labels={"date":"거래일","ratio":"비율 (1 = 100%)","measure":"공식 집계"}),"tai_pcr")
            st.caption("TAIFEX가 발표한 TXO 전체 만기 집계입니다. 선택한 개별주식이나 위클리만의 PCR이 아닙니다.")
        st.download_button("선택 만기 계약·가격·OI CSV",csv_bytes(selected),"taifex_selected_expiry.csv","text/csv",key="tai_selected_download")

    elif view=="개별 계약·티커":
        st.subheader("기초주식 → API 상품코드 → 개별 옵션 계약")
        st.code("2330 (台積電 / TSMC) → CDO → 202610W2 + P + 2450\n"
                "연구용 ID: TAIFEX:CDO:202610W2:P:2450",language="text")
        st.write("API는 거래소 주문용 완성 티커를 반환하지 않습니다. 아래 연구용 ID는 상품·만기코드·콜풋·행사가를 결합한 내부 식별자입니다. "
                 "NH·다른 브로커 주문 심볼로 그대로 사용하지 않습니다.")
        st.caption("TXO의 API 상품코드는 월물·위클리 모두 TXO입니다. 거래시스템 상품코드는 W2→TX2, F2→TXV 등으로 구분됩니다. "
                   "개별주식의 CDO와 조정계약 CDA·CDB도 서로 다른 계약으로 보존합니다.")
        tickers=data["tickers"]
        query=st.text_input("티커·상품명·기초코드 검색",placeholder="예: 2330, CDO, TXO, 202610W2",key="tai_ticker_search")
        scope=st.radio("계약 범위",["위클리","전체 — 월물·조정계약 포함"],horizontal=True,key="tai_ticker_scope")
        filtered=tickers.loc[tickers.expiry_code.str.contains(r"[WF]")] if scope=="위클리" else tickers
        if query.strip():
            haystack=filtered[["contract_id","underlying_code","name","trading_product_code"]].astype(str).agg(" ".join,axis=1)
            filtered=filtered.loc[haystack.str.contains(query.strip(),regex=False,case=False)]
        st.caption(f"선택 {len(filtered):,}개 계약 · 수집 기간 중 관측된 계약이며 현재 상장 중인 계약 수와 다릅니다.")
        columns=["contract_id","underlying_code","name","product","expiry_code","expiry_date","side","strike_text","adjusted","trading_product_code"]
        st.dataframe(filtered[columns],hide_index=True,width="stretch",height=310)
        st.download_button("선택 티커 목록 CSV",csv_bytes(filtered),"taifex_filtered_tickers.csv","text/csv",key="tai_tickers_download")
        if not filtered.empty:
            ids=filtered.contract_id.tolist()
            chosen=st.selectbox("가격·OI 경로를 볼 개별 계약",ids,key="tai_contract")
            path=data["history"].loc[lambda x:x.contract_id.eq(chosen)&x.session.eq("regular")]
            if path.empty:
                st.info("이 계약은 최신 API 마스터에는 있으나 이번 위클리 역사 수집 범위의 가격 경로는 없습니다.")
            else:
                st.write(path.label.iloc[0])
                left,right=st.columns(2)
                with left:
                    path=path.copy()
                    path.loc[~path.has_trade_price,"close"]=float("nan")
                    prices=path[["date","settlement","close"]].melt(id_vars="date",var_name="price_type",value_name="premium")
                    plot(px.line(prices,x="date",y="premium",color="price_type",markers=True,
                                 labels={"date":"거래일","premium":"프리미엄","price_type":"정산가 / 마지막 체결가"}),"tai_single_price")
                with right:
                    plot(px.line(path,x="date",y="oi",markers=True,labels={"date":"거래일","oi":"OI (계약)"}),"tai_single_oi")
                st.caption("빈 마지막 체결가는 연결하거나 0으로 채우지 않습니다. 만기 전후 종목을 자동 롤한 가격 경로가 아닙니다.")
                st.download_button("이 계약의 가격·OI CSV",csv_bytes(path),"taifex_contract_history.csv","text/csv",key="tai_single_download")
        with st.expander("상품코드·기초종목 매핑 원장"):
            st.dataframe(data["products"],hide_index=True,width="stretch")
            st.caption("조정계약의 주식 수·현금 정보는 명시된 참조일의 정보이며 과거 모든 날짜에 소급 적용하지 않습니다.")

    else:
        st.subheader("실제 호출 범위")
        st.dataframe(data["coverage"],hide_index=True,width="stretch")
        st.write("공개 API는 키 없이 성공했습니다. 명세에 날짜 필터가 없고, date=20250102를 붙여도 최신 가격 응답과 동일한 해시가 반환됐습니다. "
                 "과거 가격·OI는 별도 공식 CSV 다운로드에서 한 달 구간을 받았습니다.")
        mismatch=summary["api_csv_discrepancies"]
        st.write(f"가격·거래량·OI는 겹치는 {summary['api_csv_overlap_rows']:,}행에서 일치했습니다. "
                 f"호가는 bid {mismatch['bid']:,}행 / ask {mismatch['ask']:,}행에 차이가 있어 같은 자료로 합치지 않습니다.")
        st.caption("OpenInterestOfLargeTradersOptions는 명세와 달리 실제로 CSV를 반환했습니다. 틱 API는 30MB 수집 한도를 넘어 전체 저장하지 않았으며, "
                   "첫 부분의 필드만 확인했습니다. 완전한 틱·주문장 분석으로 표시하지 않습니다.")
        st.warning("기초자산 장중 가격과 충분한 검증 기간이 없어 HAR/RV·가격회귀율 REV·국내 전이 성능은 아직 계산하지 않았습니다. "
                   "일별 OI·행사가 집중·가격 관측 범위와 표본 변화만 분석합니다.")
        a,b=st.columns(2)
        for col,label,file,mime in [
            (a,"전체 TAIFEX CSV 패키지","docs/downloads/taifex_weekly_data.zip","application/zip"),
            (a,"분석 보고서 Markdown","docs/taifex-analysis.md","text/markdown"),
            (b,"API·CSV 수집 기록","data/source/taifex/20261012/manifest.json","application/json"),
            (b,"종목 티커 전체 CSV","data/analysis/taifex/ticker_catalog.csv","text/csv")]:
            file_path=root/file
            if file_path.is_file():
                col.download_button(label,file_path.read_bytes(),file_path.name,mime,key="tai_"+file_path.name)
        pngs=sorted((root/"docs/images/taifex").glob("*.png"))
        if pngs:
            image=st.selectbox("TAIFEX PNG 그래프",pngs,format_func=lambda p:p.stem,key="tai_png")
            st.image(str(image),width="stretch")
            st.download_button("선택 PNG",image.read_bytes(),image.name,"image/png",key="tai_png_download")
    st.caption("출처: Taiwan Futures Exchange · 금융감독관리위원회 증권선물국 공개자료. "
               "Open Government Data License 1.0 적용 자료를 가공했으며 원 제공기관의 보증·추천을 뜻하지 않습니다.")
    st.link_button("공식 TAIFEX API ↗","https://openapi.taifex.com.tw/")
