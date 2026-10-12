# 일본: JPX J-Quants Pro와 개별 계약 데이터

조사 기준: 2026-10-12 KST. 공식 명세·상품 규격을 읽은 기술 조사이며 유료 계정 인증, 원시 데이터 구매, 실제 API 데이터 수집은 실행하지 않았다. 저장소 수정이나 PR 작업은 없다.

## 1. 무엇을 얻을 수 있는가

### Takeaway
J-Quants Pro의 옵션·선물 가격 API는 일별 및 세션별 집계 자료다. 신설된 1분 API는 현물주식용이며 선물·옵션·지수 1분 자료를 제공하지 않는다. 지수 위클리의 장중 RV·REV에는 별도 DataCube 파일 조달이 필요하다.

### Cited Findings

| 데이터 | 조회 경로 / 주요 필드 | 시간·역사 범위 | 공식 근거 |
|---|---|---|---|
| 옵션 일별/세션 OHLC | /v2/derivatives/options. 가격·거래량·OI·정산가격·IV·기초가격·금리, 개별 계약 코드·행사가·콜풋·최종거래일·SQ | 매일 22:00 JST 제공. 세션 OHLC와 별개로 OI는 한 개의 일별 필드 | [옵션 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/options), [갱신표](https://jpx.gitbook.io/j-quants-pro/data-update) |
| 선물 일별/세션 OHLC | /v2/derivatives/futures. OHLC·거래량·OI·정산가격·중심월물 flag | 매일 22:00 JST. 일반 역사표 2008-05-07부터이나 상품별 상장일·코드표를 적용 | [선물 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/futures), [역사표](https://jpx.gitbook.io/j-quants-pro/data-spec) |
| 계약별 OI | /v2/derivatives/open_interest_by_issue. SeriesCode, ProductCode, 전일/당일 OI, 청산·행사수량, 최종결제일 | 2021-06-14~. 영업일 19:00 JST 기준을 약 21:15 공개 | [계약별 OI](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue), [역사표](https://jpx.gitbook.io/j-quants-pro/data-spec) |
| 참가자별 OI | /v2/derivatives/open_interest_by_participant. 계약·참가자·매도/매수 구분·순위·보유량 | 2016-12-02~. 주말 기준, 다음 주 첫 영업일 15:30 공개 | [참가자 OI](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_participant), [역사표](https://jpx.gitbook.io/j-quants-pro/data-spec) |
| 참가자별 거래량 | /v2/derivatives/volume_by_participant. 계약명·계약코드·참가자·주야간·Auction/J-NET 구분·수량 | 2014-03-24~. 매일 17:30 JST | [거래량 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/volume_by_participant), [갱신표](https://jpx.gitbook.io/j-quants-pro/data-update) |
| 현물주식 1분봉 | /v2/equities/bars/minute. Date,Time,Code,O,H,L,C,Vo,Va | 최근 36개월 이동창. 거래 당일 16:30 JST 배포. Time은 분 시작시각/JST, 수량 주·거래대금 JPY | [1분 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/equities_bars_minute) |

- 현물 1분은 TSE 주식·ETF·ETN·REIT 등을 포함하지만 선물·옵션·지수와 PTS는 제외한다. 무거래 분은 행이 없고, 가격은 분할 전후 무조정이다. 따라서 빠진 분을 거래량 0과 가격 0으로 채우면 안 된다. [1분 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/equities_bars_minute)
- 옵션 가격 코드표: NK225E=표준 Nikkei225 옵션 2008-05-07~, NK225MWE=mini 2023-05-29~, TOPIXE=TOPIX 2008-05-07~, JGBLFE=JGB 선물옵션 2008-05-07~, EQOP=개별증권 옵션 2014-11-17~. 역사표의 가장 오래된 날짜를 모든 상품에 적용하지 않는다. [Pro 옵션 코드표 일본어](https://jpx.gitbook.io/j-quants-pro-ja/api-reference/options/codelist)
- 옵션 상세 필드의 일부(최종거래일·SQ·정산가·이론가·IV·금리 등)는 2016-07-19부터 제공된다. 응급증거금 산출과 일상 정산 레코드가 같은 날 존재할 수 있어 키는 TradeDate+Code+EmergencyMarginTriggerDivision이다. 001은 응급 산출, 002는 정산가 산출이다. [옵션 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/options)

### Inferences
- 옵션 API의 NightSession/DaySession OHLC가 있다고 해서 세션별 OI·장중 IV 시계열이 생기는 것은 아니다. 시점 정합성을 위해 계약별 OI의 19:00 기준/21:15 공개와 가격파일의 22:00 배포를 따로 저장해야 한다.
- Pro 일별 자료로 H5·H6의 일별 특징과 만기 패널을 만들 수 있다. 원래 1분 실현변동성·개장 후 1/30분 REV 검증에는 DataCube 등 장중 자료가 추가로 필요하다.

### Gaps
- 옵션 OHLC API에 포함된 OI가 별도 OI 파일의 19:00 값과 항상 완전히 일치하는지, 이론가/IV 각 필드의 정확한 평가시각·단위(퍼센트 대 소수)와 계산모형은 공급자 확인 필요. 공개 명세의 숫자 예만 보고 /100 변환을 확정하지 않는다.
- Pro 미니 가격의 2023 이전 선행상품 Nikkei225 Weekly 이력이 같은 코드로 포함되는지는 확인되지 않았다. 공식 미니 시작일은 2023-05-29이다.

## 2. 인증·조회·일괄 수집 구조

### Takeaway
Pro는 데이터셋별 계약 후 발급받는 계정으로 토큰을 얻는 기업용 서비스다. 개인용 J-Quants V2의 API Key 인증과 섞으면 안 된다.

### Cited Findings
- Base URL은 https://api.jquants-pro.com/v2. POST /token/auth_user JSON body는 mailaddress,password이고 idToken,refreshToken을 반환한다. refreshToken은 1주, idToken은 24시간 유효. 조회 헤더는 Authorization: Bearer <idToken>. [Pro 인증](https://jpx.gitbook.io/j-quants-pro/api-reference/refreshtoken), [시작 절차](https://jpx.gitbook.io/j-quants-pro/getstarted)
- POST /token/auth_refresh는 refreshtoken으로 ID token을 갱신한다. 이 항목은 공식 문서가 request body라고 명시한다. [갱신 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/idtoken)

| 조회 | 필수/선택 query | 응답 배열 | 근거 |
|---|---|---|---|
| /derivatives/options | date 필수. category, code, contract_flag, pagination_key 선택. code는 EQOP의 기초주식 코드(4/5자리)이지 옵션 계약코드가 아님 | options | [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/options) |
| /derivatives/futures | date 필수. category, contract_flag, pagination_key 선택 | futures | [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/futures) |
| /derivatives/open_interest_by_issue | date 필수, product_code, pagination_key 선택 | open_interest_by_issue | [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue) |
| /derivatives/open_interest_by_participant | category,date,pagination_key. 문서 표에는 date 필수 표시가 없으나 생성일을 지정해 수집할 것 | open_interest_by_participant | [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_participant) |
| /derivatives/volume_by_participant | date 필수. category,pagination_key 선택 | volume_by_participant | [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/volume_by_participant) |
| /equities/bars/minute | code 또는 date 필수. code와 from,to로 기간 조회. date가 함께 있으면 from,to 무시 | data | [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/equities_bars_minute) |

- 옵션/선물 OHLC에는 from/to query가 없다. 날짜별 전 계약을 받아 로컬에서 기간·개별계약을 묶는다. contract_flag=1은 중심월물만, 0은 중심월물 이외만, 미지정은 둘 다이다. 전체 체인 연구에서 1로 고정하면 표본이 누락된다. [옵션](https://jpx.gitbook.io/j-quants-pro/api-reference/options), [선물](https://jpx.gitbook.io/j-quants-pro/api-reference/futures)
- 응답 pagination_key를 동일 검색조건에 붙여 반복하고 없어지면 종료한다. 수치형 고정 rate limit은 문서에 공개되지 않았으며 제한이 존재한다. [공통주의](https://jpx.gitbook.io/j-quants-pro/api-reference/attention)
- 대량 역사자료는 SFTP sftp-v2.jquants-pro.com:22, 등록 계정/비밀번호 사용, 별도 SSH 키는 불필요하다. 구독한 데이터만 디렉터리에 표시되며 historical/live 파일 구조다. Snowflake도 제공하지만 개별 데이터셋 사용권을 확인해야 한다. [SFTP](https://jpx.gitbook.io/j-quants-pro/sftp-specifications), [계약 절차](https://jpx.gitbook.io/j-quants-pro/getstarted)
- 개인용 J-Quants는 별도 제품이며 2025년12월 V2에서 token→API key 인증으로 변경되었다. 그 개인용 endpoint/헤더를 Pro 위 경로에 그대로 넣지 않는다. 개인용 장중 add-on 역시 equities 대상이다. [JPX 2026-01-19 공식 발표](https://www.jpx.co.jp/english/corporate/news/news-releases/6020/20260119.html)

### Inferences
- 요청 형태 예: GET /derivatives/options?date=2026-10-09&category=NK225MWE, 개별증권은 GET /derivatives/options?date=2026-10-09&category=EQOP&code=7203. 이는 명세에 따른 요청 예시이며 실제 응답을 수집한 것은 아니다.
- 수집기에는 최초 SFTP backfill + 매일 API delta, 원문응답/다운로드 시각/공표시각/구독권한/스키마 버전 저장을 권한다.

### Gaps
- 개인용 J-Quants의 최신 옵션 endpoint별 미니/개별증권 커버리지는 이 조사에서 직접 검증하지 않았다. Pro 커버리지를 개인용에 전이하지 않는다.
- 인증 계정이 없으므로 구독별 권한·실제 payload·수치형 rate limit은 실호출로 확인하지 않았다. Pro는 데이터별 구독이 필요하며 개인 자격 계약 가능 여부는 영업 문의 대상이다.

## 3. 개별 상장 계약과 single-stock weekly의 구분

### Takeaway
Nikkei225 mini의 콜/풋·행사가·실제 만기별 계약은 수집 대상에 포함할 수 있다. 그러나 일본 표준 single-stock 옵션을 weekly라고 분류하면 안 된다. 일반 개별증권 옵션은 월물이고 J-NET flexible는 별도 거래방식이다.

### Cited Findings
- Nikkei225 mini는 2023-05-29 상장, 수요일 만기는 2025-05-26 추가. 현재 금요일 둘째 주 정규월물 3개, 나머지 금요일 4개, 수요일 4개로 11개 만기구조이며 승수는 옵션가격×JPY100이다. 수요일/둘째 금요일 이외 금요일을 weekly로 분류한다. [JPX 규격](https://www.jpx.co.jp/derivatives/products/domestic/225mini-options/01.html), [개요](https://www.jpx.co.jp/english/derivatives/products/domestic/225mini-options/)
- 최종거래일은 SQ의 전 영업일, 최종결제는 SQ 현금결제다. 휴일에 따른 앞당김을 실제 날짜로 적용해야 한다. [상품 규격](https://www.jpx.co.jp/derivatives/products/domestic/225mini-options/01.html)
- 월·화·목 만기 추가는 2026-03-26 발표상 2027년4월 시행 예정이다. 현재 만기목록에 추가하지 않는다. [2026 공식 발표](https://www.jpx.co.jp/english/news/2040/20260326-01.html)
- 일반 Securities Options는 직전 2개 월물과 3월 주기 2개 월물, 둘째 금요일 전 영업일 최종거래/행사, European 방식이다. 표준 weekly 계약 규격이 아니다. 기초자산은 개별주식뿐 아니라 ETF/REIT도 포함한다. [일반 개별증권 규격](https://www.jpx.co.jp/english/derivatives/products/individual/securities-options/01.html), [기초자산 개요](https://www.jpx.co.jp/english/derivatives/products/individual/securities-options/index.html)
- Flexible 옵션은 J-NET off-auction 전용이며 개별증권은 최대3년의 일자별 만기 설정, 최소5영업일 계약기간으로 물리/종가현금결제가 가능하다. 이 맞춤형 단기 계약을 표준 주간 상장상품과 합치지 않는다. [Flexible 규격](https://www.jpx.co.jp/english/derivatives/rules/flexible/index.html)
- 계약별 OI ProductCode에는 NK225MWE와 개별증권 XXXX+E, flexible XXXX+E+FL/XXXX+CE+FL 등이 명시되어 있다. 참가자별 OI의 별도 코드표에는 TOPIXF,NK225F,NK225MF,NK225E,EQOP만 제시되어 NK225MWE 포함을 확정할 수 없다. [Issue OI 상품표](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue/productlist), [Participant OI 상품표](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_participant/codelist)
- OI 데이터에는 합계행도 들어오므로 DataType=IssueData를 계약 테이블에 사용한다. ContractMonthTotalData/PutCallTotalData/ProductTotalData와 함께 더하면 중복 집계다. [OI 코드표](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue/codelist)
- 참가자 거래량은 Executing Participant, 참가자 OI는 Carrying Participant 기준이므로 Give-up 전후 동일 주체의 흐름·잔고라고 보장되지 않는다. 2023-11-06 이후 거래량은 매수·매도 분리 대신 합산 공개된다. [거래량 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/volume_by_participant), [OI 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_participant), [거래량 코드표](https://jpx.gitbook.io/j-quants-pro/api-reference/volume_by_participant/codelist)

### Inferences
- 표준 계약의 공통키: exchange+product_code+raw_contract_code+put_call+strike+actual_last_trade_date+actual_settlement_date. 이름·승수·행사방식·결제방식·standard/flexible·monthly/weekly와 효력기간을 함께 보관한다.
- 미니 ContractMonth는 YYYY-MM처럼 보여도 MM이 일반 월이 아니다. 월로 파싱하거나 Code를 숫자로 캐스팅하지 말고, LastTradingDay/SpecialQuotationDay를 실제 만기의 근거로 사용한다.
- H7의 참가자 집중도는 증권사별 청산보유 집중도이며 최종투자자의 보유 집중도와 다르다. NK225MWE가 참가자 OI에 포함되는지 확인 전 미니 집중도 연구 가능이라고 표시하지 않는다.

### Gaps
- 전체 live 계약 체인/기초자산별 정확한 현재 종목 수는 인증 자료를 받지 않아 추출하지 못했다. 마스터 목록에 없는 미상장 코드를 규칙으로 만들어 배포하지 않는다.
- /open_interest_by_issue의 query 예시는 EQOP를 들지만 상품표는 주식별 XXXX+E를 쓰므로 실제 EQOP 그룹 필터 지원 여부를 공급자에 확인해야 한다.

## 4. 장중 파일 대안, 자료 품질, 지금 문의할 항목

### Takeaway
개인 연구자가 일본 데이터를 조달하려면 Pro 견적과 함께 DataCube의 개인/학술용 월별 파일을 비교할 가치가 있다. 공개 스키마만으로 데이터 구조는 확인되지만 구독·구매 없이 완전한 분석 표본은 확보되지 않았다.

### Cited Findings
- JPX는 선물·옵션 틱/1분/일별 가격을 유료 CSV로 DataCube에서 제공한다. 상품 페이지 Sample Data 버튼으로 샘플을 안내하며, 이 조사에서 상품 페이지는 JavaScript 검증 화면으로 보여 샘플파일을 내려받지 못했다. [공식 조달 안내](https://www.jpx.co.jp/english/markets/paid-info-derivatives/historical/01.html)
- 옵션 1분 제공 시작: Nikkei225 standard 2006-09-01, mini 2023-05-29, TOPIX 2014-03-24, JPX-Nikkei400 2016-07-19, Securities Options 2014-03-24. mini 상장 전 자료가 있었다는 뜻이 아니다. [1분 옵션 상품표](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/ohlc_minute/options/deribatibu-opushon-risuto)
- 선물 1분은 Nikkei225 large/mini 2006-09-01~, micro 2023-05-29~, TOPIX/miniTOPIX 2014-03-24~이다. [선물 1분 상품표](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/ohlc_minute/futures/deribatibu-risuto)
- 옵션 1분 CSV에는 trade_date,execution_date,security_code,session_id,interval_time,OHLC,trade_volume,VWAP,number_of_trade,record_no,contract_month,exercise_price 등이 있다. 실행 달력일은 2022-09부터, 헤더 소문자화는 2022-07부터. Session_ID는 주간999/야간003이며 API의00/04와 다르다. [1분 스키마](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/ohlc_minute/options), [Pro 거래량 코드](https://jpx.gitbook.io/j-quants-pro/api-reference/volume_by_participant/codelist)
- 옵션 틱은 체결가격·수량(계약수)·시각·순번을 포함하는 가격 틱 자료다. 시각은 2016-07-19부터 밀리초지만 2021-09-21~2022-02-10의 밀리초부분은 잘못된 시스템값이므로 초까지만 쓰라고 명시한다. 제공 스키마에 주문별 bid/ask·잔량 필드는 없다. [틱 스키마](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/tick/options)
- 공개 가격표는 개인/학술용 옵션 1분 자료 1개월 JPY220, 옵션 틱1개월 JPY330을 표시하며 기업/외부배포 요율은 별도다. 결제단위·상품선택 범위·본인 자격·공개 파생그래프 허용은 견적에서 확인할 것. [현재 가격표](https://jpx.gitbook.io/jquants-dc/en/dataspec/period_pricing)

### Inferences
우선 문의 순서:
1. Nikkei225 mini의 수·금 만기 전 콜풋/전 행사가 일별 OHLC·OI·IV와 1분 가격, 같은 날짜 Nikkei225 선물1분을 요청한다. 신호시점 이후 미래5거래일 RV를 만들 수 있는지 확인한다.
2. H1 도입효과는 2023 mini 전환과 2025 수요일 추가를 별개 사건으로 정의하고 상품승수·상장구조 변경을 통제한다. standard 옵션과 weekly의 구분 및 원래 2015 weekly 이력 조달은 추가 문의한다.
3. 개별증권은 EQOP 가격+현물주식1분+분할/배당/효력일 자료를 확보하되 월물 비교집단으로 관리한다. single-stock weekly 도입효과 표본으로 일본 일반 월물을 사용하지 않는다.
4. H9b 호가연구는 위 체결틱만으로 진행하지 않고 J-GATE/벤더의 실제 호가이력 상품을 따로 견적받는다.
5. raw timestamp, trading_date, session, published_at, available_at를 분리하고 공급자 원문값·단위를 보존한다.

### Gaps
- DataCube 1분 Trade_Volume 설명은 JPY/point로 적혀 있어 틱 스키마의 계약수와 불일치한다. 명백히 단위확인이 필요한 문서 문제로 표시한다. 거래량을 JPY로 자동해석하지 않는다.
- 1분 interval_time의 시작/종료 경계와 비거래 분 생성정책은 개별 파일 샘플로 재확인 필요. Pro 현물1분의 시작시각 정의를 DataCube 파생1분에 그대로 적용하지 않는다.
- Nikkei 현물지수 틱 라이선스 및 해당 지수의 DataCube 포함 범위, 다단계 호가 역사자료, private RFQ, 투자자 최종수익자 포지션은 이번 Pro 명세 조사만으로 확보되지 않았다.
- 공개 그래프와 원시데이터 재배포 권한은 서로 다르다. 개인/학술 파일 구매가 공개 CSV 배포 허용이라는 뜻은 아니다.
