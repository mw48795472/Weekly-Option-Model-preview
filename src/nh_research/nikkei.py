"""Nikkei expansion readiness and private cash-index baselines.
TAIFEX TOPIX/TJF is never relabelled as Nikkei225. No synthetic market observations.
"""
from __future__ import annotations
import io
import numpy as np
import pandas as pd

PRODUCT_URL='https://www.taifex.com.tw/enl/eng2/products'
OSE_URL='https://www.jpx.co.jp/english/derivatives/products/domestic/225mini-options/01.html'
PRICE_URL='https://www.jpx.co.jp/english/markets/derivatives/option-price/01.html'
DAILY_URL='https://www.jpx.co.jp/english/markets/statistics-derivatives/daily/'
NIKKEI_URL='https://indexes.nikkei.co.jp/nkave/data/index.en.html'


def readiness(manifest):
    requests=manifest.get('requests',[])
    success=sum(bool(r.get('complete')) for r in requests)
    # Request success is transport evidence only, never evidence that Nikkei is listed.
    return dict(version='nikkei-readiness-20261013',verified_at='2026-10-13',
        status='data_unavailable',taifex_nikkei_listed=False,
        correct_venue='OSE',correct_product='Nikkei 225 mini Options',
        taifex_japan_product='TOPIX futures (TJF)',nikkei_observations=0,
        option_oi_observations=0,h5_executed=False,h6_executed=False,
        api_requests=len(requests),api_success=success,
        requested_start='2025-01-02',requested_end='2026-10-08',
        actual_start=None,actual_end=None,
        product_evidence='Official product page; not an API response audit',
        reason='TAIFEX does not list Nikkei225 in its official product catalog. OSE/Nikkei source files were not acquired.',
        public_raw_redistribution=False)


def status_table():
    rows=[
      ('상품 식별','공식 확인','TAIFEX 일본 상품은 TOPIX/TJF. Nikkei225 실측은 OSE로 별도 구성.',PRODUCT_URL),
      ('TAIFEX API','원본 미확보','두 요청 모두 로컬 네트워크 권한 오류. 서비스 HTTP 응답/종목코드 결과로 해석하지 않음.','https://openapi.taifex.com.tw/'),
      ('OSE 계약 규격','공식 확인','Mini: JPY100, 2023-05-29 개시. 수요일 만기 2025-05-26 도입. 최종거래일과 SQ일 구분.',OSE_URL),
      ('Nikkei 현물 OHLC','미수집','공식 공개 일별 자료 안내는 확인. 이번 작업에서 원본 검증 및 통계 계산 미실행.',NIKKEI_URL),
      ('OSE 옵션 CSV','필드 안내 확인','최근 약2개월 이론가격/종가/기초지수 종가 안내. OI 시계열 확보를 뜻하지 않음.',PRICE_URL),
      ('H5·H6','미실행','실제 기초지수+옵션 OI+계약별 최종거래/SQ 및 가용시각 필요.',DAILY_URL),
      ('공개 배포 권한','별도 확인 필요','공개 열람과 원본·파생데이터 재배포 허가는 다름. 로컬 원본은 Git 및 다운로드 제외.',NIKKEI_URL)]
    return pd.DataFrame(rows,columns=['stage','state','detail','source_url'])


def required_data():
    rows=[
      ('P0','Nikkei225 현물 OHLC','date,open,high,low,close,timezone,available_at','일별 Parkinson·수익률 비교; 현물과 선물 구별',NIKKEI_URL,'공개 조회 가능 안내; 미수집·재배포 허가 확인'),
      ('P0','OSE mini 옵션 일별 전 계약','date,contract_id,expiry_date,last_trade_date,strike,side,oi,volume,close,settlement,available_at','동일 계약 OI 변화·진입/소멸 분해 및 H6',DAILY_URL,'일보 안내 확인; 장기 원문 미확보'),
      ('P0','OSE 계약 마스터·실제 SQ','contract_id,multiplier,currency,last_trade_date,sq_date,listing_date,holiday_adjustment','H5 사건일·월간SQ·수요일 제도변경; 계약 규모 정규화',OSE_URL,'규격 확인; 실제 역사 달력 미확보'),
      ('P0','이용·재배포 허가','provider,license_scope,derived_statistics,display,redistribution,retention','GitHub/Streamlit 공개 범위 확정','https://www.jpx.co.jp/english/term-of-use/index.html','확인 필요; 원본 비공개 기본'),
      ('P1','Nikkei225 intraday 현물·호가','exchange_time,receive_time,price,bid,ask,session','SQ 시초가와 일중/야간 변동성 구분; 일봉 대리변수 오차 축소',NIKKEI_URL,'장기 세부자료 별도 계약 범위'),
      ('P1','옵션 IV·호가·Greeks','contract_id,iv,bid,ask,delta,gamma,calculation_time','ATM·DTE·가격민감도 가중 OI; 이론가격과 체결 구분',PRICE_URL,'최근 공개 CSV 안내; 전체 역사/호가 미확보'),
      ('P1','일본 뉴스·배당·구성변경·금리·환율','event_time,event_type,dividend,index_divisor,rate,JPY_TWD','H5 교란 및 한·대·일 비교 시통제',NIKKEI_URL,'원천별 확보·라이선스 필요')]
    return pd.DataFrame(rows,columns=['priority','dataset','minimum_fields','purpose','source_url','access_status'])


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
