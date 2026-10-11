# 가격회귀율(REV) 분석 실행과 가능성 검토

**계산·검증 경로를 구현하고 공개 자료 가용성 분석을 실행했다. 실제 시장의 REV 효과 추정은 가격 이력과 거래일 캘린더가 없어 아직 불가능하다.** 보존된 2026-10-11 마스터를 사용하며 컷오프는 같은 날 09:00 KST다. 효과가 없다는 결론이 아니다.

## 이번 실행 결과

| 항목 | 결과 | 의미 |
|---|---:|---|
| 입력 고유 계약 | 766 | 콜풋·행사가별 종목 수 |
| 기초자산 × 만기일 후보 | 6 | KOSPI200 / KOSDAQ150 × 10-12, 10-15, 10-19 |
| 서로 다른 만기 날짜 | 3 | 같은 날 두 지수도 독립 사건으로 단정하지 않음 |
| 컷오프 이후 만기 | 6/6 | 완료된 만기 사건 없음 |
| 확보한 가격 지점 | 0/30 | 사건당 필요한 가격 5개 모두 없음 |
| REV1 / REV2 / REV3 실측 표본 | 0 / 0 / 0 | 평균·중앙값·양수 비중은 공란 |
| 효과 추정치 / p-value | 미산출 | 0 또는 ‘유의하지 않음’으로 채우지 않음 |

실행 산출물: [manifest](../data/analysis/reversal/manifest.json), [사건별 상태 CSV](../data/analysis/reversal/event_results.csv), [실측 요약 CSV](../data/analysis/reversal/summary.csv). 입력은 공개 계약 CSV이며 키나 비공개 시세를 읽지 않는다. 저장된 로컬 수집 기록은 인증 성공 후 국내 현재가·일봉·분봉에 `403 / EGW016`을 반환한 상태다. 이번 분석에서 API 권한 승인 여부를 새로 확인하거나 인증을 재시도하지 않았다.

![실제 자료 가용성](images/reversal_feasibility.png)

회색 막대는 **확보량이 아닌 필요 가격 5개**다. 각 행의 `0/5`가 관측 결과다. 766계약을 복제한 수익률로 표본 수를 늘리지 않는다. 상·하한 가격, 행사가, 잔존일수는 기초자산 가격 이력을 대체할 수 없다.

## 이번 연구의 정의

사용자 제공 `위클리 옵션 모델 기획서.pdf` p.8과 `expiry_reversal_analysis.py`의 시가·1분·30분 구분을 따른다. 이는 회귀분석의 R²나 평균회귀 속도가 아닌 **전일 마지막 30분 방향에 부호를 맞춘 다음 장 수익률**이다.

```text
P−30 = 사건일 장 마감 30분 전의 동일 기초자산 가격
Pc   = 사건일 해당 세션 종가
Ph   = 다음 거래 세션의 시가 / 시가+1분 / 시가+30분 가격
rpre = Pc / P−30 − 1
REVh = −sign(rpre) × (Ph / Pc − 1)
출력 rev1_bp / rev2_bp / rev3_bp = REVh × 10,000
```

양수는 반전, 음수는 지속이다. 전일 변화가 0이면 방향을 정의할 수 없어 결측이다. 다음 장 가격이 전일 종가와 같으면 유효한 0이다. `--min-pre-move-bp`로 미세한 전일 움직임을 제외하는 민감도 분석을 할 수 있으며 기본 0은 정확한 무변화만 제외한다. 모든 수익률은 단순 수익률이다.

REV는 복원된 가격 변화의 비율이 아니다. 가정 가격 `100 → 101 → 100`의 REV는 `+99.01bp`이고, 가격이 원점에 돌아왔다는 이유로 `+100%`라고 쓰지 않는다. `100 → 99 → 100`은 `+101.01bp`로 종가 분모 차이 때문에 대칭이지 않다. `100 → 101 → 102`는 `−99.01bp`다.

