"""Japanese-market Nikkei225 research via J-Quants; no synthetic observations."""
from __future__ import annotations
import io
import numpy as np
import pandas as pd

OSE_URL = 'https://www.jpx.co.jp/english/derivatives/products/domestic/225mini-options/01.html'
PERSONAL_URL = 'https://jpx-jquants.com/en/spec/drv-bars-daily-opt'
STANDARD_URL = 'https://jpx-jquants.com/en/spec/drv-bars-daily-opt-225'
PRO_URL = 'https://jpx.gitbook.io/j-quants-pro/api-reference/options'
OI_URL = 'https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue'
NIKKEI_URL = 'https://indexes.nikkei.co.jp/nkave/data/index.en.html'


def readiness(manifest=None):
    manifest = manifest or {}
    service = manifest.get('source_service')
    verified_service = service in ('jquants_personal_v2', 'jquants_pro_v2')
    requests = manifest.get('requests', []) if verified_service else []
    return dict(version='nikkei-jquants-readiness-20261013', verified_at='2026-10-13',
        status='service_and_entitlement_unverified', data_provider='J-Quants',
        configured_service=service if verified_service else None,
        correct_venue='OSE (JPX)', correct_product='Nikkei 225 mini Options',
        product_category='NK225MWE', comparison_product_category='NK225E',
        nikkei_observations=0, option_oi_observations=0,
        h5_executed=False, h6_executed=False,
        api_requests=len(requests), api_success=sum(bool(r.get('complete')) for r in requests),
        requested_start='2023-05-29', requested_end='2026-10-08', actual_start=None, actual_end=None,
        product_evidence='J-Quants official API specifications; authenticated response not verified',
        reason='Japanese-market J-Quants source selected. Personal/Premium or Pro entitlement and credentials are not yet confirmed.',
        taifex_audit_is_jquants_evidence=False, public_raw_redistribution=False)


def api_routes():
    return pd.DataFrame([
        ('개인용 J-Quants Premium', 'https://api.jquants.com/v2', '/derivatives/bars/daily/options',
         'x-api-key', 'date + category=NK225MWE + pagination_key', 'data', '미니옵션 가격·OI·IV; 실제 권한 미확인', PERSONAL_URL),
        ('J-Quants Pro', 'https://api.jquants-pro.com/v2', '/derivatives/options',
         'Authorization: Bearer', 'date + category=NK225MWE + pagination_key', 'options', '미니옵션 가격·OI·IV; 별도 계약 확인', PRO_URL),
        ('J-Quants Pro', 'https://api.jquants-pro.com/v2', '/derivatives/open_interest_by_issue',
         'Authorization: Bearer', 'date + product_code=NK225MWE + pagination_key', 'open_interest_by_issue',
         '계약별 OI 대사; DataType=IssueData만 사용', OI_URL),
        ('개인용 Standard 이상', 'https://api.jquants.com/v2', '/derivatives/bars/daily/options/225',
         'x-api-key', 'date + pagination_key', 'data', '표준 닛케이 옵션 비교군; 위클리·미니 제외', STANDARD_URL),
    ], columns=['service', 'base_url', 'endpoint', 'authentication', 'query', 'response_array', 'scope', 'source_url'])


def status_table():
    return pd.DataFrame([
        ('연구 시장·출처', '확정', '일본 OSE 닛케이225 옵션을 J-Quants로 수집. 대만 TAIFEX 분석과 독립된 자료 경로.', PERSONAL_URL),
        ('위클리·미니 범위', '명세 확인', 'NK225MWE, 2023-05-29부터. 개인용 Premium 또는 Pro 옵션 API 대상.', 'https://jpx-jquants.com/en/spec/drv-bars-daily-opt/derivative-product-category'),
        ('서비스·권한', '사용자 확인 대기', '개인용 API와 Pro는 호스트·인증·필드명이 다름. NH선물 키를 재사용하지 않음.', PERSONAL_URL),
        ('J-Quants 인증·조회', '미실행', 'J-Quants 인증 요청·실제 시세 응답은 아직 검증하지 않음. 이전 TAIFEX 호출 실패와 무관.', PRO_URL),
        ('현물 가격·OI·SQ', '미수집', 'UnderPx/UnderlyingPrice는 현물 OHLC가 아님. H/L 및 장중 자료를 별도로 확보해야 함.', PERSONAL_URL),
        ('H5·H6', '미실행', '일본 SQ 달력·기초가격과 계약별 OI를 연결한 뒤 일본 표본에서 재추정.', OSE_URL),
        ('공개 이용 범위', '확인 필요', '개인용/Pro의 계약 범위에 따라 내부 분석·파생통계 공개 가능 여부를 확인.', 'https://pro.jpx-jquants.com/'),
    ], columns=['stage', 'state', 'detail', 'source_url'])


