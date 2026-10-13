"""Separate OSE/Nikkei scope from TAIFEX; render verified availability only."""
import json
import pandas as pd
import streamlit as st
from .empirical_dashboard import table_download


@st.cache_data
def load_nikkei(root):
    directory = root / 'data/analysis/nikkei'
    return (json.loads((directory / 'summary.json').read_text(encoding='utf-8')),
            pd.read_csv(directory / 'status.csv'), pd.read_csv(directory / 'required_data.csv'))


def render_nikkei(root):
    summary, status, requirements = load_nikkei(root)
    st.title('닛케이225 확장')
    st.caption('TAIFEX 연구 설계 → JPX/OSE Nikkei 225 mini Options | 확인 2026-10-13')
    st.warning('TAIFEX의 일본 지수 상품은 TOPIX 선물(TJF)입니다. 닛케이225 옵션의 실제 분석은 별도의 OSE 자료가 필요합니다.')
    a, b, c = st.columns(3)
    a.metric('닛케이 실제 관측', str(summary['nikkei_observations']))
    b.metric('추가 API 성공 / 시도', f"{summary['api_success']} / {summary['api_requests']}")
    c.metric('닛케이 H5·H6', '미실행')
    st.info('이번 추가 다운로드는 로컬 네트워크 권한 오류와 승격 재시도 중단으로 완료되지 않았습니다. '
            'API 키 부족이나 서비스 응답 내용으로 판정한 것이 아닙니다. 실제 가격·OI를 확보하기 전까지 효과와 예측 성능은 표시하지 않습니다.')
    view = st.radio('닛케이 확장 보기', ['상품·확보 상태', '분석 입력·실행 조건'], horizontal=True, key='nikkei_view')
    if view == '상품·확보 상태':
        st.subheader('시장·상품을 정확히 구분하기')
        st.dataframe(pd.DataFrame([
            ['TAIFEX', 'TAIEX / TXO', '대만 지수옵션', '기존 H5·H6 실측 분석'],
            ['TAIFEX', 'TOPIX / TJF', '일본 TOPIX 선물', '닛케이225 옵션으로 대체하지 않음'],
            ['OSE (JPX)', 'Nikkei 225 mini Options', '닛케이225 미니옵션', '정확한 신규 비교 대상 · 원자료 미확보'],
        ], columns=['거래소', '상품', '종류', '이번 연구 범위']), hide_index=True, width='stretch')
        st.write('미니옵션은 2023-05-29 개시, 수요일 만기는 2025-05-26 도입입니다. 승수는 JPY 100이며, '
                 '수·금 SQ일과 직전 영업일의 최종거래일을 구분합니다. SQ는 시초가 기준이므로 대만의 마감 무렵 결제창을 그대로 적용하지 않습니다.')
        st.link_button('OSE 닛케이225 미니옵션 규격', 'https://www.jpx.co.jp/english/derivatives/products/domestic/225mini-options/01.html')
        st.link_button('TAIFEX 공식 상품표', 'https://www.taifex.com.tw/enl/eng2/products')
        st.subheader('확인된 자료와 미확보 자료')
        st.dataframe(status, hide_index=True, width='stretch', column_config={'source_url':st.column_config.LinkColumn('공식 근거')})
        st.write('JPX 공개 옵션이론가격 CSV는 최근 약 2개월과 종목·월물·프리미엄종가·이론가격·변동성·기초지수 종가를 안내합니다. '
                 '안내 필드에는 OI가 없어 이것만으로 H6를 실행할 수 없습니다. 이론가격과 실제 체결가격도 분리해야 합니다.')
        st.caption('상품표의 웹 확인과 API 원문 수집 성공은 다른 상태입니다. 이번에는 공식 웹으로 상품을 확인했고 API 원문은 확보하지 못했습니다.')
        table_download(status, '닛케이 자료 확보 상태 CSV', 'nikkei_status_csv')
    else:
        st.subheader('같은 연구 질문을 OSE 구조에 맞춰 다시 정의')
        st.dataframe(pd.DataFrame([
            ['H5 만기', 'OSE 실제 SQ·최종거래일 + 시초가·장중 가격', '수요일 도입, 월간 SQ, 요일·휴일과 만기를 구분; 사건창별 분석'],
            ['H6 OI', '개별 계약 OI + 공표·정정시각 + 동일 현물 타깃', '1·5·22일 기준모형; 같은 훈련·평가 날짜; 미래 5일 창 겹침 제거'],
            ['한·대·일 전이', 'UTC available_at + 각 거래소 세션·휴일', '현지 날짜의 단순 조인 금지; 국내 기준모형 대비 추가 가치 별도 검증'],
        ], columns=['연구', '필요 입력', '설계 차이']), hide_index=True, width='stretch')
        st.dataframe(requirements, hide_index=True, width='stretch', column_config={'source_url':st.column_config.LinkColumn('공식 출처')})
        st.write('공개 열람 가능 여부와 자동 수집·파생통계 공개·원자료 재배포 권한은 따로 확인해야 합니다. '
                 'Nikkei/JPX 가격 파일은 공개 GitHub나 다운로드 ZIP에 포함하지 않았습니다.')
        st.caption('허용된 현물 OHLC 파일을 로컬 검증기에 넣으면 기초 통계를 계산할 수 있습니다. 옵션 OI와 실제 SQ 달력이 없는 현물 통계는 H5·H6 검정이 아닙니다.')
        table_download(requirements, '닛케이 추가 데이터·필드 CSV', 'nikkei_requirements_csv')
    st.download_button('닛케이 가용성 감사 JSON', json.dumps(summary, ensure_ascii=False, indent=2),
                       'nikkei_availability.json', 'application/json', key='nikkei_summary')