선행문헌에서도 REV라는 명칭에 서로 다른 정의를 사용한다. 자본시장연구원의 2012년 보고서 pp.28–30은 장마감 동시호가를 기준으로 별도의 REV1·REV2 척도를 설명한다. **그 수치와 이번 프로젝트 REV1·REV2·REV3를 같은 지표로 결합하거나 재현했다고 주장하지 않는다.** [원문: 주가지수파생상품 만기일 효과에 관한 연구](https://www.kcmi.re.kr/kcmifile/oldreportdata/0000256_2.pdf)

원래 로컬 `expiry_reversal_analysis.py`는 난수로 H/L 차익거래 비중 그룹과 수익률 반전을 주입한 합성자료다. 그 평균·유의확률을 시장의 발견으로 사용하지 않았다. 신규 예시도 직접 지정한 네 경로로 제한하고 통계 분석 입력과 구분했다.

![명시적 가정의 수식 검증](images/reversal_formula_examples.png)

왼쪽은 지정한 가격 경로, 오른쪽은 같은 가격의 REV다. 되돌아오는 두 경로는 양수, 상승이 이어지는 경로는 음수다. 시장 관측이나 모형 적합 결과가 아니다. [예시 CSV](../data/analysis/reversal/formula_examples.csv)의 `observation_type=mathematical_example`을 유지한다. 단일 HTML의 ‘가격회귀율 REV’에서 가격을 바꾸고 두 차트를 확인할 수 있다.

## 실측 입력과 재실행

공개 가용성 분석 및 PNG 재생성:

```sh
python scripts/analyze_reversal.py
python scripts/build_poc.py --output docs/downloads/weekly_option_poc.html --zip
```

실제 자료를 확보하면 아래 세 CSV를 `data/private/`에 준비한다. 시각은 초 단위 ISO 8601 `+09:00` KST, 파일은 UTF-8(선택적으로 BOM)이다. 가격 단위·심볼 연결은 입력자가 검증해야 한다.

| 입력 | 필수 열 | 준비 규칙 |
|---|---|---|
| events.csv | `underlying_id,event_date,event_type,price_kind,price_symbol,expiry_source` | 기초자산/날짜당 한 행. `event_type=expiry/control`, `price_kind=cash_index/future_proxy`. 실제 종료한 사건과 대조일 추가 |
| calendar.csv | `price_symbol,session_date,open_at,close_at,source` | 해당 구간의 **모든 거래 세션**을 빠짐없이 기재. 휴일·단축장·특별 개장시간 및 출처 반영 |
| prices.csv | `price_symbol,timestamp,price,observation_type,source` | `observation_type=observed`; 양의 유한 가격. 동일 심볼/시각 중복 사전 해소 |

후보 입력: [event_candidates.csv](../data/analysis/reversal/event_candidates.csv). `price_symbol`은 검증된 현물지수 코드가 없어 비워 두었다. NH에서 현물지수 분봉을 제공한다고 가정하지 않는다. [캘린더 헤더](../data/analysis/reversal/calendar_template.csv), [가격 헤더](../data/analysis/reversal/prices_template.csv)는 실제 캘린더·시세가 아닌 입력 양식이다.

```sh
python scripts/analyze_reversal.py --events data/private/events.csv --calendar data/private/calendar.csv --prices data/private/prices.csv --as-of 2026-10-20T10:00:00+09:00
# 전일 마지막 30분의 절대 변화가 1bp 미만인 사건 제외
python scripts/analyze_reversal.py --events data/private/events.csv --calendar data/private/calendar.csv --prices data/private/prices.csv --as-of 2026-10-20T10:00:00+09:00 --min-pre-move-bp 1
```

실측 입력 실행은 `artifacts/private/reversal/`의 사건별 결과·요약·입력 해시와 설정을 덮어쓴다. 민감도 실행 간 비교하려면 실행 후 별도 폴더에 보존한다. 공개 결과/HTML로 자동 복사하지 않는다. 현재 공개 HTML은 저장된 마스터의 가용성 분석으로 고정되어 있다.

엔진은 캘린더의 다음 행을 다음 거래일로 사용한다. **캘린더의 진위·완전성은 엔진이 증명할 수 없으므로 공급자 자료와 대조해야 한다.** 주말 계산이나 목요일 고정 규칙으로 보충하지 않는다. 주간 세션 분석 전용이며 야간 세션을 넘는 종가/시가 정의는 별도 설계가 필요하다.

지정 시각과 정확히 일치하는 관측만 사용한다. 미래 컷오프 이후 값, 결측, 다른 계약으로의 롤, 중복을 자동으로 채우지 않는다. 시가만 확보되면 REV1만 계산한다. 결과 CSV에 각 가격·시각·출처·탈락 사유가 남는다. 엄격한 일치 정책은 거래가 드문 상품을 제외할 수 있으므로 추후 결측 편향을 보고해야 한다.

## NH 연동과 후속 실증

1. 국내 시세 권한 승인 후 기존 `collect_demo.py`로 읽기 전용 수집을 재시도한다. 현재 마스터로 과거 만기 이력을 만들 수 없으므로 과거 마스터나 출처 있는 실제 만기 캘린더가 추가로 필요하다.
2. `domestic/chart-minute`의 `dcnt=1`, 연속조회·역사 조회 범위를 확인한다. `occurs1_ref_dt`, `occurs1_exch_tm` 및 OHLC 필드를 실응답과 대조한다. **분봉 시각이 시작/종료 중 무엇인지, 개장 첫 거래와 종가 단일가를 어떻게 기록하는지** 확인하기 전에는 자동 변환기를 연결하지 않는다. [보존된 API 명세](api-catalog.md)
3. 현물지수 시계열 대신 선물을 쓰면 같은 만기 계약을 전후에 추적한 별도 `future_proxy` 분석으로 구분한다. 모든 지점에서 같은 심볼이어야 한다. 현물 가격 왜곡 효과라고 부르거나 만기 소멸 옵션의 ‘다음날 가격’을 사용하지 않는다.
4. 같은 기초자산·요일·시기의 비만기 대조군, 동시만기, 금리 발표·야간 뉴스, 시장 국면을 확보한다. 날짜/주 단위 의존성을 고려한 블록 부트스트랩·회귀 추론은 충분한 날짜가 생긴 후 사전 규약에 따라 추가한다. 현재 요약은 기술통계만 제공한다.
5. 차익거래 비중의 정의·분모·당시 가용시각을 확보하기 전에는 H/L 비교를 보류한다. 확보 후에도 미래 정보를 사용한 전체 표본 중앙값 분할을 피하고 사전 기간에서 기준을 정한다. 세 시점과 여러 대조군의 다중 비교를 관리한다.

양의 REV는 ‘반대 방향 움직임’의 관측이다. 정상가격으로의 복귀, 만기 효과의 인과성, 차익거래 청산, 수익성은 이것만으로 입증하지 못한다.