def required_data():
    return pd.DataFrame([
        ('P0', 'J-Quants 서비스·옵션 이용 권한', 'service,plan,credential_reference,permitted_uses', '개인용 Premium / Pro 경로 선택; 키 값은 로컬 보관', PERSONAL_URL, '확인 대기'),
        ('P0', 'NK225MWE 전 만기·행사가 가격/OI', 'Date/TradeDate,Code,ProdCat/DerivativesProductCategory,OI/OpenInterest,IV/ImpliedVolatility,LTD/LastTradingDay,SQD/SpecialQuotationDay,available_at', '계약별 H6; 페이지 끝까지 수집하고 표준 NK225E와 구분', PRO_URL, '명세 확인; 실제 미수집'),
        ('P0', '닛케이225 현물 OHLC·장중 가격', 'date,open,high,low,close,timezone,available_at', '일별 H5/H6 타깃; UnderPx 한 값으로 Parkinson 분산 생성 금지', NIKKEI_URL, 'J-Quants 옵션 필드만으로 확보되지 않음; 별도 보완'),
        ('P0', '실제 최종거래일·SQ·휴장 달력', 'Code,LTD/LastTradingDay,SQD/SpecialQuotationDay,multiplier,currency,listing_date', '시초 SQ, 수요일 도입 전후 및 월간 SQ 대조', OSE_URL, '명세 확인; 역사 레코드 미수집'),
        ('P0', 'OI 공표·정정 이력', 'observed_at,published_at,received_at,available_at,revision', '미래정보 누출 방지; 공표 예상시각과 실제 가용시각 구분', OI_URL, '개인용은 행별 가용시각·정정 전 원본 미제공'),
        ('P0', '이용·공개 범위', 'internal_use,derived_statistics,display,redistribution', '실측을 공개 앱에 올리기 전 허용 범위 확정', 'https://pro.jpx-jquants.com/', '계약 확인 필요'),
        ('P1', 'Pro 계약별 OI 대사', 'Date,SeriesCode,ProductCode,DataType,CurrentDayOpenContractQuantity', 'IssueData 계약행만 사용; 옵션 API OI와 시점·단위 대사', OI_URL, 'Pro 별도 데이터셋 권한 확인'),
        ('P1', '옵션 장중 호가·체결·IV', 'contract_id,timestamp,bid,ask,price,iv,delta,gamma', '감마·유동성 메커니즘; 일별 옵션 API와 별도', 'https://dc.jpx-jquants.com/', '별도 자료 범위 확인'),
    ], columns=['priority','dataset','minimum_fields','purpose','source_url','access_status'])


def parse_cash_prices(raw,identity):
    """Read a user's normalized local CSV; explicit cash identity prevents futures substitution."""
    if identity!='NIKKEI225_CASH':
        raise ValueError('Explicit NIKKEI225_CASH identity required; TOPIX or futures cannot substitute')
    df=pd.read_csv(io.StringIO(raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw))
    cols=['date','open','high','low','close']
    if set(cols)-set(df):raise ValueError('Expected normalized date/open/high/low/close columns')
    df=df[cols].copy()
    if df.empty or df.date.duplicated().any():raise ValueError('Empty or duplicated cash dates')
    if not df.date.astype(str).str.fullmatch(r'\d{4}-\d{2}-\d{2}').all():raise ValueError('ISO date required')
    pd.to_datetime(df.date,format='%Y-%m-%d',errors='raise')
    for col in cols[1:]:df[col]=pd.to_numeric(df[col],errors='raise')
    prices=df[cols[1:]]
    if not np.isfinite(prices).all().all() or not prices.gt(0).all().all():raise ValueError('Invalid cash price')
    if (df.high<df[['open','close','low']].max(axis=1)).any() or (df.low>df[['open','close','high']].min(axis=1)).any():raise ValueError('Invalid OHLC ordering')
    return df.sort_values('date').reset_index(drop=True)


def cash_baseline(prices):
    """Descriptive cash-price statistics only. This does not run H5 or H6."""
    data=prices.copy()
    data['log_return']=np.log(data.close/data.close.shift())
    # A zero observed range is preserved; never declared positive latent volatility.
    data['parkinson']=np.log(data.high/data.low)**2/(4*np.log(2))
    summary=dict(kind='private_cash_descriptive_only',days=len(data),start=data.date.min(),end=data.date.max(),
        returns=int(data.log_return.notna().sum()),zero_range_days=int(data.high.eq(data.low).sum()),
        mean_parkinson=float(data.parkinson.mean()),mean_log_return=float(data.log_return.mean()) if len(data)>1 else None,
        h5_executed=False,h6_executed=False,
        calendar_caveat='User must supply the complete Japanese trading calendar; gaps are not filled.',
        disclosure='Private input and output only; public statistics require source usage review.')
    return data,summary
