# 홍콩 HKEX: 해외 위클리옵션 데이터셋·접근 구조

조사 기준: 2026-10-12 KST. 공식 자료만 확인. 계정 생성·구매·인증키 사용·레포지토리 변경은 수행하지 않았다. 자료 증거 단계는 공개 문서 열람과 명부 전사이며, 유료 거래·호가 원시 파일 또는 최신 계약체인 실데이터를 내려받아 분석한 상태가 아니다.

## 1. 어떤 위클리 상품과 개별 상장 주식옵션을 포함하는가?

### Takeaway
공식 위클리 주식옵션 명부는 2026-09-01 업데이트 기준 54개 기초주식 클래스이며, 각 클래스 아래 만기×콜풋×행사가별 계약을 별도로 구성해야 한다. 지수 위클리 HSI·HSCEI·HSTECH는 별도 시장 및 데이터 상품군이다.

### Cited Findings
- 공식 명부의54행을 CSV/JSON으로 전사했다. 중복검사 결과 주식코드54개, HKATS클래스코드54개, 기업명54개로 모두 고유했다. ETF나 조정계약을 별도 기초주식으로 추가하지 않았다. 이는 명부 스냅샷이며 조사일 현재 모든 클래스의 개별 계약이 거래 가능한지 확인한 결과는 아니다. — [공식 명부](https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options/Weekly-Stock-Options?sc_lang=en)
- 파일: hkex_weekly_stock_option_classes_20261012.csv / .json. 필드: stock_code(5자리 문자), hkats_code, underlying_name, weekly_launch_date, launch_source_url, roster_page_updated_at, retrieved_at, retrieved_timezone, source_url, availability_status. — [명부 출처](https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options/Weekly-Stock-Options?sc_lang=en)
- 7월 발표52개와 명부54개의 차이는 이후 ZJI(03308,7월30일), SHN(00625,9월1일) 추가로 설명된다. 출시 공지는 각각 주식 상장을 전제로 했고, 현재 명부에도 두 클래스가 등재되어 있다. — [7월13일52개](https://www.hkex.com.hk/News/News-Release/2026/260713news?sc_lang=en), [Zhongji InnoLight](https://www.hkex.com.hk/News/News-Release/2026/260727news?sc_lang=en), [SHEIN](https://www.hkex.com.hk/News/News-Release/2026/260828news?sc_lang=en)

| 위클리 출시일 | 추가 클래스 수 | HKATS 클래스 | 공식 근거 |
|---|---:|---|---|
| 2024-11-04 | 10 | HKB HEX TCH KST BYD PAI MET JDC BIU ALB | [출시 통지](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2024/EQD_09_24_e.pdf) |
| 2025-06-02 | 1 | CAT | [CATL](https://www.hkex.com.hk/News/News-Release/2025/250516news?sc_lang=en) |
| 2025-11-10 | 5 | CNC CHT SMC AIA MIU | [5개 추가](https://www.hkex.com.hk/News/News-Release/2025/251009news?sc_lang=en) |
| 2026-06-15 | 10 | ANA ZJG WXB WXA ZJM LAO BLI AKS TRP POP | [17개 추가](https://www.hkex.com.hk/News/News-Release/2026/260427news?sc_lang=en) |
| 2026-06-22 | 7 | SHK GAH LAU SNO CLI PEN NTE | [17개 추가](https://www.hkex.com.hk/News/News-Release/2026/260427news?sc_lang=en) |
| 2026-07-09 | 1 | LSP | [Luxshare](https://www.hkex.com.hk/News/News-Release/2026/260708news?sc_lang=en) |
| 2026-07-30 | 1 | ZJI | [Zhongji](https://www.hkex.com.hk/News/News-Release/2026/260727news?sc_lang=en) |
| 2026-08-10 | 6 | MNX ZTE KAT KCH YOF UBR | [18개 추가](https://www.hkex.com.hk/News/News-Release/2026/260713news?sc_lang=en) |
| 2026-08-17 | 6 | SGM ZMI WCP KEH ZLT NIO | [18개 추가](https://www.hkex.com.hk/News/News-Release/2026/260713news?sc_lang=en) |
| 2026-08-31 | 6 | MTU SBI ZSI GST TPX VGT | [18개 추가](https://www.hkex.com.hk/News/News-Release/2026/260713news?sc_lang=en) |
| 2026-09-01 | 1 | SHN | [SHEIN](https://www.hkex.com.hk/News/News-Release/2026/260828news?sc_lang=en) |

- 주식옵션은 미국형·실물인수도이며 주당 HKD 프리미엄으로 표시된다. 위클리는 당주·차주, 주간 마지막 영업일 만기이며 월물과 같은 만기일에는 중복 위클리를 상장하지 않는다. 주간 거래시간09:30–12:00,13:00–16:00(HKT); 행사 후 주식결제T+2, 프리미엄T+1. — [주식옵션 명세](https://www.hkex.com.hk/Products/Listed-Derivatives/Single-Stock/Stock-Options?sc_lang=en)
- 지수 위클리는 HSI / HHI(HSCEI) / HTI(HSTECH)로 분리한다. 모두 HKD50/지수포인트이며 코드 예시는 HSI27000A9W25, HHI10400A9W25, HTI3500J4W25처럼 만기일 W접미를 사용한다. 공식 예시일 뿐 현재 거래계약이 아니다. HSI·HSCEI출시는2019-09-16, HSTECH출시는2024-09-02. — [HSI](https://www.hkex.com.hk/Products/Listed-Derivatives/Equity-Index/Hang-Seng-Index-%28HSI%29/Weekly-Hang-Seng-Index-Options?sc_lang=en), [HSCEI](https://www.hkex.com.hk/Products/Listed-Derivatives/Equity-Index/Hang-Seng-China-Enterprises-Index/Weekly-Hang-Seng-China-Enterprises-Index-Options?sc_lang=en), [HSTECH](https://www.hkex.com.hk/Products/Listed-Derivatives/Equity-Index/Hang-Seng-TECH-Index-Futures-and-Options/Weekly-Hang-Seng-TECH-Index-Options?sc_lang=en), [출시 규칙 변경](https://www.hkex.com.hk/Services/Rules-and-Forms-and-Fees/Rules/HKFE/Rules/Rule-Update_Rules%2C-Regulations-and-Procedures-of-the-Futures-Exchange?sc_lang=en)
- 2026-07-20부터 관련 지수 야간 시작이17:15에서17:00으로 변경되었다. 현재 야간은17:00–익일03:00, 만기 계약 주간 마감은16:00이다. 과거 캘린더에 현재 시간표를 소급 적용하지 않아야 한다. — [야간 변경](https://www.hkex.com.hk/Services/Trading/Derivatives/Overview/Trading-Mechanism/After-Hours-Trading?sc_lang=en), [HSI 규격](https://www.hkex.com.hk/Products/Listed-Derivatives/Equity-Index/Hang-Seng-Index-%28HSI%29/Weekly-Hang-Seng-Index-Options?sc_lang=en)

### Inferences
- 최신54개를 모든 과거일에 고정해 생존자 편향을 만들지 말고 출시 코호트로 과거 유니버스를 구성한다. 2026년 신규 클래스는 관측 이력이 짧으므로 2~3년 패널을 갖는다고 전제할 수 없다.
- 국내 지수옵션과 홍콩 미국형 개별주식옵션은 배당·조기행사·기업행사 구조가 달라 통합 가격모형을 곧바로 학습시키기보다 지수 전이와 개별주식 전이를 분리하는 것이 적절하다.

### Gaps
- 54개는 공식 클래스 명부이며 당일 활성 시리즈 수, 거래량이 있는 시리즈 수, 각 세션 거래 가능 여부는 확인하지 않았다.
- 현재 모든 조정계약과 계약승수를 개별 시리즈까지 추출하지 않았다. CSV의 회사명·클래스코드는 현재 명부 기준이며 과거 명칭 변경까지 포함한 마스터가 아니다.

## 2. HKEX 데이터셋과 실제 접근 방식은 무엇인가?

### Takeaway
HKEX Data Marketplace는 무료 REST JSON 시세 API가 아니라 계정·라이선스 기반의 데이터 상품 구매/구독·파일 전달 플랫폼이다. 실시간 OMD-D는 별도의 바이너리 시장데이터 피드이며, NH REST 호출구조와 다르다.

### Cited Findings
| 자료 | 범위·내용 | 주기·역사 | 접근·검증 상태 |
|---|---|---|---|
| CFBD-SOM Historical Full Book CSV | 주식옵션 주문 추가·변경·취소, 체결·체결취소, 참조정보 | 일별파일. 기존상품 최초발행2014-12-01; 위클리는 출시 후부터 | 유료 상품. 현재 CSV열·샘플 미다운로드. [상품](https://data.hkex.com.hk/catalog/dataset/44c1441a763911ef953342323a43f021)·[과거 공식 상품정보](https://www.hkex.com.hk/eng/ods/historicalDataProfile.aspx?ProductID=AXKl3G5PDbgXlQR0tfjyV%2Ff%2B%2FyiJKtxtJSyQXVPTL4A%3D&SchemeID=SfuO1%2FAc2Za7Gwz7%2Fyyx6zvnn4uzzHGD%2B7D9oKwQ7Vo%3D) |
| CFBD-NSOM Historical Full Book CSV | 주식옵션을 제외한 선물·옵션. 지수위클리는 여기 포함 | 카탈로그 시작2014-12-01; 다음날11:30HKT 전후 전달 안내 | 가격표에는 월HKD1,500이 표시되나 기간·권리별 견적 확인. [상품](https://data.hkex.com.hk/catalog/dataset/c712edce763911ef953342323a43f021) |
| Trade File SOM / Non-SOM | 거래별 시각·가격·수량 중심. Full Book과 별도 상품 | 바이너리 과거상품 확인, 현재 카탈로그 코드·상세 범위 미확정 | 호가·OI 제공으로 오인하지 않음. [공식 과거 카탈로그](https://sc.hkex.com.hk/TuniS/www.hkex.com.hk/eng/ods/historicalData.aspx) |
| BASFOD Best Bid/Ask | 표준 주식선물·옵션의 장중 최우선 매수/매도 가격·잔량 | 일별 CSV/fixed-length. 조회된 페이지의 범위2025-10-01이후 | 다단계/주문별 데이터가 아님. 더 오래된 자료 및 조정계약 문의. [상품](https://data.hkex.com.hk/catalog/dataset/a1c614abe56f4ea4a2c3b8765029a0a4) |
| End of Day Summary – All Futures/Options | 표준 선물·옵션의 일별 거래 통계 | 일별 | 정확한 OI·IV·정산가 열은 샘플 확인 필요. [카탈로그](https://data.hkex.com.hk/?lang=en) |
| 공개 Daily Market Report / DTOP | 시장별 거래 통계와 미결제약정 보고서 | 일별·과거 보고서 경로 | DTOP에서는 위클리 시장을 따로 구분. 무료 웹 열람과 재배포 허가는 별도. [일별보고서](https://www.hkex.com.hk/Market-Data/Statistics/Derivatives-Market/Daily-Market-Report-(Latest)?sc_lang=en)·[위클리 기술안내](https://www.hkex.com.hk/-/media/HKEX_Common/Market/Products/Listed-Derivatives/Single-Stock/Weekly-Stock-Options/Overview-of-Technical-Documentation-for-WSO.pdf) |
| RP006 Series Prices | Series, Market, Commodity, Currency, Settlement Price, Previous Settlement, Difference, IV | RP006 / INTRADAY / FINAL 유형 | 정산가격 자료. 공개 명세 record01에 OI는 없음. [필드 명세](https://www.hkex.com.hk/eng/market/rm/rm_dcrm/riskdata/srprices/seriespricesFormat.htm) |
| Weekly Series + RPF + TP011 | 비월물 시리즈 참조, 위험 파라미터, 기업행사 전후 조정 연결 | 위클리 주식옵션은 첫 거래일부터 만기까지 참조정보 제공 | Weekly Series 링크는 찾았으나 실제 행은 확보 못함. [참조 경로](https://www.hkex.com.hk/eng/stat/dmstat/dayrpt/web_series_idx.htm)·[기술안내](https://www.hkex.com.hk/-/media/HKEX_Common/Market/Products/Listed-Derivatives/Single-Stock/Weekly-Stock-Options/Overview-of-Technical-Documentation-for-WSO.pdf) |

- 전달방식은 direct download, SFTP, cloud-to-cloud(S3)다. 웹 계정 이메일·비밀번호로 로그인하고, 라이선스를 받은 데이터에 Download가 표시된다. 공개 고객용 REST base URL, bearer-token 발급, pagination 명세는 이번 확인에서 발견하지 못했다. 내부 웹 요청을 공식 API라고 추정하지 않는다. — [서비스 소개](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/HKEX-Data-Marketplace?sc_lang=en), [사용자 가이드](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/-/media/08660B4BD3874369BAFF9CE983ED98FD.ashx)
- SFTP는 sftp.data.hkex.com.hk:22, 사용자명은 Marketplace 이메일, OpenSSH 공개키 등록 후 로컬 개인키로 인증한다. 예: /CFBD-SOM/HKEX-DAILY-DERIVATIVES-SOM/HKEX/YYYY/MM/DD 및 /CFBD-NSOM/HKEX-DAILY-DERIVATIVES-NON-SOM/HKEX/YYYY/MM/DD. 주문은 /Downloads/Order_ID_DXXXXXX. 일별 구독파일·역사주문·생성다운로드는 통상14일 내려받기 보관창이다. 이는 데이터 역사14일 제한이 아니다. — [SFTP 가이드 v1.3](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/-/media/1BC625C24564466B83E98212152F8EF7.ashx)
- 실시간 OMD-D: Standard는 집계 가격별(conflated market-by-price), Premium은 streaming market-by-price, FullTick은 streaming market-by-order다. FullTick 단독으로 공식 통계/OI가 모두 온다고 가정하지 말아야 한다. 개별 주문정보는 경매시간에도 동일하게 제공된다고 가정할 수 없다. SOM/Non-SOM은 구독·호스트가 구분된다. — [OMD-D](https://www.hkex.com.hk/OMDD?sc_lang=en), [FAQ](https://www.hkex.com.hk/Global/Exchange/FAQ/Market-Data?sc_lang=en)

### Inferences
- 첫 국내→홍콩 전이는 일별 OI·정산자료 + 현물/지수/선물 1분가격을 확보하는 단계가 적절하다. H9b 유동성 분석에서만 Full Book 또는 최소 최우선 호가 이력이 필수로 추가된다.
- CFBD-SOM만 구매하면 현물 주식 가격 틱은 포함되지 않는다. REV와 실현변동성에는 현물 Securities 자료 또는 별도 현물 시세 공급자가 필요하다. 지수값도 별도 라이선스·필드 범위를 확인해야 한다.

### Gaps
- Marketplace의 실제 유료 CSV/바이너리 샘플·열 이름·압축파일 구성·행별 타임스탬프 정밀도를 확인하지 못했다. OMD 바이너리 명세의 필드를 역사 CSV에 그대로 대응한다고 확정하면 안 된다.
- 일반적인 API라는 문구가 다른 상품 안내에 있어도 위 파생상품의 공개 REST endpoint/auth/pagination이 확인된 것은 아니다. 추가 자동화 API가 있는지 영업/기술지원에 문의해야 한다.
- 논문/공개 대시보드용 파생 그래프, 원시 CSV 재배포, 연구실 공동사용 권리는 별도 확인한다. 과거 카탈로그의 가격·전달시간과 현재 Marketplace가 다르면 현재 상품·견적을 우선한다.

## 3. 클래스에서 실제 계약·거래·OI를 연결하는 방법과 다음 실행

### Takeaway
기초주식 코드와 HKATS 클래스만으로 계약이 유일해지지 않는다. 참조정보를 먼저 저장하고 OrderbookID·유효일·시장·만기·콜풋·행사가·기업행사 수정자를 유지해야 한다.

### Cited Findings
- OMD-Dv1.49: 301 Commodity →302 Class →303 Series Base /304 Series Extended 연결. 303은 OrderbookID, Symbol, ExpirationDate(YYYYMMDD), StrikePrice·소수점, PutOrCall(1call/2put);304는 Market, InstrumentGroup, Modifier, CommodityCode, ContractSize, 실제 만기·첫/마지막 거래시각을 포함한다. 승수는 DecimalInContractSize 적용; 조정은 Modifier/TP011로 추적한다. 주식위클리 Market18와145, 지수 HSI39·HHI87·HTI84를 구분한다. OI366은 DayIndicator·Settlement·GrossOI·NetOI·Turnover이며 당일/전일과 수정 발행을 보존한다. SendTime은 UTC epoch nanoseconds 표현이나 정밀도ms, TradeTime은1/100초다. 나노초 표현을 나노초 정확도로 해석하지 않는다. — [OMD-D 바이너리 명세 v1.49 §3.3,3.7,3.10,3.12,8.4](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Market-Data-Services/Infrastructure/HKEX-Orion-Market-Data-Platform-Derivatives-Market-OMD-D/HKEX_OMD_Derivatives_Binary_Interface_Specifications_v1-49.pdf)
- TP011은 자본조정 전후 계약, Weekly Series와 RPF는 실제 위클리 시리즈 정보를 연결하는 데 사용된다. 위클리 주식옵션은 일반적인 사전상장 없이 첫 거래일부터 그 정보가 공개된다. — [위클리 기술안내](https://www.hkex.com.hk/-/media/HKEX_Common/Market/Products/Listed-Derivatives/Single-Stock/Weekly-Stock-Options/Overview-of-Technical-Documentation-for-WSO.pdf)
- OMD-D 사이트에는 현재v1.49와 ODP 이행 후용v2.3가 함께 게시되어 있고 후자는 이행 이후에만 유효하다고 명시한다. 버전번호가 높다는 이유만으로 새 명세를 현재 운영 피드에 적용하지 않는다. — [명세 버전 구분](https://www.hkex.com.hk/OMDD?sc_lang=en)

### Inferences
제안 정규화 테이블(설계이며 제공처의 원래 CSV열이 아님):
1. underlying_master: exchange, stock_code, hkats_class, underlying_name, asset_type, valid_from/to.
2. contract_master: source_date, market, orderbook_id, symbol, underlying_id, expiry_date, call_put, strike, strike_scale, contract_size, modifier, currency, first/last_trading_time, exercise_style, settlement_type.
3. daily_clearing: business_date, publication_time, contract_id, gross_oi, net_oi, settlement, revision.
4. trades_quotes: exchange_time, receive_time, sequence, session, contract_id, event_type, trade_id/order_id, price, quantity, side, corrections.
5. corporate_actions/calendar: effective_at와 known_at을 나눠 기업행사·거래시간 변경의 미래정보 누출 방지.

최소 샘플 요청:
- HSI·HHI·HTI 지수 위클리 및 TCH·ALB·HKB 등 주식 위클리 각각 정상일·만기일·휴일전날, 조정계약이 존재하는 날의 작은 파일.
- 동일 날짜 CFBD-SOM/NSOM, daily OI·정산가격, 301~304에 대응하는 참조정보, TP011 및 기초자산 가격을 함께 요청.
- 조정·무거래·거래정지·실제 만기 예외·체결취소·주야간 귀속, OI 공표시각, 가격/승수 소수점, UTC/HKT를 검증하고 1분 바와 향후5거래일 RV를 생성.
- H5/H6는 일별 OI·만기와 장중 기초가격, REV는 현물 종가전30분·종가·다음개장·+1분·+30분, H9b는 event-level 호가/체결과 비용을 우선 확보.

### Gaps
- 이번 결과에는 실제 매매가격 sample row 또는 최신 활성 option-series row가 없다. 공개 Weekly Series 경로를 읽었으나 도구에서 행이 노출되지 않았고 유료 파일 접근도 수행하지 않았다.
- 공개 명부 CSV는 코드·상품명·상장 코호트 검토용이다. 아직 가격/OI 분석용 패널이나 거래 가능한 주문 종목 마스터가 아니다.
