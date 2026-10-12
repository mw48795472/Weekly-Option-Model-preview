# 해외 위클리옵션 데이터와 API 조사

> **2026-10-12 후속 실호출 업데이트:** TAIFEX API와 공식 역사 CSV 수집에 성공했습니다. [20거래일 가격·OI 분석 및 개별 계약 티커](../../taifex-analysis.md)를 확인하세요. 아래 API 실패·미검증 기록은 최초 조사 시점의 이력으로 보존합니다.

**확인 기준: 2026-10-12 KST.** 국내 기준모형의 해외 전이를 준비하기 위한 일본·홍콩·대만 데이터 조달 조사입니다. 공식 문서·상품 규격·기초종목 명부와 실제 시세 수집 상태를 구분합니다.

**[전체 보고서 읽기](report.md)** · [메인 README 요약](../../../README.md#overseas-data)

## 전체 보고서에서 확인할 내용

| 주제 | 바로가기 |
|---|---|
| 일본 Pro REST 인증·엔드포인트·OI 공개 시각, 별도 DataCube 분봉 | [일본 데이터 구조](report.md#japan) |
| 홍콩 SOM/Non-SOM, 파일·SFTP·피드 구조, 실제 계약 식별 | [홍콩 데이터 구조](report.md#hongkong) |
| 대만 위클리 7종목, OpenAPI 실행 미검증 항목 | [대만 데이터 구조](report.md#taiwan) |
| 계약 마스터·정보 가용시각·H2/H5/H6/REV/H9b 연결 | [국내 기준모형에 연결](report.md#model-transfer) |
| 자료 확보 순서와 공급처에 전달할 문의표 | [조달·문의 체크리스트](report.md#acquisition) |

## 종목 명부와 구조화된 자료

아래 CSV·JSON은 **공개 대상 명부·문서 기반 API 맵·검증 상태**입니다. 옵션 가격·OI 원시 시계열이나 실행 가능한 인증 정보를 포함하지 않습니다. 홍콩 54개·대만 7개는 기초종목 수이며 만기·행사가·콜풋별 실제 계약 수가 아닙니다.

| 파일 | 내용·기준 |
|---|---|
| [홍콩 위클리 주식옵션 CSV](data/hkex_weekly_stock_option_classes_20261012.csv) · [JSON](data/hkex_weekly_stock_option_classes_20261012.json) | 54개 클래스의 주식코드·HKATS·기업명·출시 근거. 명부 갱신일 2026-09-01 |
| [대만 위클리 주식옵션 CSV](data/taifex_weekly_stock_option_underlyings_20261012.csv) | 7개 기초종목의 명부 코드·주식코드·상품명·출처. 효력일 2026-09-03 |
| [일본 API 맵 JSON](data/japan_api_map.json) | Pro 인증·조회 경로·query·상품 코드·출처. 실제 인증 호출 미실행 |
| [홍콩 데이터셋 목록 CSV](data/hkex_dataset_inventory.csv) | 7개 자료군의 조달·용도 비교 |
| [대만 호출 확인 기록 JSON](data/taifex_api_probe_status.json) | 스키마 취득 실패 및 데이터 GET 미검증 상태 |

GitHub 파일 화면의 **Download raw file**로 개별 파일을 저장할 수 있습니다. Excel에서 CSV를 불러올 때 코드 열은 텍스트로 지정해 선행 0을 보존하세요. 원본 수집 명부의 기준일을 유지했으며 현재 시점에 자동 갱신되지 않습니다.

## 국가별 근거 노트

[일본](sources/japan.md) · [홍콩](sources/hongkong.md) · [대만](sources/taiwan.md)

`sources/`는 보고서 작성에 사용한 공식 출처·검토 노트, `data/`는 함께 배포하는 명부·메타데이터입니다. 국가별 실제 시세 표본, 최신 활성 계약체인, 이용 권한은 별도 검증 대상입니다.
