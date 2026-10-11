# 위클리옵션 가설 심화 검토 근거

기준일은 2026-10-11 KST입니다. [통합 보고서](../../hypotheses-review.md)는 아래 세부 검토를 합친 결과입니다. [Word 버전](../../downloads/weekly_option_hypotheses_review.docx)도 제공합니다.

| 자료 | 범위 |
|---|---|
| [도입 효과와 전이](causality_transfer.md) | H1·H2·H4, 발표와 개시의 분리, 인과효과와 예측력, 해외 학습과 해외 정보 추가 |
| [포지션과 투자자 구조](position_mechanisms.md) | H3·H7·H8, 공급·소유집중·리밸런싱의 식별, NH 수급 대안 |
| [만기와 예측 실행](forecast_execution.md) | H5·H6·H9·H9b, 미래창·OI·요일 식별, 시간 검증과 체결비용 |
| [진단 JSON](../../../data/analysis/hypotheses/forecast_diagnostics.json) | 실제 저장 마스터의 설계행렬 rank와 H9 원본 인덱스 검증 |
| [설계행렬 CSV](../../../data/analysis/hypotheses/forecast_design_matrix.csv) | 상품×만기일 6개 셀. 독립 시장수익률 표본이 아님 |
| [가격·호가·차트 명세](../../../data/analysis/hypotheses/forecast_api_fields.json) | 저장된 API 문서에서 추출한 정의. 실제 응답 관측이 아님 |
| [투자자 동향 명세](../../../data/analysis/hypotheses/position_mechanisms_nh_fields.json) | 품목 단위 집계 매매 필드. 계약별 포지션 자료가 아님 |

저장소 루트에서 `python scripts/analyze_hypotheses.py`로 JSON과 CSV를 재생성합니다. 입력은 `data/analysis/contracts/weekly_contracts.csv`와 `data/catalog/catalog.json`입니다. 원자료 SHA-256과 고정 검토 기준일을 결과에 보존하며 현재 시각의 시장 상태로 갱신하지 않습니다. 실행에는 `dashboard` 추가 의존성이 필요합니다.

원 기획서와 합성 Python 소스는 로컬에서 검토했으며 원문은 이 PR에 포함하지 않습니다. 해당 출처는 [기존 감사 요약](../../source-audit.md)과 [원천 파일 목록](../../../data/analysis/weekly_option_source_inventory.json)으로 추적합니다. 합성 코드의 성능·상관·유의확률을 시장 결과로 재사용하지 않습니다. 인덱스 마커 진단도 라벨 정렬을 확인하는 소프트웨어 검증입니다.
