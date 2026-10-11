"""Offline contract-level CSVs, field profiles and research availability.

CSV is intentionally a plain interchange format. All master values are retained
as strings; unavailable market observations are blank, never simulated or zeroed.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .master import HEADER, load_master, weekly_name_candidate

SNAPSHOT = date(2026, 10, 11)
SOURCE = 'vendor/nh/2026-10-11/masters/fut_opt.mst.gz'
MASTER_NOTES = {
    'mrkt_tp': ('시장 구분 원코드', '코드', '필터 후보', '코드만으로 상품 종류 재분류 금지'),
    'fo_tp': ('선물·옵션 구분', '코드', '옵션 후보 선정', 'O 행 중 이름 규칙 적용'),
    'opt_tp': ('옵션 유형', '코드', '콜·풋 비교', '이 파일의 3=콜, 4=풋은 이름과 교차 확인'),
    'under_name': ('상품군 코드', '코드', '상품별 층화', 'WKI/WKM/WQI/WQM은 서로 다른 표본군'),
    'exp_ym': ('만기 원값', 'YYYYMMDD', 'H5 만기 구분', '문서명은 만기년월이나 이 파일 값은 8자리 날짜'),
    'cme_tp': ('세션', 'day/night', '주간·야간 비교', '동시점 시세를 의미하지 않음'),
    'class': ('분류 원코드', '코드', '현재 사용 불가', '현재 모든 행 공란'),
    'kospi_key': ('기초자산 연결 원키', '문자열', '코드 연결 검토', '주야간 차이 확인 후 연결'),
    'series': ('종목코드', '문자열', '계약 식별', '세션 원장 키는 cme_tp+series'),
    'rank_series': ('정렬용 종목코드', '문자열', '원문 보존', '식별키 대체 전 의미 확인'),
    'name_kor': ('한글 종목명', '문자열', '이름 기반 위클리 후보 선정', '거래소 인증 분류가 아님'),
    'name_eng': ('영문 종목명', '문자열', '이름 교차 검증', 'WEEK 이름 조건'),
    'upper_p_lv1': ('1단계 상한 가격 원값', '가격 원단위', '기준 밴드 정합성', '현재가·매도호가가 아님'),
    'lower_p_lv1': ('1단계 하한 가격 원값', '가격 원단위', '기준 밴드 정합성', '현재가·매수호가가 아님'),
    'strike_p': ('행사가', '지수 가격 단위', '콜풋 짝·행사가 범위', '기초자산 가격 없이 ATM 판단 불가'),
    'inst_grp_cd': ('상품 그룹 원코드', '문자열', '원문 코드 보존', '001 등 앞자리 0 유지'),
    'p_dec': ('가격 소수 자릿수', '자리수', '가격 표시 확인', '이를 호가 틱 크기로 간주하지 않음'),
    'ctrt_size': ('계약 승수 원값', '원문 승수', '후속 손익 단위 연결', '현행 상품 규정·단위 확인 후 금액 변환'),
    'rem_cnt': ('잔존일수 원값', '일', '세션 기준 진단', '다운로드 날짜 기준 남은 일수와 다를 수 있음'),
    'dynmc_yn': ('동적 가격제한 적용 원값', 'Y/N', '가격제한 원문 검토', '변동성 상태·거래 가능 여부로 해석 금지'),
    'dynmc_up_p': ('동적 상한 가격 원값', '가격 원단위', '원문 보존', 'dynmc_yn 및 기준 시각 확인 필요'),
    'dynmc_dn_p': ('동적 하한 가격 원값', '가격 원단위', '원문 보존', '현재 bid/ask 아님'),
    'real_Code': ('API 연결용 원코드', '문자열', '후속 시세 요청 매핑', 'series와 같음을 가정하지 않고 대조'),
    'kofex_Code': ('대체 종목 원코드', '문자열', '이종 코드 연결', '고유성 검증 후 사용'),
    'mrkt_code': ('시장 상세 원코드', '문자열', '원문 코드 보존', '03 등 앞자리 0 유지'),
    'trd_code': ('거래 상품 원코드', '문자열', '상품 연결 확인', '현행 코드표 대조 필요'),
}
DERIVED_NOTES = {
    'product_name': ('한글 상품명', '문자열', '상품명 검색·표시', '한글 종목명에서 콜풋·만기·행사가 부분을 제외한 원문 명칭'),
    'snapshot_date': ('파일 확보일', 'YYYY-MM-DD', '출처 시점', '거래소 관측 시각이 아님'),
    'source_file': ('원본 파일', '상대 경로', '재현 출처', '공개 파일 스냅샷'),
    'candidate_rule': ('선정 규칙', '문자열', '표본 정의', '공식 위클리 분류 아님'),
    'option_side': ('콜·풋', 'C/P', '대칭 계약 구성', '미확인 opt_tp는 공란'),
    'expiry_date': ('만기 날짜 변환', 'YYYY-MM-DD', 'H5 실제 만기 그룹', '정확한 만기시각은 별도 확인'),
    'expiry_weekday': ('만기 요일', '월~일', '요일·상품 혼동 진단', '만기 효과의 인과 추정치가 아님'),
    'calendar_dte_at_snapshot': ('확보일 기준 달력 잔존일', '일', '스냅샷 상대 날짜', 'exp_ym - 확보일; 실제 세션 잔존시간 아님'),
    'implied_reference_date': ('만기일-원문 잔존일 진단', 'YYYY-MM-DD', '세션 기준 차이 진단', '공급자 공표일·최신성 판정 아님'),
    'opposite_series': ('같은 세션의 반대 콜풋 코드', '문자열', '짝지은 체인 준비', '같은 상품·만기·행사가로 유일할 때만 연결'),
    'pair_status': ('반대 콜풋 짝 상태', 'matched/absent/ambiguous', '계약 구성 검증', '동시 호가·OI의 존재와 다름'),
    'session_difference_fields': ('같은 코드의 세션 간 차이 필드', '필드명 목록', '합치기 전 정합성 진단', '시점 차이에 따른 정상 차이일 수도 있음'),
    'market_data_status': ('시장 관측 가용 상태', '상태', '모델 착수 여부', '미확보 값을 0으로 대체하지 않음'),
}
NEEDED = {
    'last_pric': ('현재가', '가격 단위 확인 필요', '가격 경로·수익률', 'H5/H9b'),
    'bid_pric': ('최우선 매수호가', '가격 단위 확인 필요', '상대 스프레드·실행 가격', 'H9b'),
    'ask_pric': ('최우선 매도호가', '가격 단위 확인 필요', '상대 스프레드·실행 가격', 'H9b'),
    'trd_qty': ('거래량', '계약 수; 누적 규칙 확인', '유동성 통제', 'H5/H9b'),
    'pd_trd_qty': ('전일 거래량', '계약 수', '동일 시각 비교 검토', 'H9b'),
    'trd_amt': ('거래대금', '단위 확인 필요', '금액 유동성', 'H9b'),
    'opint': ('미결제약정', '계약 수', '당기 OI', 'H6'),
    'pd_opint': ('전일 미결제약정', '계약 수', 'ΔOI의 전기 분모', 'H6'),
    'ivol': ('내재변동성', '%/소수 스케일 확인', 'IV·스큐', 'H5/H6'),
    'delta': ('델타', '공급자 정의 확인', '민감도·헤지', 'H5'),
    'gamma': ('감마', '공급자 정의 확인', '감마 민감도', 'H5'),
    'theta': ('세타', '일/연 스케일 확인', '시간가치 변화', 'H5'),
    'vega': ('베가', '변동성 1%/1 단위 확인', 'IV 민감도', 'H5'),
    'rho': ('로', '금리 1%/1 단위 확인', '금리 민감도', '가격모형'),
    'spt_pric': ('현물 대상 가격', '대상 종목·단위 확인', '머니니스 기준 후보', 'H5/H6'),
    'theo_pric': ('공급자 이론가', '가격 단위 확인', '가격 비교', '가격모형'),
    'pd_sett_pric': ('전일 정산가', '가격 단위 확인', '전일 비교', '가격모형'),
}
FUTURE_DERIVED = {
    'relative_spread_bps': ('상대 스프레드', 'bp', '10000*(ask-bid)/((ask+bid)/2), 0<bid<=ask', 'H9b'),
    'oi_change_rate': ('OI 전기분모 변화율', '비율', '(opint-pd_opint)/pd_opint, 전기 OI>0', 'H6'),
    'oi_log_change': ('로그 OI 변화', '로그차', 'log1p(opint)-log1p(pd_opint)', 'H6'),
    'log_moneyness': ('로그 머니니스', '로그비율', 'log(K/F), 같은 시각의 적합한 선도가 필요', 'H5/H6'),
    'rv_daily': ('기초자산 세션 실현분산', '로그수익률 제곱 합', '동일 세션 5분 격자 수익률 제곱 합', 'H5/H6'),
    'rv_forward_5d': ('기초자산 다음 5거래일 누적 RV', '분산', 't+1부터 t+5까지 완결 라벨; 마지막 5일 결측', 'H6'),
}


def csv_bytes(rows, fields=None):
    fields = fields or list(rows[0])
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='raise', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def _number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def prepare_contracts(raw, snapshot=SNAPSHOT):
    """Preserve session records and consolidate only consistent identity values."""
    rows = [dict(r) for r in raw if weekly_name_candidate(r)]
    if len({(r['cme_tp'], r['series']) for r in rows}) != len(rows):
        raise ValueError('Duplicate session/series in source; resolve before exporting')
    rows.sort(key=lambda r: (r['under_name'], r['exp_ym'], float(r['strike_p']), r['opt_tp'], r['cme_tp']))
    groups, pair_index = defaultdict(list), defaultdict(list)
    for r in rows:
        groups[r['series']].append(r)
        pair_index[(r['cme_tp'], r['under_name'], r['exp_ym'], float(r['strike_p']), r['opt_tp'])].append(r['series'])
    differences = {
        series: [k for k in HEADER if k != 'cme_tp' and len({r[k] for r in rs}) > 1]
        for series, rs in groups.items()
    }
    for r in rows:
        expiry = datetime.strptime(r['exp_ym'], '%Y%m%d').date()
        opposite_type = {'3': '4', '4': '3'}.get(r['opt_tp'])
        pair = pair_index.get((r['cme_tp'], r['under_name'], r['exp_ym'], float(r['strike_p']), opposite_type), [])
        r.update(snapshot_date=snapshot.isoformat(), source_file=SOURCE,
                 product_name=re.split(r'\s+[CP]\s+', r['name_kor'], maxsplit=1)[0].strip(),
                 candidate_rule='fo_tp=O AND name contains 위클리/WEEK',
                 option_side={'3': 'C', '4': 'P'}.get(r['opt_tp'], ''),
                 expiry_date=expiry.isoformat(), expiry_weekday='월화수목금토일'[expiry.weekday()],
                 calendar_dte_at_snapshot=(expiry-snapshot).days,
                 implied_reference_date=(expiry-timedelta(days=int(r['rem_cnt']))).isoformat(),
                 opposite_series=pair[0] if len(pair) == 1 else '',
                 pair_status='matched' if len(pair) == 1 else ('absent' if not pair else 'ambiguous'),
                 session_difference_fields=';'.join(differences[r['series']]),
                 market_data_status='미확보: 국내 시세 EGW016; 마스터만 보유')
        r.update({k: '' for k in [*NEEDED, *FUTURE_DERIVED]})
    identity = ['series','real_Code','under_name','product_name','opt_tp','option_side','name_kor','name_eng',
                'exp_ym','expiry_date','expiry_weekday','calendar_dte_at_snapshot','strike_p','ctrt_size','p_dec']
    by_series = defaultdict(list)
    for r in rows:
        by_series[r['series']].append(r)
    contracts = []
    for series, rs in by_series.items():
        # A field that disagrees is explicitly blank, with the conflict recorded.
        out = {k: rs[0][k] if len({r[k] for r in rs}) == 1 else '' for k in identity}
        out['snapshot_date'] = snapshot.isoformat()
        out['sessions'] = ';'.join(sorted(r['cme_tp'] for r in rs))
        out['session_rows'] = len(rs)
        out['identity_conflict_fields'] = ';'.join(k for k in identity if len({r[k] for r in rs}) > 1)
        out['session_difference_fields'] = ';'.join(differences[series])
        for session in ('day', 'night'):
            r = next((r for r in rs if r['cme_tp'] == session), {})
            for key in ('rem_cnt','implied_reference_date','upper_p_lv1','lower_p_lv1','dynmc_yn','dynmc_up_p','dynmc_dn_p','opposite_series','pair_status'):
                out[f'{session}_{key}'] = r.get(key, '')
        out['market_data_status'] = rs[0]['market_data_status']
        out.update({k: '' for k in [*NEEDED, *FUTURE_DERIVED]})
        contracts.append(out)
    return rows, contracts


def _profiles(rows, catalog):
    price = next(a for a in catalog if a['metadata']['path'] == '/trade/v1/domestic/price')
    documented = {f['key']: f for f in price['output']}
    result, frequencies = [], []
    numeric = {'strike_p','ctrt_size','rem_cnt','p_dec','upper_p_lv1','lower_p_lv1','dynmc_up_p','dynmc_dn_p','calendar_dte_at_snapshot'}
    for key, (label, unit, use, caution) in {**MASTER_NOTES, **DERIVED_NOTES}.items():
        values = [r[key] for r in rows]
        populated = [str(v) for v in values if v != '' and v is not None]
        counts = Counter(populated)
        nums = [_number(v) for v in populated] if key in numeric else []
        nums = [v for v in nums if v is not None]
        result.append(dict(variable=key,label_ko=label,kind='마스터 원값' if key in MASTER_NOTES else '파생 진단',
                           status='확보' if populated else '원자료 공란',unit_or_format=unit,
                           denominator_rows=len(rows),observed_rows=len(populated),blank_rows=len(rows)-len(populated),
                           unique_values=len(counts),min_value=min(nums) if nums else '',max_value=max(nums) if nums else '',
                           examples='; '.join(list(counts)[:4]),analysis_use=use,source=SOURCE,caution=caution))
        for value, count in sorted(counts.items()):
            frequencies.append(dict(variable=key,value=value,count=count,denominator='세션 원장',share=count/len(rows)))
        if len(populated) < len(rows):
            frequencies.append(dict(variable=key,value='[공란]',count=len(rows)-len(populated),denominator='세션 원장',share=(len(rows)-len(populated))/len(rows)))
    for key, (label, unit, use, hypothesis) in {**NEEDED, **FUTURE_DERIVED}.items():
        if key in NEEDED and key not in documented:
            raise ValueError(f'Undocumented price field: {key}')
        result.append(dict(variable=key,label_ko=label,kind='미확보 API 관측' if key in NEEDED else '미계산 연구 변수',
                           status='미확보',unit_or_format=unit,denominator_rows=len(rows),observed_rows=0,blank_rows=len(rows),
                           unique_values=0,min_value='',max_value='',examples='',analysis_use=f'{hypothesis}: {use}',
                           source='/trade/v1/domestic/price' if key in NEEDED else 'docs/research-design.md',
                           caution='마스터에 없는 값; 문서 예제·PoC 가정은 관측값으로 사용하지 않음'))
    return result, frequencies


def export_contracts(root: Path, output_dir: Path | None = None):
    output = output_dir or root/'data/analysis/contracts'
    rows, contracts = prepare_contracts(load_master(root/SOURCE))
    catalog = json.loads((root/'data/catalog/catalog.json').read_text(encoding='utf-8'))
    variables, frequencies = _profiles(rows, catalog)
    summary = []
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r['under_name'], r['expiry_date'], r['cme_tp'])].append(r)
    for (product, expiry, session), rs in sorted(grouped.items()):
        strikes = sorted({float(r['strike_p']) for r in rs})
        gaps = [round(b-a,8) for a,b in zip(strikes,strikes[1:])]
        summary.append(dict(product=product,product_name=rs[0]['product_name'],expiry_date=expiry,session=session,contracts=len(rs),
                            calls=sum(r['option_side']=='C' for r in rs),puts=sum(r['option_side']=='P' for r in rs),
                            unique_strikes=len(strikes),min_strike=min(strikes),max_strike=max(strikes),
                            min_observed_strike_step=min(gaps) if gaps else '',max_observed_strike_step=max(gaps) if gaps else '',
                            matched_rows=sum(r['pair_status']=='matched' for r in rs)))
    readiness = [
        ('계약 식별·세션 비교','가능','series,cme_tp,session_difference_fields','세션 중복·차이를 분리','지금'),
        ('H5 만기·행사가 표본 설계','가능','exp_ym,strike_p,opt_tp,under_name','여러 독립 만기 시계열은 아직 없음','지금'),
        ('콜풋 짝 구성','가능','opposite_series,pair_status','동시 가격 확보 전 패리티 검정 불가','지금'),
        ('H5 만기 효과 예측 검증','미확보','calendar_dte_at_snapshot,rv_daily','분봉·세션 종료시각·휴장 캘린더 필요','1순위'),
        ('H6 OI와 미래 RV','미확보','opint,pd_opint,rv_forward_5d','OI 공표시각·롤·미래 완결 라벨 필요','1순위'),
        ('H9b 스프레드·거래비용','미확보','bid_pric,ask_pric,trd_qty','호가시각·잔량·실제 비용 필요','1순위'),
        ('IV 스마일·감마','미확보','ivol,gamma,log_moneyness','선도/현물 및 단위 검증 필요','2순위'),
        ('RFQ·보유집중도·기관 사건','외부 자료 필요','RFQ logs,position holdings,event dates','마스터·OI·투자자 순매수로 대체 불가','후속'),
    ]
    readiness = [dict(zip(('analysis','status','variables','remaining_requirement','priority'),r)) for r in readiness]
    assumptions = [
        ('S',100,'정규화 가격','H5'),('K',100,'정규화 가격','H5'),('sigma',0.25,'연 변동성 소수','H5'),
        ('tenor',7,'달력일','H5'),('oiPrev',10000,'가정 계약 수','H6'),('oiNow',12000,'가정 계약 수','H6'),
        ('horizon',5,'미래 거래일','H6'),('edge',20,'가정 bp','H9b'),('fee',2,'편도 bp','H9b'),('slip',1,'편도 bp','H9b'),
    ]
    assumptions = [dict(variable=k,value=v,unit=u,hypothesis=h,status='PoC 기본 가정; 실측 아님') for k,v,u,h in assumptions]
    assumptions += [dict(variable=f'rv_example_day_{i+1}',value=v,unit='RV ×10^-4',hypothesis='H6',status='고정 합성 예시; 실측 아님') for i,v in enumerate([1,1.2,.9,1.3,1.7,1.4,1.1,.8,1.2,1.5,1,.9])]
    files = {
        'weekly_contracts.csv': csv_bytes(contracts),
        'weekly_contract_sessions.csv': csv_bytes(rows),
        'variable_dictionary.csv': csv_bytes(variables),
        'variable_value_counts.csv': csv_bytes(frequencies),
        'product_expiry_session_summary.csv': csv_bytes(summary),
        'analysis_readiness.csv': csv_bytes(readiness),
        'poc_assumptions.csv': csv_bytes(assumptions),
    }
    for product in sorted({r['under_name'] for r in contracts}):
        files[f'products/{product}.csv'] = csv_bytes([r for r in contracts if r['under_name']==product])
    output.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    per_symbol = defaultdict(list)
    for r in rows:
        per_symbol[r['series']].append(r)
    stats = dict(snapshot_date=SNAPSHOT.isoformat(),session_rows=len(rows),unique_contracts=len(contracts),
                 day_rows=sum(r['cme_tp']=='day' for r in rows),night_rows=sum(r['cme_tp']=='night' for r in rows),
                 night_only_contracts=sum(r['sessions']=='night' for r in contracts),
                 matched_pair_rows=sum(r['pair_status']=='matched' for r in rows),
                 identity_conflicts=sum(bool(r['identity_conflict_fields']) for r in contracts),
                 session_difference_contracts=sum(bool(r['session_difference_fields']) for r in contracts),
                 variable_count=len(variables),raw_fields=len(HEADER),missing_market_fields=len(NEEDED)+len(FUTURE_DERIVED),
                 inferred_dates=dict(Counter(r['cme_tp']+':'+r['implied_reference_date'] for r in rows)))
    instructions = f'''위클리옵션 종목별 CSV 패키지\n확보일: {SNAPSHOT.isoformat()} (시장 관측시각 아님)\n\nweekly_contracts.csv: 고유 계약 {len(contracts)}행. 상충하는 식별 속성은 공란+identity_conflict_fields.\nweekly_contract_sessions.csv: 원본 26필드와 진단, 미확보 변수. {len(rows)}행. 키=cme_tp+series.\nproducts/: 상품군별 고유 계약 CSV 4개.\nsymbols/: 계약코드별 CSV {len(per_symbol)}개. 각 파일 1~2행, 주간·야간 원값 보존.\nvariable_dictionary.csv: 변수별 의미·실제 예시·범위·공란 수·분석 용도. 분모는 세션 원장.\nvariable_value_counts.csv: 모든 관측값의 빈도. 서로 다른 세션을 독립 계약으로 세지 마세요.\nproduct_expiry_session_summary.csv: 상품·만기·세션별 행사가 범위와 관측 간격. 공식 행사가 간격/누락 판정이 아님.\nanalysis_readiness.csv: 지금 가능한 분석과 필요한 다음 자료.\npoc_assumptions.csv: 가정값만 분리. 종목별 시장 관측값에 섞지 않습니다.\n\nUTF-8 BOM. Excel에서는 데이터 > 텍스트/CSV로 가져오기, 코드 열을 텍스트로 지정하세요(001/03 등 0 보존).\n빈칸은 미확보/원문 공란/세션 부재입니다. 0이 아닙니다. market_data_status와 변수 사전을 확인하세요.\nexp_ym-rem_cnt는 진단값이며 공표일이 아닙니다. calendar_dte_at_snapshot은 확보일 기준 달력 차이입니다.\nupper_p_lv1/lower_p_lv1은 가격제한 원값으로 bid/ask가 아닙니다.\n내재변동성·OI·Greeks·RV는 미확보입니다. 모의 인증 성공은 시세조회 성공을 의미하지 않습니다.\n'''
    files['READ_ME.txt'] = instructions.encode('utf-8-sig')
    for series, rs in per_symbol.items():
        if not series.isalnum():
            raise ValueError('Unexpected symbol filename')
        files[f'symbols/{series}.csv'] = csv_bytes(rs)
    manifest = dict(stats=stats,source=SOURCE,source_sha256=hashlib.sha256((root/SOURCE).read_bytes()).hexdigest(),
                    files={name:dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest()) for name,content in files.items()})
    files['manifest.json'] = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    (output/'summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    archive_path = root/'docs/downloads/weekly_option_data.zip'
    archive_path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive_path,'w') as archive:
        for name, content in files.items():
            info = zipfile.ZipInfo(name,date_time=(2026,10,11,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info,content)
    return dict(contracts=contracts,sessions=rows,variables=variables,readiness=readiness,
                assumptions=assumptions,summary=summary,stats=stats,archive=archive_path)
