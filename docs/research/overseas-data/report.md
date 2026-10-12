# 해외 위클리옵션 데이터와 API 구조

> **2026-10-12 후속 실호출 업데이트:** TAIFEX API와 공식 역사 CSV 수집에 성공했습니다. [20거래일 가격·OI 분석 및 개별 계약 티커](../../taifex-analysis.md)를 확인하세요. 아래 API 실패·미검증 기록은 최초 조사 시점의 이력으로 보존합니다.

[자료 폴더 안내](README.md) · [메인 README 요약](../../../README.md#overseas-data)

확인 기준: **2026년 10월 12일, Asia/Seoul**. 공개 공식 명세·상품 규격·상장 대상 명부를 조사했다. 유료 데이터 구매나 계정 인증은 수행하지 않았으며, 이번 결과는 데이터 조달·연결 설계다.

**일본은 일별 옵션 API와 별도 장중 파일, 홍콩은 라이선스 기반 파일·시장데이터 피드, 대만은 공개 포털과 역사 다운로드를 구분해서 접근해야 한다.** 일본 J-Quants Pro의 1분 API는 현물주식용이므로 옵션 분봉을 받을 수 있다고 전제하면 안 된다. 홍콩과 대만에서는 개별주식 위클리 대상 명부를 각각 **54개·7개 기초종목**으로 확인했지만, 이는 만기·행사가·콜풋별 실제 상장 계약 수가 아니다. 일본의 표준 개별증권 옵션은 월물이고, 단기 맞춤형 Flexible 계약은 표준 위클리와 구분한다. 국내 기준모형의 해외 전이는 먼저 지수끼리 비교하고 개별주식은 별도 표본으로 확장하는 것이 적합하다. **이번 조사에서 실제 옵션 가격·OI 패널을 확보하거나 전이 성능을 추정하지는 않았다.** 특히 대만은 OpenAPI 명세·JSON 취득에 실패해 인증·쿼리·필드를 검증 완료로 표시할 수 없다. ([JPX 1분 명세](https://jpx.gitbook.io/j-quants-pro/api-reference/equities_bars_minute), [JPX 개별증권 규격](https://www.jpx.co.jp/english/derivatives/products/individual/securities-options/01.html), [HKEX 위클리 명부](https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options/Weekly-Stock-Options?sc_lang=en), [TAIFEX 대상 명부](https://www.taifex.com.tw/cht/2/stockLists))

| 조달 경로 | 자료의 핵심 | 위클리·개별종목 범위 | 이번 증거 수준과 남은 관문 |
|---|---|---|---|
| **JPX J-Quants Pro** | 일별·세션별 옵션 가격, 계약별 OI, 참가자 통계; 계정 토큰 REST·SFTP | Nikkei225 mini `NK225MWE`; 개별증권 `EQOP`는 일반 월물 | 공개 API 명세 확인. 구독 권한·실제 응답은 미검증 |
| **JPX DataCube** | 유료 옵션·선물 1분봉과 체결 틱 CSV | mini 1분은 2023-05-29부터; 개별증권 옵션 파일도 별도 제공 | 파일 스키마 확인. 실제 샘플·거래량 단위·분 경계 추가 확인 |
| **HKEX Marketplace** | SOM/Non-SOM Full Book, 최우선 호가, 일별 통계; 다운로드·SFTP·S3 | 주식 위클리 54개 클래스; HSI·HHI·HTI 지수 위클리 별도 | 명부 CSV·JSON 저장. 유료 가격·호가·최신 계약체인 미확보 |
| **TAIFEX** | OpenAPI 조사 대상 + 옵션 역사 다운로드 | 주식옵션 대상 32개 중 위클리 7개; 지수옵션은 별도 확인 | 공식 상품·대상 명부 확인. Swagger 원문·데이터 GET 검증 미완료 |

위 표는 공개 명세에 따른 조달 구분이다. 각 서비스의 세부 근거와 미확인 항목은 아래에 분리했다. **“명세 확인”, “명부 저장”, “실제 시세 수집”은 서로 다른 완료 상태**로 관리한다.

<a id="japan"></a>
## 1. 일본은 Pro 일별 패널과 DataCube 장중 자료를 결합한다

### Nikkei225 mini 위클리와 개별증권 월물을 구분한다

Nikkei225 mini 옵션은 2023-05-29 상장됐고 2025-05-26 수요일 만기가 추가됐다. 현재 수요일과 금요일 만기 구조이며, 둘째 금요일 정규월물은 다른 주간 만기와 구별해야 한다. 승수는 **옵션가격 × JPY 100**이고, 최종거래일은 SQ 전 영업일이므로 SQ 날짜와 최종거래일을 각각 저장한다. 월·화·목 만기는 **2027년 4월 예정**으로 발표됐으며 현재 계약 목록에 넣지 않는다. ([mini 규격](https://www.jpx.co.jp/derivatives/products/domestic/225mini-options/01.html), [만기 확대 예정 공지](https://www.jpx.co.jp/english/news/2040/20260326-01.html))

일반 Securities Options는 개별주식·ETF·REIT를 기초자산으로 하지만 표준 만기는 월물이다. J-NET Flexible는 맞춤형 만기를 설정하는 별도 거래방식이다. 따라서 **“일본 개별주식 위클리 대상 명부”를 일반 `EQOP` 목록으로 대신 만들지 않는다.** 일본 개별증권 자료는 월물 비교집단이나 상품 차이 연구에 사용할 수 있다. ([개별증권 규격](https://www.jpx.co.jp/english/derivatives/products/individual/securities-options/01.html), [기초자산 범위](https://www.jpx.co.jp/english/derivatives/products/individual/securities-options/index.html), [Flexible 규격](https://www.jpx.co.jp/english/derivatives/rules/flexible/index.html))

### Pro는 날짜별 계약 데이터를 모으는 REST 구조다

Base URL은 `https://api.jquants-pro.com/v2`다. `POST /token/auth_user`에 JSON `mailaddress`, `password`를 보내 `idToken`, `refreshToken`을 받고, 조회에는 `Authorization: Bearer <idToken>`을 사용한다. 문서상 ID token은 24시간, refresh token은 1주 유효하다. `POST /token/auth_refresh`의 `refreshtoken`으로 갱신하며 문서는 이를 request body 항목으로 설명한다. **개인용 J-Quants의 API Key 방식과 Pro 인증을 혼용하지 않는다.** 아래는 명세에 따른 구조이고 실제 로그인·조회 성공을 확인한 예시는 아니다. ([Pro 인증](https://jpx.gitbook.io/j-quants-pro/api-reference/refreshtoken), [갱신](https://jpx.gitbook.io/j-quants-pro/api-reference/idtoken), [개인용 서비스 변경 공지](https://www.jpx.co.jp/english/corporate/news/news-releases/6020/20260119.html))

| GET 경로 — base URL 뒤에 연결 | 주요 query·응답 | 연구 내용·시점·제약 |
|---|---|---|
| `/derivatives/options` | 필수 `date`; 선택 `category`, `code`, `contract_flag`, `pagination_key`; 배열 `options` | 일별·주야간 OHLC, 거래량, OI, 정산가격, IV와 계약정보. 매일 22:00 JST 제공. `code`는 `EQOP`의 **기초주식 코드**이며 옵션 계약코드가 아님. [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/options) |
| `/derivatives/futures` | 필수 `date`; 선택 `category`, `contract_flag`, `pagination_key`; 배열 `futures` | 일별·세션별 선물 가격·거래량·OI. 매일 22:00 JST. 옵션과 같은 날짜의 기초 선물 자료 후보. [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/futures) |
| `/derivatives/open_interest_by_issue` | 필수 `date`; 선택 `product_code`, `pagination_key`; 배열 `open_interest_by_issue` | `SeriesCode`, `ProductCode`, 전일·당일 OI, 청산·행사량 등. 2021-06-14부터; 19:00 JST 기준을 약 21:15 공개. [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue) |
| `/derivatives/open_interest_by_participant` | `category`, `date`, `pagination_key`; 배열 `open_interest_by_participant` | 참가자·계약·매수/매도·순위·보유량. 2016-12-02부터; 주말 기준을 다음 주 첫 영업일 15:30 공개. 미니 포함 여부 추가 확인. [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_participant) |
| `/derivatives/volume_by_participant` | 필수 `date`; 선택 `category`, `pagination_key`; 배열 `volume_by_participant` | 참가자·계약·주야간·Auction/J-NET별 거래량. 2014-03-24부터; 매일 17:30 JST. [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/volume_by_participant) |
| `/equities/bars/minute` | `code` 또는 `date` 필수; `from`, `to`, `pagination_key`; 배열 `data` | **현물주식용** `Date, Time, Code, O, H, L, C, Vo, Va`. 최근 36개월 이동창, 당일 16:30 JST. 선물·옵션·지수 제외. [명세](https://jpx.gitbook.io/j-quants-pro/api-reference/equities_bars_minute) |

역사 시작일과 갱신시간은 데이터셋별로 다르며, 상품 상장일보다 앞선 시계열을 뜻하지 않는다. 옵션 가격의 주요 category는 `NK225E`(표준 Nikkei225, 2008-05-07~), `NK225MWE`(mini, 2023-05-29~), `TOPIXE`(2008-05-07~), `JGBLFE`(2008-05-07~), `EQOP`(2014-11-17~)다. 별도 OI 및 참가자 통계의 역사 범위는 가격 범위와 다르다. ([상품 코드표](https://jpx.gitbook.io/j-quants-pro-ja/api-reference/options/codelist), [역사 범위](https://jpx.gitbook.io/j-quants-pro/data-spec), [갱신시간](https://jpx.gitbook.io/j-quants-pro/data-update))

옵션 OHLC에는 `from/to`가 없으므로 날짜별로 수집한 뒤 연결한다. 예를 들어 `GET /derivatives/options?date=2026-10-09&category=NK225MWE`는 문서 기반 요청 예시다. 응답에 `pagination_key`가 있으면 동일 조건으로 이어 받는다. `contract_flag=1`은 중심월물만 선택하므로 **전 만기·전 행사가 체인 연구에서는 고정하지 않는다.** 정산·응급증거금 레코드가 같은 날 함께 존재할 수 있어 `TradeDate + Code + EmergencyMarginTriggerDivision`을 구분해야 한다. ([옵션 조회·필드](https://jpx.gitbook.io/j-quants-pro/api-reference/options), [공통 주의](https://jpx.gitbook.io/j-quants-pro/api-reference/attention))

OI 파일에서는 `DataType=IssueData`를 계약행으로 사용하고 월물·콜풋·상품 합계행을 다시 더하지 않는다. 미니의 `ContractMonth`를 일반 달력 월로 해석하지 말고 `LastTradingDay`, `SpecialQuotationDay`와 원본 코드를 보존한다. 참가자 OI는 청산보유 참가자, 거래량은 실행 참가자 기준이므로 두 자료가 같은 최종 투자자의 포지션 이동을 보여준다고 단정할 수 없다. ([OI 자료형](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue/codelist), [옵션 필드](https://jpx.gitbook.io/j-quants-pro/api-reference/options), [참가자 OI](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_participant), [참가자 거래량](https://jpx.gitbook.io/j-quants-pro/api-reference/volume_by_participant))

대량 초기 적재에는 구독한 자료가 표시되는 `sftp-v2.jquants-pro.com:22`를 사용할 수 있다. Pro SFTP는 등록 계정·비밀번호 방식이며 HKEX의 SSH 공개키 방식과 다르다. 수치형 호출한도, 데이터셋별 사용권, 개인 연구자의 계약 가능 여부는 견적 단계에서 확인한다. ([SFTP](https://jpx.gitbook.io/j-quants-pro/sftp-specifications), [이용 절차](https://jpx.gitbook.io/j-quants-pro/getstarted))

### DataCube 옵션 1분봉은 별도 파일 상품이다

| DataCube 자료 | 공식 제공 범위 | 수집 시 확인할 점 |
|---|---|---|
| Nikkei225 mini 옵션 1분 | **2023-05-29~** | 수·금 만기, 모든 콜풋·행사가와 무거래 계약 처리 |
| 표준 Nikkei225 옵션 1분 | **2006-09-01~** | mini와 코드·승수·만기 체계를 분리 |
| Securities Options 1분 | **2014-03-24~** | Pro `EQOP` 일별 시작일과 다름; 월물·조정계약 식별 |
| 옵션 체결 틱 | 체결시각·가격·수량·순번 | 주문장·bid/ask 잔량이 포함된 Full Book으로 취급하지 않음 |

위 범위는 [DataCube 옵션 1분 상품표](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/ohlc_minute/options/deribatibu-opushon-risuto)와 [틱 명세](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/tick/options)에 따른다. 1분 CSV는 `trade_date`, `execution_date`, `security_code`, `session_id`, `interval_time`, OHLC, `trade_volume`, VWAP, `number_of_trade`, `record_no`, `contract_month`, `exercise_price` 등을 제공한다. 주간 `999`·야간 `003` 세션 코드를 다른 Pro 자료의 코드와 별도 매핑해야 한다. **분 시작/종료 경계, 무거래 분 생성정책과 거래량 단위는 샘플로 재확인**한다. 틱의 일부 과거 기간에는 밀리초 값에 공식 주의사항이 있으므로 타임스탬프 정밀도도 기간별 관리가 필요하다. ([1분 스키마](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/ohlc_minute/options), [틱 주의사항](https://jpx.gitbook.io/jquants-dc/en/dataspec/fin_derivatives/tick/options))

일본의 첫 조달 묶음은 **mini 일별 OHLC·OI·IV + 같은 계약 옵션 1분 + 같은 날짜 기초 선물 또는 현물지수 장중 가격**으로 제안한다. 옵션 분봉만으로 기초자산 RV가 생기지는 않는다. REV에는 종가 전 30분·다음 개장·개장 후 1분/30분 가격이 필요하고, H9b 스프레드·잔량 연구에는 별도 호가 이력이 필요하다. 명세를 기계가 읽는 형태로 정리한 [일본 API 맵 JSON](data/japan_api_map.json)도 함께 저장했다.

<a id="hongkong"></a>
## 2. 홍콩은 54개 주식 클래스와 지수 위클리를 서로 다른 상품군에서 받는다

### 54개 대상 명부를 실제 계약 마스터와 연결해야 한다

공식 위클리 주식옵션 페이지의 **2026-09-01 갱신 명부는 54개 클래스**다. 주식코드·HKATS 클래스·기업명을 CSV와 JSON으로 저장했고 각 필드의 고유 값도 54개로 확인했다. 2026년 7월의 52개 발표와 최신 54개는 기준 시점이 다르다. **54개는 기초주식 대상 수이며, 현재 활성 계약이나 거래가 발생한 계약 수가 아니다.** 각 클래스 아래의 실제 만기×행사가×콜풋과 조정계약을 추가로 받아야 한다. ([현재 명부](https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options/Weekly-Stock-Options?sc_lang=en), [7월 발표](https://www.hkex.com.hk/News/News-Release/2026/260713news?sc_lang=en))

전체 목록은 [홍콩 주식 위클리 54개 CSV](data/hkex_weekly_stock_option_classes_20261012.csv)와 [동일 명부 JSON](data/hkex_weekly_stock_option_classes_20261012.json)에서 확인할 수 있다. `stock_code`, `hkats_code`, `underlying_name`, `weekly_launch_date`, 출시 근거 URL, 명부 갱신일, 수집일과 상태를 담았다. **현재 54개를 과거 모든 날짜에 소급 적용하지 않고 개별 출시일부터 편입하는 유니버스**를 구성한다. 기존 종목의 위클리 도입과 기업의 신규 주식 상장이 동시에 일어난 경우도 구분해야 한다.

홍콩 주식옵션은 **미국형·실물인수도**, 프리미엄은 주당 HKD다. 위클리는 당주·차주 만기이며 월물과 같은 만기에 중복 상장하지 않는다. 지수 위클리는 **HSI, HHI(HSCEI), HTI(HSTECH)**로 별도 관리하고 승수는 HKD 50/포인트다. 표준·미니·월물·위클리를 상품명 유사성만으로 같은 계약으로 합치지 않는다. ([주식옵션 규격](https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options?sc_lang=en), [HSI 위클리](https://www.hkex.com.hk/Products/Listed-Derivatives/Equity-Index/Hang-Seng-Index-%28HSI%29/Weekly-Hang-Seng-Index-Options?sc_lang=en), [HHI 위클리](https://www.hkex.com.hk/Products/Listed-Derivatives/Equity-Index/Hang-Seng-China-Enterprises-Index/Weekly-Hang-Seng-China-Enterprises-Index-Options?sc_lang=en), [HTI 위클리](https://www.hkex.com.hk/Products/Listed-Derivatives/Equity-Index/Hang-Seng-TECH-Index-Futures-and-Options/Weekly-Hang-Seng-TECH-Index-Options?sc_lang=en))

### Full Book, 일별 OI, 현물 가격은 별도 조달 항목이다

| 자료·식별자 | 실제 용도 | 범위와 주의점 |
|---|---|---|
| `CFBD-SOM` Historical Full Book CSV | **주식옵션** 주문 추가·수정·취소, 체결·취소 및 참조정보 | 기존 상품 역사 시작은 2014-12-01이나 각 위클리 클래스는 출시 이후만 존재. 최신 CSV 샘플 미확보. [상품](https://data.hkex.com.hk/catalog/dataset/44c1441a763911ef953342323a43f021) |
| `CFBD-NSOM` Historical Full Book CSV | 주식옵션 이외 선물·옵션; **지수 위클리** | 카탈로그는 2014-12-01부터 안내. 일별 전달과 장중 이벤트 간격을 구분. [상품](https://data.hkex.com.hk/catalog/dataset/c712edce763911ef953342323a43f021) |
| `BASFOD` Best Bid/Ask | 표준 주식선물·옵션 최우선 매수·매도 가격/잔량 | Full Book이 아님. 표시 범위 2025-10-01 이후; 더 오래된 이력·조정계약 문의. [상품](https://data.hkex.com.hk/catalog/dataset/a1c614abe56f4ea4a2c3b8765029a0a4) |
| End of Day Summary / Daily Market Report / DTOP | 일별 거래 통계·OI 자료 조달 후보 | 필요한 **계약 단위 OI·공표시각·정정** 범위를 샘플로 대조. [일별보고서](https://www.hkex.com.hk/Market-Data/Statistics/Derivatives-Market/Daily-Market-Report-(Latest)?sc_lang=en) |
| `RP006` Series Prices | 시리즈별 정산가격·전일정산가·IV | 공개 record01 명세에 OI 없음. IV·정산자료가 체결 분봉을 대체하지 않음. [필드 명세](https://www.hkex.com.hk/eng/market/rm/rm_dcrm/riskdata/srprices/seriespricesFormat.htm) |
| Weekly Series / RPF / `TP011` | 실제 비월물 시리즈와 위험 파라미터·기업행사 조정 연결 | 위클리 주식옵션 참조정보는 첫 거래일부터 제공. 최신 실제 시리즈 행은 이번에 미확보. [기술안내](https://www.hkex.com.hk/-/media/HKEX_Common/Market/Products/Listed-Derivatives/Single-Stock/Weekly-Stock-Options/Overview-of-Technical-Documentation-for-WSO.pdf) |

Marketplace는 계정과 라이선스를 기반으로 **직접 다운로드·SFTP·S3 cloud-to-cloud**를 제공한다. 공개 고객용 REST base URL·토큰·페이지네이션은 이번 조사에서 확인하지 못했으므로 NH REST와 같은 방식으로 설계하지 않는다. SFTP는 `sftp.data.hkex.com.hk:22`, 사용자명은 Marketplace 이메일이며 OpenSSH 공개키를 등록해 개인키로 인증한다. 예시 경로는 `/CFBD-SOM/HKEX-DAILY-DERIVATIVES-SOM/HKEX/YYYY/MM/DD`, `/CFBD-NSOM/HKEX-DAILY-DERIVATIVES-NON-SOM/HKEX/YYYY/MM/DD`다. 가이드의 통상 **14일 다운로드 보관창은 전체 역사자료가 14일뿐이라는 뜻이 아니다.** ([Marketplace 안내](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/HKEX-Data-Marketplace?sc_lang=en), [SFTP 가이드](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/-/media/1BC625C24564466B83E98212152F8EF7.ashx))

실시간 **OMD-D는 별도 바이너리 피드**다. Standard/Premium은 가격별 집계, FullTick은 주문별 데이터 중심이며, FullTick 단독 구독에 통계·OI·IV가 모두 포함된다고 가정할 수 없다. 현물 주식 가격도 SOM 옵션 파일과 별도다. 따라서 Full Book만 구매하면 H5/H6·REV에 필요한 기초가격과 일별 OI까지 완성된다는 견적은 피해야 한다. ([OMD-D 상품 구분](https://www.hkex.com.hk/OMDD?sc_lang=en), [시장데이터 FAQ](https://www.hkex.com.hk/Global/Exchange/FAQ/Market-Data?sc_lang=en))

### 개별 계약은 OMD 참조 계층·유효일·조정정보로 식별한다

OMD-D v1.49의 참조 연결은 `301 Commodity → 302 Class → 303 Series Base / 304 Series Extended`다. 핵심은 `OrderbookID`, `Symbol`, `ExpirationDate`, `StrikePrice`와 소수점, `PutOrCall`, `Market`, `Modifier`, `CommodityCode`, `ContractSize`와 소수점, 첫·마지막 거래시각이다. 주식 위클리의 Market은 **18과 145**를 확인해야 하며 18만 필터링하면 누락이 생긴다. 지수 위클리는 HSI 39, HHI 87, HTI 84로 구분한다. OI 메시지 366의 `DayIndicator`, `Settlement`, `GrossOI`, `NetOI`, `Turnover`와 정정도 보존한다. **이 필드들은 실시간 명세의 필드이며 구매 CSV의 동일 열을 실물 확인한 것은 아니다.** ([OMD-D 바이너리 명세 v1.49](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Market-Data-Services/Infrastructure/HKEX-Orion-Market-Data-Platform-Derivatives-Market-OMD-D/HKEX_OMD_Derivatives_Binary_Interface_Specifications_v1-49.pdf))

기업행사 전후 계약 연결에는 `TP011` 등 조정 자료가 필요하다. 같은 회사명·행사가처럼 보여도 승수·조정자가 달라지면 다른 경제적 계약일 수 있다. 명세에는 현행 v1.49와 ODP 이행 후용 v2.3가 함께 게시돼 있으므로 버전 숫자만으로 운영 사양을 선택하지 않는다. 저장한 [HKEX 데이터셋 목록 CSV](data/hkex_dataset_inventory.csv)는 조달 항목 비교용이며 유료 원시자료를 포함하지 않는다. ([위클리 기술안내](https://www.hkex.com.hk/-/media/HKEX_Common/Market/Products/Listed-Derivatives/Single-Stock/Weekly-Stock-Options/Overview-of-Technical-Documentation-for-WSO.pdf), [운영·이행 명세 구분](https://www.hkex.com.hk/OMDD?sc_lang=en))

<a id="taiwan"></a>
## 3. 대만은 개별주식 위클리 7개를 확인했지만 API 실행 검증은 남았다

### 대상 명부는 주식옵션 여부와 위클리 여부를 따로 표시한다

TAIFEX 공식 명부의 2026-09-03 효력 기준으로 **주식옵션 대상 32개 중 위클리 대상은 7개**다. 판단 기준은 `是否為股票選擇權週契約標的` 열이다. 이 명부의 위클리 ETF 대상은 0개이며, ETF 계약규격이 존재하는 것과 실제 위클리 ETF 상장은 구분한다. 아래 두 글자 코드는 **대상 명부의 원본 코드**다. ([TAIFEX 대상 명부](https://www.taifex.com.tw/cht/2/stockLists))

| 명부 코드 | 기초주식 코드 | 공식 상품명 | 식별용 영문명 |
|---|---|---|---|
| `CA` | `1303` | 南亞 | Nan Ya Plastics |
| `CC` | `2303` | 聯電 | United Microelectronics / UMC |
| `CD` | `2330` | 台積電 | Taiwan Semiconductor Manufacturing / TSMC |
| `CZ` | `2603` | 長榮 | Evergreen Marine |
| `DH` | `2317` | 鴻海 | Hon Hai Precision |
| `DV` | `2454` | 聯發科 | MediaTek |
| `DX` | `3231` | 緯創 | Wistron |

전체 7개 목록과 출처·효력일은 [대만 주식 위클리 대상 CSV](data/taifex_weekly_stock_option_underlyings_20261012.csv)에 담았다. `CA`를 `CAO` 등 실제 옵션 자료 코드로 연결하는 규칙, 실제 주차 문자열, 행사가별 활성 시리즈 수는 이번 JSON 응답으로 검증하지 못했다. **접두사에 문자를 붙여 만든 코드를 실제 조회 성공 종목으로 배포하지 않는다.**

주식옵션은 원칙적으로 **2,000주 단위·유럽형·현금결제**이며 기업행사 조정 예외가 있다. 주간계약은 수요일 상장 후 두 번째 다음 수요일 만기 구조이고 월물과 같은 최종거래일이면 중복 주간계약을 상장하지 않는다. 일반 거래시간은 현지 08:45–13:45, 만기계약 최종거래일은 13:30까지다. 명부에 보이는 17:25–익일 05:00 열은 **주식선물의 야간시간**이므로 주식옵션 시간으로 적용하면 안 된다. ([주식옵션 규격](https://www.taifex.com.tw/cht/2/sSO), [명부 열 정의](https://www.taifex.com.tw/cht/2/stockLists))

### OpenAPI 이름과 실제 검증된 엔드포인트를 구분한다

[TAIFEX OpenAPI](https://openapi.taifex.com.tw/)가 Swagger UI 진입점인 것은 확인했다. 그러나 이번에는 `swagger.json` 취득이 실패했고 데이터 JSON도 확보하지 못했다. 따라서 **base server 경로, HTTP 메서드·인증 필요 여부, query parameters, 응답 필드, 반환 기준일·행수, 호출한도를 검증 완료로 기재하지 않는다.** 아래는 사용자가 제시한 이름과 후속 조사 후보를 연구 목적에 매핑한 표이며, 호출 성공 목록이 아니다. 실패·미완료 상태는 [API 확인 기록 JSON](data/taifex_api_probe_status.json)에 남겼다.

| API 조사 대상 이름 | 연구에서 필요한 내용 | 다시 확인할 정확한 항목 |
|---|---|---|
| `DailyMarketReportOpt` | 계약별 일별 가격·거래량·OI 패널 후보 | 실제 path, 만기/주차·행사가·콜풋·세션 필드, 날짜 필터, 과거 범위 |
| `DailyOptionsDelta` | 델타 참조값 | 계약 연결키, 계산모형·기초가격·평가시점·단위 |
| `PutCallRatio` | 풋콜 집계 지표 | 거래량 PCR와 OI PCR 구분, 포함 상품·만기, 공표시각 |
| `OpenInterestOfLargeTradersOptions` | 대규모 거래자 포지션 집계 | 집계 대상·순위·매수/매도·분모·시점; 개별 투자자 정답과 구분 |
| `OptionsTimeAndSalesData` | 옵션 체결 틱 후보 | 거래일·달력일·세션, 시각 정밀도, 거래취소, 조회기간·전달방식 |
| `SSOLists` | 기초주식↔옵션 상품 마스터 후보 | 위클리 대상 표시, 원본 코드와 거래자료 코드 연결, 이력 보존 |
| `ContractAdj` | 기업행사 계약조정 후보 | 조정 전후 코드·승수·행사가, 효력일·공지일 |
| 최종결제 관련 자료 | 실제 만기·결제값 연결 | endpoint 명칭·스키마 및 주식옵션 포함 범위 |

**장기 이력은 별도 확인 대상**이다. [공식 옵션 역사 다운로드 페이지](https://www.taifex.com.tw/enl/eng3/optDailyMarketView?menuid1=03)와 [주식옵션 최종결제가 페이지](https://www.taifex.com.tw/cht/5/sSOFSP)의 존재는 확인했지만 이번 실행에서 다운로드 제한·연간 파일·최초 제공일·유료 장기상품 조건을 검증하지 못했다. 따라서 OpenAPI가 최신 스냅샷만 주는지 기간 조회까지 지원하는지 확정하기 전 `?date=`, `?startDate=` 같은 파라미터를 임의로 사용하지 않는다.

지수옵션 **TXO의 현재 위클리 만기·코드 체계도 추가 검증 항목**으로 남는다. 개별주식 수요일 규칙을 지수 위클리 전체에 일반화하지 않는다. TAIFEX 옵션 자료와 연결할 현물 주식·지수 장중 가격 및 기업행사는 TWSE/TPEx 등 별도 공급 경로·이용권 확인이 필요하다. 이번 7개 명부만으로 일별 옵션 시세, 장중 RV 또는 REV를 계산할 수는 없다.

<a id="model-transfer"></a>
## 4. 국내 기준모형은 계약·시간·목표를 맞춘 뒤 해외 정보를 더한다

다음은 **공급자 필드가 아닌 내부 설계 제안**이다. 지수 위클리와 개별주식 위클리를 별도 패널로 유지하고, 기초종목 마스터와 실제 계약 마스터를 분리한다. 현재 명부가 과거 상장 상태를 대신하지 않도록 유효기간을 저장한다. 원본 코드는 문자열로 유지해 선행 0과 특수 만기코드를 보존한다.

| 내부 데이터 층 | 필수 정보 | 이 정보가 없으면 생기는 문제 |
|---|---|---|
| `underlying_master_history` | 거래소, 기초코드·이름, 자산유형, 위클리 편입일, `valid_from/to`, 출처 | 현재 명부를 과거에 적용하는 생존자 편향 |
| `contract_master_history` | 원본 계약 ID, 상품군, 실제 최종거래·결제시각, 콜풋, 행사가·단위, 승수, 통화, 행사·결제 방식, 조정자 | 같은 기초주식의 여러 계약·월물·위클리·조정계약 혼합 |
| `daily_option_panel` | 종가와 정산가 분리, 거래량·OI, IV·Greeks의 모형·단위, 정정 버전 | 체결 없는 가격·사후 정산가·미래 공개 OI를 실시간 입력으로 오인 |
| `underlying_intraday` / `option_events` | 거래소 시각·수신시각, 거래일·세션, 가격·수량·sequence, 거래/호가 종류, 커버리지 | 야간 귀속 오류, 옵션 분봉을 현물 RV로 오인, 무거래와 수집 결측 혼동 |
| `reference_events` | 기업행사·배당·금리·휴장·규격 변경의 공지시각과 효력시각 | 사후 확정 정보를 과거 학습 입력에 사용 |

공통 시각은 `observed_at`, `published_at`, `received_at`, `available_at`을 구분하며 예측 시각 이전에 이용 가능했던 값만 쓴다. 예를 들어 일본 OI 19:00 기준값이 21:15에 공개된다면 해당 날짜 국내 장 마감 예측에 넣을 수 없다. 외국의 현지 날짜가 같아도 미완결 세션·미공표 자료일 수 있다. 시세의 UTC 시각과 현지 거래일·세션은 함께 보존한다. ([JPX OI 공표 기준](https://jpx.gitbook.io/j-quants-pro/api-reference/open_interest_by_issue))

머니니스는 적절한 선도가 확보되면 `log(K/F)`, 잔존기간은 실제 만기까지 시간으로 정의한다. 계약 수 단위 OI는 승수·기초자산 규모를 확인하고 같은 범위에서 비교한다. OI 증가와 변화의 절댓값은 다른 피처이며, 신규상장·만기소멸·기업행사 조정과 기존 계약 변화를 분해한다. IV의 퍼센트/소수·연율·행사모형을 맞추지 않은 채 국가별 값을 평균하지 않는다. 특히 홍콩 미국형 주식옵션을 일본·대만 유럽형 자료와 같은 가격모형으로 처리하지 않는다.

| 기획서 연구 | 최소 조달 묶음 | 실행·해석의 경계 |
|---|---|---|
| **H2 해외 전이** | 국내외 동기간 기초 RV, 동일 정의 옵션 피처, 상품·가용시각 사전 | 국내 단독과 같은 국내 평가 날짜·목표·튜닝 예산으로 비교 |
| **H5 만기 / H6 OI** | 실제 계약·만기 이력, 일별 OI와 공표시각, 기초 장중 가격 | 요일·만기 중복을 점검; OI 원인이 아닌 추가 예측력부터 검증 |
| **가격회귀율 REV** | 만기일 종가 전 30분·종가·다음 개장·개장 후 1분/30분의 기초가격 | 일별 OHLC만으로 개장 후 1분·30분 회귀를 계산하지 않음 |
| **H9b 유동성 스트레스** | 동기화된 bid/ask·잔량·체결, 관측 가능 상태, 비용 | 체결 틱이나 1분봉만으로 스프레드·주문장을 복원하지 않음 |
| **H1·H7·H8 메커니즘** | 도입·편입 코호트와 대조군, 실제 보유·포지션·리밸런싱 사건 | 참가자 통계·대규모 보유 집계를 최종 투자자/딜러 순포지션으로 확정하지 않음 |

전이 실험은 **국내 RV 기준 → 국내 옵션 추가 → 이용 가능한 해외 요약값 추가 → 해외 사전학습 후 국내 보정**으로 나눌 것을 제안한다. 해외 요약값이 도움이 되는 결과는 정보유입의 증거이고, 해외에서 학습한 관계가 국내로 이전됐다는 증거와는 다르다. 미래 5거래일 RV를 목표로 한다면 평균과 누적 중 하나를 사전에 정하고 모든 시장에 같은 정의를 적용한다. 같은 날짜의 계약은 같은 검증 fold에 두며, 미래 라벨이 검증기간과 겹치는 훈련 관측을 제거한다. 계약 수가 많아도 독립 날짜·만기 사건 수가 증가하는 것은 아니다.

<a id="acquisition"></a>
## 5. 구매 전에 같은 날짜의 작은 연결 표본부터 요청한다

**첫 확보물은 모델 성능표보다 계약·가격·OI가 같은 키와 시각으로 연결되는 표본**이어야 한다. 정상일·만기일·휴일 전후와 기업행사 조정이 있는 날을 포함한 작은 표본을 받아 계약 매칭, 시각, 단위, 무거래·결측 처리를 검증한 뒤 필요한 역사 기간을 정한다. 아래 우선순위는 조달 제안이며 실제 구매·계약은 진행하지 않았다.

| 우선순위 | 요청 대상 | 공급처에 전달할 구체적인 확인 문장 |
|---|---|---|
| **1 — 일본 지수 전이** | Pro + DataCube | “`NK225MWE` 수·금 만기의 전 행사가·콜풋 OHLC/OI/IV와 1분 파일, 같은 날짜 기초 선물 가격을 연결한 샘플이 필요합니다. 주간 OI 참가자 자료에 mini가 포함됩니까? IV 평가시각·단위, 1분 구간 경계·거래량 단위·무거래 행 정책을 알려주세요.” |
| **1 — 대만 구조 검증** | TAIFEX OpenAPI 지원·역사자료 담당 | “Swagger의 서버·보안·parameter 원문과 해당 옵션 API의 작은 JSON 예시가 필요합니다. 날짜 조회와 과거 범위가 있습니까? 주식 위클리 7개 및 TXO의 실제 상품코드·주차·계약조정 연결키와 만기 후 조회 범위를 알려주세요.” |
| **2 — 홍콩 일별+현물** | HKEX Marketplace | “주식 위클리와 HSI/HHI/HTI 지수 위클리의 계약별 일별 OI·정산가·IV·참조정보, 같은 기초자산 장중 가격을 요청합니다. Full Book과 별도 구독해야 하는 통계 자료, 공표·정정시각, 역사 명부/조정계약 포함 범위를 확인해주세요.” |
| **3 — 호가 가설** | HKEX 또는 각 거래소·벤더 | “최우선 bid/ask·잔량 또는 Full Book의 이벤트 이력, 체결취소, 초기 스냅샷·sequence·재구성 규칙이 필요합니다. SOM/Non-SOM 구독과 CSV 기술명세를 각각 제시해주세요.” |
| **모든 단계 — 사용권** | 각 공급처 | “개인/학술 연구, 연구실 공동사용, 공개 Streamlit 파생 그래프, 집계표와 원시 CSV 배포는 각각 허용됩니까? 필요한 계약과 비용·보관기간을 구분해주세요.” |

국내 기준모형의 첫 해외 비교는 **일본 지수 mini처럼 계약·일별 자료·장중 조달 경로가 명확한 표본**에서 시작하고, 대만은 명세 검증을 마친 뒤 비용·역사 범위를 비교하는 순서가 합리적이다. 홍콩 개별주식 위클리는 도입 코호트와 실제 계약체인을 연결하면 종목별 연구의 중요한 후보지만, 최근 편입 종목의 짧은 이력과 미국형·실물결제 차이를 별도 통제해야 한다. 이 순서는 시장의 우열이 아니라 **현재 확인한 자료 구조와 미해결 연결 비용에 따른 연구 우선순위**다.

완료 산출물은 국가별 명세 조사와 홍콩·대만 대상 명부다. 다음 실증 단계의 착수 조건은 **권한이 확인된 실제 표본에서 계약 키·공표시각·기초가격·OI를 대사하는 것**이다. 그 조건을 통과한 데이터만 국내 기준모형에 추가하면, 해외 정보가 효과가 없다는 결과도 자료 결함과 구별해 해석할 수 있다.
