# NH선물 API 49종 색인

수집일: 2026-10-11 (KST). 원본 Excel은 바이트 변경 없이 보존했습니다.

필드 단위 정의·원본 행 번호는 `data/catalog/catalog.json`, 해시는 `source_manifest.json`, 업로드본 비교는 `audit.json`을 참조합니다.

| API | 명칭 | 방식 | 호출 분류 | Excel | 공식 문서 |
|---|---|---|---|---|---|
| `revoke` | 접근토큰 폐기 | POST | API 디폴트 | [다운로드 원본](../vendor/nh/2026-10-11/individual/auth/revoke.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=10&a=79&v=1) |
| `token` | 접근토큰 발급 | POST | API 디폴트 | [다운로드 원본](../vendor/nh/2026-10-11/individual/auth/token.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=10&a=8&v=1) |
| `web-socket-key` | 웹소켓 키 발급 | GET | API 디폴트 | [다운로드 원본](../vendor/nh/2026-10-11/individual/auth/web-socket-key.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=10&a=80&v=1) |
| `domestic/cancel-night` | 국내_취소주문(야간) | POST | 주문 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_cancel-night.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=121&a=239&v=1) |
| `domestic/cancel` | 국내_취소주문 | POST | 주문 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_cancel.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=238&v=1) |
| `domestic/chart-daily` | 국내_차트(일) | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_chart-daily.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=237&v=1) |
| `domestic/chart-minute` | 국내_차트(분) | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_chart-minute.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=236&v=1) |
| `domestic/deposit` | 국내_예수금조회 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_deposit.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=223&v=1) |
| `domestic/modify-night` | 국내_정정주문(야간) | POST | 주문 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_modify-night.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=121&a=231&v=1) |
| `domestic/modify` | 국내_정정주문 | POST | 주문 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_modify.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=230&v=1) |
| `domestic/open-interest` | 국내_잔고내역 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_open-interest.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=227&v=1) |
| `domestic/order-error` | 국내_주문오류내역 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_order-error.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=235&v=1) |
| `domestic/order-history` | 국내_주문내역 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_order-history.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=216&v=1) |
| `domestic/order-night` | 국내_신규주문(야간) | POST | 주문 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_order-night.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=121&a=222&v=1) |
| `domestic/order` | 국내_신규주문 | POST | 주문 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_order.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=221&v=1) |
| `domestic/orderable-quantity` | 국내_주문가능수량 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_orderable-quantity.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=120&a=234&v=1) |
| `domestic/price-all-futures` | 국내_선물전체시세 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_price-all-futures.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=219&v=1) |
| `domestic/price-all-option-night` | 국내_옵션전체시세(야간) | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_price-all-option-night.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=119&a=226&v=1) |
| `domestic/price-all-option` | 국내_옵션전체시세 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_price-all-option.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=225&v=1) |
| `domestic/price-bid` | 국내_호가 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_price-bid.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=244&v=1) |
| `domestic/price-expect-fill` | 국내_종목예상체결가 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_price-expect-fill.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=232&v=1) |
| `domestic/price-night` | 국내_현재가(야간) | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_price-night.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=119&a=243&v=1) |
| `domestic/price` | 국내_현재가 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_price.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=242&v=1) |
| `domestic/product-detail` | 국내_품목별세부정보 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_product-detail.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=241&v=1) |
| `domestic/trend-investor` | 국내_투자자직전매매동향 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/domestic/domestic_trend-investor.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=118&a=240&v=1) |
| `overseas/bid-price` | 해외_호가 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_bid-price.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=124&a=277&v=1) |
| `overseas/chart-daily` | 해외_차트(일) | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_chart-daily.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=124&a=274&v=1) |
| `overseas/chart-minute` | 해외_차트(분) | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_chart-minute.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=124&a=273&v=1) |
| `overseas/cumulative-pl` | 해외_누적손익현황 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_cumulative-pl.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=261&v=1) |
| `overseas/deposit` | 해외_예수금조회 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_deposit.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=265&v=1) |
| `overseas/market-operations` | 해외_장운영정보 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_market-operations.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=124&a=268&v=1) |
| `overseas/open-interest-expiry` | 해외_보유포지션만기조회 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_open-interest-expiry.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=264&v=1) |
| `overseas/open-interest` | 해외_잔고내역 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_open-interest.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=267&v=1) |
| `overseas/order-error` | 해외_주문오류내역 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_order-error.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=272&v=1) |
| `overseas/order-history` | 해외_주문내역 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_order-history.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=263&v=1) |
| `overseas/order` | 해외_주문 | POST | 주문 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_order.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=270&v=1) |
| `overseas/orderable-quantity` | 해외_주문가능수량 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_orderable-quantity.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=271&v=1) |
| `overseas/price-all-option` | 해외_옵션전체시세 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_price-all-option.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=124&a=266&v=1) |
| `overseas/price` | 해외_현재가 | POST | 시세 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_price.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=124&a=276&v=1) |
| `overseas/product-detail` | 해외_품목별세부정보 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_product-detail.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=124&a=275&v=1) |
| `overseas/product-expiry` | 해외_만기일조회 | POST | 계좌 LIMIT | [다운로드 원본](../vendor/nh/2026-10-11/individual/overseas/overseas_product-expiry.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=125&a=262&v=1) |
| `FA` | 해외_시세체결 | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/FA.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=126&a=180&v=1) |
| `FB` | 해외_시세호가 | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/FB.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=126&a=189&v=1) |
| `KA` | 국내_시세체결 | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/KA.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=123&a=191&v=1) |
| `KB` | 국내_시세호가 | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/KB.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=123&a=192&v=1) |
| `KC` | 국내_시세체결(야간) | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/KC.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=123&a=193&v=1) |
| `KD` | 국내_시세호가(야간) | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/KD.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=123&a=194&v=1) |
| `O1` | 해외_주문/체결 | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/O1.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=126&a=190&v=1) |
| `O1_K` | 국내_주문/체결 | WEBSOCKET | 전체 실시간 구독 제한은 20개입니다. | [다운로드 원본](../vendor/nh/2026-10-11/individual/websocket/O1_K.xlsx) | [페이지](https://apidev.futures.co.kr/#/api?g=123&a=207&v=1) |
