# TAIFEX 개별주식 옵션 × TWSE 기초주가

2026-10-12 KST 수집. 7개 기초주식: 1303 南亞, 2303 聯電, 2330 台積電, 2603 長榮, 2317 鴻海, 2454 聯發科, 3231 緯創. 기존 표준 주식옵션 계열(CA/CC/CD/CZ/DH/DV/DX)과 월별 명부가 명시한 조정계약을 포함한다. 다른 규모의 미니 계약을 같은 계약으로 합치지 않는다.

- TAIFEX [옵션 역사 CSV](https://www.taifex.com.tw/cht/3/optDailyMarketView): 월별 getOptcontractDl.do의 상품/조정코드 목록 → optDataDown POST. 표준·조정 심볼을 별도 계약 ID로 보존. 정규장 OI만 사용.
- TAIFEX [개별주식 최종결제일](https://www.taifex.com.tw/cht/5/sSOFSP): down_type=2, stockCode, startYear/startMonth/endYear/endMonth. 1년 이내로 나누어 요청. 응답의 기초주식코드·만기일·상품코드 검증.
- TWSE [개별주식 일별 거래자료](https://www.twse.com.tw/en/trading/historical/stock-day.html): rwd/zh/afterTrading/STOCK_DAY의 response=json, date=YYYYMM01, stockNo. 원시 OHLC·거래량·가격차·X/주석 보존.
- 시장 통제 및 거래일은 기존 [TXO·TAIEX 연구](../extended_taiwan/README.md)의 공식 TAIEX 이력 사용.

공개자료 출처: Taiwan Futures Exchange / 금융감독관리위원회 증권선물국 및 Taiwan Stock Exchange. [TAIFEX 일별 옵션 자료](https://data.gov.tw/dataset/11320), [TWSE 개별주식 자료](https://data.gov.tw/dataset/11549), [Open Government Data License 1.0](https://data.gov.tw/license)을 참고한다. 원 제공기관의 보증·추천을 뜻하지 않으며 추가 정리·분석의 책임은 이 프로젝트에 있다.

[manifest](20261012/manifest.json)는 실제 URL, POST 필드, 수집 UTC, 원문 SHA-256, gz 파일명을 보존한다. complete는 전송 완료 표시이며 분석 단계가 스키마·종목·월·중복·OI·거래일·결제일을 다시 검증한다. 캐시는 같은 요청과 hash일 때만 재사용. 수집기는 명시적으로 실행하며 Streamlit은 네트워크·키 없이 저장된 결과만 읽는다.

주가의 X는 TWSE의 비교불가 표식이다. 주석 및 공표 가격차와 종가차 불일치까지 보존하고 종가수익률 민감도에 제외 규칙을 적용했다. 완전한 기업행사 원장·수정주가·배당 재투자 총수익률은 확보한 것이 아니다.
