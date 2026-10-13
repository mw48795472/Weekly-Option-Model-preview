# 닛케이225 기반 확장: 실제 상품 확인과 확보 범위

## TAIFEX에서 닛케이225를 수집할 수 있는가

### Takeaway
공식 TAIFEX 상품표에는 닛케이225/NK가 없다. 일본 지수 상품은 TOPIX 선물(TJF)이며 닛케이225 위클리옵션의 대체물이 아니다. 이 작업에서 닛케이225 가격·OI 원본은 확보하지 못했고 H5·H6 실측을 실행하지 않았다.

### Cited Findings
- TAIFEX 주가지수선물은 TOPIX와 미국·영국 지수 등을 열거하고, 지수옵션은 TAIEX·전자·금융 지수 상품을 열거한다. Nikkei225는 명시돼 있지 않다. — [TAIFEX Products](https://www.taifex.com.tw/enl/eng2/products)
- TJF의 기초지수는 TOPIX다. 상품명이 일본 지수라는 이유로 닛케이225로 재명명할 수 없다. — [TAIFEX TOPIX futures](https://www.taifex.com.tw/enl/eng2/tJF?menuid1=12)
- 실제 API 접근 시도는 DailyMarketReportFut와 IndexFuturesAndOptionsMargining 각 1회였다. 로컬 네트워크 PermissionError로 모두 응답 원문을 얻지 못했다. 승격 재시도도 승인대기 후 중단됐으며 API 성공·응답에 NK가 없다는 주장을 하지 않는다. — [수집 감사 manifest](../../data/source/nikkei/20261013/manifest.json)

### Inferences
- 요청의 의미는 기존 TAIFEX H5·H6 연구 설계를 OSE 닛케이225 옵션에 전이하는 것으로 구현하는 것이 맞다. 거래소와 기초지수 식별자는 별도로 유지한다.

### Gaps
- 키가 없어 막힌 것으로 확인되지 않았다. 이번 실패는 로컬 네트워크 권한 문제이며 서비스 HTTP 응답은 얻지 못했다.

## JPX/OSE 닛케이225 옵션의 데이터와 제도는 무엇인가

### Takeaway
정확한 비교 대상은 OSE Nikkei225 mini Options다. 공개 파일에 어떤 필드가 있는지는 확인했으나 파일 다운로드·원문 검증은 완료되지 않았다. 최근 옵션이론가격 CSV만으로 OI 예측력 검정이 가능하다고 볼 수 없다.

### Cited Findings
- Mini옵션은 2023-05-29 개시, 수요일 만기는 2025-05-26 도입, 승수는 JPY100이다. 금요일·수요일 SQ와 직전 영업일 최종거래일을 구분하며 휴일에는 SQ가 앞당겨진다. — [공식 계약규격](https://www.jpx.co.jp/english/derivatives/products/domestic/225mini-options/01.html)
- 표준 Nikkei225 Options와 mini Options는 서로 다른 계약단위·만기구조다. — [공식 mini 개요](https://www.jpx.co.jp/english/derivatives/products/domestic/225mini-options/index.html)
- 공개 옵션이론가격 CSV는 최근 약2개월, 종목코드·월물·프리미엄종가·이론가격·변동성·기초지수 종가를 제공한다고 명시한다. 안내 필드에 OI는 없다. 이론가격과 실제 체결가격은 구분해야 한다. — [JPX User Guide](https://www.jpx.co.jp/english/markets/derivatives/option-price/01.html)
- 일보는 다음 영업일 약09:00 JST 갱신되며 지수옵션 파일 siop_dyr_YYYYMMDD.pdf를 제공한다. 휴일거래 통계는 별도로 공표하지 않고 지정된 영업일에 합산된다. — [OSE Daily Report](https://www.jpx.co.jp/english/markets/statistics-derivatives/daily/)
- Nikkei 공식사이트는 공개 일별 지수 CSV 약3년을 안내한다. 공개 조회와 재배포 허가는 별개이며 개인이용·인용을 넘어서는 사용에는 별도 라이선스를 명시한다. — [Nikkei data provision](https://indexes.nikkei.co.jp/nkave/data/index.en.html)
- JPX 사이트는 일반 공개자료를 오픈데이터로 제공한다고 명시하지 않으며 상업적 수집·2차이용에는 사전허가/유료계약 조건이 있다. — [JPX Terms](https://www.jpx.co.jp/english/term-of-use/index.html)

### Inferences
- 타이베이/도쿄 현지일자를 그대로 조인하면 거래시간·휴일·야간 귀속 차이로 선행정보가 섞일 수 있다. timezone와 available_at을 UTC로 비교해야 한다.
- TAIFEX 수요일 만기/금요일 제도변경 변수를 그대로 붙이면 잘못된 설명변수가 된다. OSE 자체의 실제 SQ·최종거래일·수요일 도입 전후를 따로 정의해야 한다.

### Gaps
- OI 계약별 장기 시계열·실제 옵션 OHLC/체결량·행사가별 IV·현물 intraday 데이터·기업배당/구성종목변경·사용 및 공개배포 권한이 필요하다.
- 이번 작업은 닛케이 원본을 다운로드하거나 재배포하지 않았다. 가격 수준/수익률/통계결과를 허구로 생성하지 않는다.

## 다음 실측 실행 조건과 재현 코드

### Takeaway
공개 결과는 상품·자료 가용성 감사와 필요한 데이터 표다. 로컬 CSV 검증기는 준비하지만 실제 실증 결과는 자료 확보 전까지 미실행으로 유지한다.

### Cited Findings
- 본 저장소의 collect_nikkei.py는 키 없는 TAIFEX 접근증거만 기본 수집한다. 선택적인 JPX/Nikkei 페이지 검사는 data/private/에 보관하며 Streamlit 시작 시 네트워크 수집하지 않는다. — [수집 스크립트](../../scripts/collect_nikkei.py)
- analyze_nikkei.py는 기본적으로 public summary/status/required_data를 만들고, 허용된 현물 CSV를 입력한 경우에만 로컬 전용 기초 통계를 계산한다. 입력 형식은 date,open,high,low,close이며 날짜중복·가격양수·OHLC 순서를 검증한다. 이 계산을 H5/H6라고 부르지 않는다. — [분석 스크립트](../../scripts/analyze_nikkei.py)

### Inferences
- H5: 실제 OSE 월물별 최종거래일과 SQ를 현물 세션에 정렬하고 수요일 도입·요일·월간SQ·휴일 대체일을 통제한다. SQ는 시초가 기준이므로 일중 마감까지의 변동성과 같은 사건이 아니다. 사건창별 intraday 보강이 우선이다.
- H6: 동일 계약의 5영업일 전후 OI, 만기/행사가/moneyness와 계약 승수를 보존한다. OI 공표시각 이전 예측에는 전일 가용분만 사용하고 정규/야간 합산으로 OI를 두번 세지 않는다. 동일일 평가, 5일 타깃 중첩 purge와 block interval을 적용한다.
- 장기 목표는 2023-05-29~최근완료일, 최소 12~24개월 평가표본과 수요일 도입 전후를 모두 확보하는 것이다. 고정된 날짜수가 검정력 확보를 보장하지 않으므로 기존 효과크기/신뢰구간 기반 표본설계로 다시 산정한다.

### Gaps
- 현재 닛케이 실측 관측치0, 옵션 OI0, H5/H6 검정 미실행. 데이터 접근/이용허가 뒤 local-only 계산을 검증하고 공개할 파생통계 허용범위를 확인해야 한다.
