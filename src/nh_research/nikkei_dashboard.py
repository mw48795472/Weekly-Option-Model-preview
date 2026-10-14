"""Japanese OSE Nikkei225 research through J-Quants, with explicit data readiness."""
import json
import pandas as pd
import streamlit as st
from .empirical_dashboard import table_download
from .nikkei import api_routes, PERSONAL_URL, PRO_URL, OSE_URL


@st.cache_data
def load_nikkei(root):
    directory = root / 'data/analysis/nikkei'
    return (json.loads((directory / 'summary.json').read_text(encoding='utf-8')),
            pd.read_csv(directory / 'status.csv'), pd.read_csv(directory / 'required_data.csv'))


def render_nikkei(root):
    summary, status, requirements = load_nikkei(root)
    st.title('닛케이225 확장')
    st.caption('일본 JPX/OSE 시장 · J-Quants 기반 | 명세 확인 2026-10-13')
    st.info('일본 닛케이225 미니옵션(NK225MWE)의 가격·OI를 J-Quants에서 확보해 H5·H6를 별도 추정합니다. '
            '대만 실측 결과는 국가 간 비교 자료로 유지합니다.')
    a, b, c = st.columns(3)
    a.metric('닛케이 실제 관측', str(summary['nikkei_observations']))
    b.metric('데이터 출처', 'J-Quants')
    c.metric('닛케이 H5·H6', '미실행')
    st.warning('현재 J-Quants 서비스·구독 권한과 로컬 인증 설정을 확인 중입니다. '
               'J-Quants 인증·시세 조회는 미실행이며, 이전 TAIFEX 요청 결과는 일본 데이터의 가용성 판단에 사용하지 않습니다.')
    view = st.radio('닛케이 확장 보기', ['상품·확보 상태', '분석 입력·실행 조건'], horizontal=True, key='nikkei_view')
    if view == '상품·확보 상태':
        st.subheader('J-Quants 서비스별 수집 경로')
        routes = api_routes()
        st.dataframe(routes, hide_index=True, width='stretch', column_config={'source_url':st.column_config.LinkColumn('공식 명세')})
        st.write('개인용 Premium의 전체 옵션 API와 Pro의 옵션 API는 NK225MWE를 지원합니다. '
                 '개인용 Standard 이상의 닛케이225 전용 API는 위클리·미니를 제외하므로 표준 옵션 비교군에만 사용합니다.')
        st.caption('명세에 포함된 것과 사용 계정의 이용 권한·실제 수집 성공은 다릅니다. 개인용은 x-api-key, Pro는 Bearer 토큰을 사용합니다.')
        st.link_button('개인용 J-Quants 옵션 API', PERSONAL_URL)
        st.link_button('J-Quants Pro 옵션 API', PRO_URL)
        st.subheader('일본 상품·만기 구조')
        st.write('위클리 연구 대상은 NK225MWE, 표준 옵션 비교군은 NK225E입니다. 미니옵션 이력은 2023-05-29부터이며 '
                 '수요일 만기는 2025-05-26 도입입니다. SQ일과 최종거래일, 주간과 야간을 구분합니다. '
                 '승수는 JPY 100이고 시초가 SQ를 사용하므로 일본 사건창에 맞춰 분석합니다.')
        st.link_button('OSE 닛케이225 미니옵션 규격', OSE_URL)
        st.subheader('명세 확인과 실제 확보 상태')
        st.dataframe(status, hide_index=True, width='stretch', column_config={'source_url':st.column_config.LinkColumn('공식 근거')})
        table_download(routes, 'J-Quants API 경로 CSV', 'nikkei_routes_csv')
        table_download(status, '닛케이 자료 확보 상태 CSV', 'nikkei_status_csv')
    else:
        st.subheader('일본 데이터로 H5·H6 구성')
        st.dataframe(pd.DataFrame([
            ['H5 만기', '현물 OHLC·장중 가격 + 실제 SQ/최종거래일', '시초 SQ 사건창; 수요일 도입·월간 SQ·요일·휴일 구분'],
            ['H6 OI', 'NK225MWE 계약별 OI + 동일 현물 타깃', '계약 생애·공표시각 보존; 같은 훈련/평가일; 미래 5일 창 겹침 제거'],
            ['국가 간 비교', '일본 J-Quants 결과와 기존 대만 결과', '시장별로 먼저 추정; UTC 가용시각 정렬; 국내 기준모형 대비 추가 가치 검증'],
        ], columns=['연구', '필요 입력', '검증 설계']), hide_index=True, width='stretch')
        st.warning('옵션 응답의 UnderPx/UnderlyingPrice는 기초가격 한 값입니다. 현물의 일중 고가·저가나 실현분산으로 대체하지 않습니다. '
                   'J-Quants 지수 목록에 닛케이225 현물 OHLC가 있다고 전제하지 않으며 별도 자료로 보완합니다.')
        st.dataframe(requirements, hide_index=True, width='stretch', column_config={'source_url':st.column_config.LinkColumn('공식 출처')})
        st.write('날짜별 전 체인을 페이지 끝까지 확보합니다. 중심월물 필터는 고정하지 않고, '
                 '개인용 Date+Code+EmMrgnTrgDiv / Pro TradeDate+Code+EmergencyMarginTriggerDivision으로 정산·긴급증거금 행을 구분합니다. '
                 '미니의 CM/ContractMonth는 주차 표현일 수 있어 달력 월로 변환하지 않습니다.')
        st.caption('실제 공표·수신 시각과 원본 버전을 보존합니다. 옵션·현물 입력이 갖춰져야 실측 추정을 시작할 수 있습니다. '
                   '개인용/Pro별 이용조건을 확인한 범위만 공개하며 자격증명은 앱에 포함하지 않습니다.')
        table_download(requirements, '닛케이 추가 데이터·필드 CSV', 'nikkei_requirements_csv')
    st.download_button('닛케이 가용성 감사 JSON', json.dumps(summary, ensure_ascii=False, indent=2),
                       'nikkei_availability.json', 'application/json', key='nikkei_summary')
