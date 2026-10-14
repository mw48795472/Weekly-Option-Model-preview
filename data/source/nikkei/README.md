# 일본 닛케이225 · J-Quants 수집 상태

연구 대상은 일본 OSE의 Nikkei 225 mini Options (NK225MWE)이며 데이터 원천은 J-Quants다. 개인용 Premium과 Pro는 API 주소·인증·필드명이 다르다. 서비스·구독 권한은 사용자 확인 대기이며 실제 인증·가격·OI 수집은 아직 실행하지 않았다.

20261013 폴더의 TAIFEX 요청 metadata는 이전 작업의 역사 기록이다. 해당 실패를 J-Quants 요청 수·실패·접근권한 판단에 사용하지 않는다. 현재 일본 상태는 data/analysis/nikkei/summary.json, 서비스별 경로는 api_routes.csv에서 확인한다.

scripts/collect_nikkei.py --service personal --date 2026-10-08 은 오프라인 요청 계획만 표시한다. Pro는 --service pro를 지정한다. 실제 API 호출 기능으로 해석하지 않는다.

키·토큰 및 라이선스 원자료는 Git과 공개 다운로드에 포함하지 않는다. 사용자 허용 범위의 원본 저장 위치는 Git에서 제외된 data/private/nikkei/다.

공식 명세: https://jpx-jquants.com/en/spec/drv-bars-daily-opt · https://jpx.gitbook.io/j-quants-pro/api-reference/options
