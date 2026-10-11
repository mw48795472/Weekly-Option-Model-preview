# 연구 재현 및 운영 안내

README의 [핵심 그래프와 분석](../README.md)을 재현하거나 실제 시세 수집 경로를 확인하는 절차입니다. 저장소 루트에서 Python 3.10 이상을 사용합니다. 기본 분석은 보존된 2026-10-11 공개자료를 사용합니다.

## 오프라인 분석과 검증

```sh
python -m pip install -e ".[dashboard,streamlit]"
python scripts/build_catalog.py
python scripts/analyze_masters.py
python scripts/build_contract_exports.py
python scripts/analyze_reversal.py
python scripts/analyze_hypotheses.py
python -m unittest discover -s tests -v
```

카탈로그·마스터·계약 CSV·REV 가용성·가설 진단을 순서대로 재생성합니다. 결과는 `data/analysis/` 등에 저장되며 API나 키를 사용하지 않습니다. 같은 스냅샷의 재현이지 현재 거래 가능 종목을 새로 조회한 결과가 아닙니다.

공식 개별 Excel 49개, 사용자 제공 통합 Excel 1개, 공개 국내 종목 마스터 3개는 `vendor/nh/2026-10-11/`에 보존되어 있습니다. 카탈로그의 형식 차이는 `data/catalog/audit.json`을 참고하세요.

## 대시보드 및 HTML mock

Streamlit은 [별도 실행 안내](streamlit-dashboard.md)를 따릅니다. 서버가 실행 중이면 [로컬 대시보드](http://127.0.0.1:8501/)에서 사용할 수 있습니다.

정적 마스터 대시보드와 단일 HTML PoC를 로컬에 생성하려면:

```sh
python scripts/render_dashboard.py
python scripts/build_poc.py
```

`artifacts/private/dashboard/index.html` 또는 `weekly_option_poc.html`을 브라우저에서 엽니다. Plotly가 HTML에 포함되어 오프라인에서도 작동합니다. 필요하면 생성물 폴더만 서버로 제공합니다.

```sh
python -m http.server 8765 --bind 127.0.0.1 --directory artifacts/private/dashboard
```

배포용 HTML·ZIP을 다시 생성하려면:

```sh
python scripts/build_poc.py --output docs/downloads/weekly_option_poc.html --zip
```

배포본은 약 10MB의 단일 HTML에 마스터 요약·종목 CSV·변수 사전·기존 PNG 6개를 포함합니다. 템플릿은 `templates/research_poc.html`입니다. 자료를 갱신하면 README의 다운로드 커밋도 새 파일을 포함한 커밋으로 갱신합니다.

## Word 보고서

```sh
python -m pip install -e ".[reports]"
python scripts/build_hypotheses_docx.py --source-ref main
```

[통합 보고서](hypotheses-review.md)와 클릭 가능한 근거 링크를 Word로 만듭니다. 생성 명령만으로 페이지 배치를 검증할 수는 없으므로 배포 전 문서를 열어 표·페이지·링크를 확인합니다.

## 요청 구조 확인

```sh
nh-research doctor
nh-research plan --api domestic/price --params examples/price_query.json
```

`doctor`는 환경변수 `NH_APPKEY`·`NH_APPSECRET`의 설정 유무만 표시합니다. `plan`은 키를 사용하거나 전송하지 않고 요청 요약을 만듭니다. 두 명령은 `.env`를 자동으로 읽지 않습니다. 예시 종목코드는 보존된 마스터 기준이므로 실제 조회 전 최신 마스터와 대조해야 합니다.

`contracts.py`는 요청 구성기, `client.py`는 모의 인증·읽기 전용 HTTP 전송기입니다. WebSocket은 메시지 구성만 지원하며 실시간 수집은 아직 구현하지 않았습니다.

## 시세 권한 확인 후 모의 수집

보존된 검증 기록의 모의 인증은 `scopes=S`, 유효기간 86,400초로 성공했고 국내 현재가·일봉·분봉·옵션전체시세는 `403 / EGW016`이었습니다. 이 기록은 현재 권한을 새로 조회한 결과가 아닙니다.

`.env.example`을 저장소 루트의 `.env`로 복사하고 모의 `NH_APPKEY`, `NH_APPSECRET`을 설정합니다. `NH_ENV=demo`를 유지합니다. `.env`는 Git에서 제외되며, 수집기가 읽습니다. 같은 이름의 환경변수가 있으면 환경변수가 우선합니다.

```sh
python scripts/collect_demo.py
python scripts/render_dashboard.py --snapshot data/private/demo_snapshot.json
```

수집기는 모의 서버만 사용하며 주문·잔고 조회는 허용하지 않습니다. 토큰은 메모리에만 보관하고 원본 응답·로컬 분석은 Git 제외 경로에 저장합니다. 성공 여부는 종료 코드와 snapshot의 `failures`·데이터셋 목록을 함께 확인합니다. 공개 Streamlit 앱은 이 비공개 snapshot이나 `.env`를 읽지 않습니다.

시세가 확보되면 정적 대시보드에서 유효 OHLC 일봉·분봉과 20개 수익률 관측치 기반 역사적 변동성을 추가 표시할 수 있습니다. 실제 응답 검증은 남아 있습니다. 종목 선택에는 보존된 마스터를 사용하므로 실행 전 최신 코드 또는 `--symbol`을 확인합니다. REV에 실제 가격·캘린더 CSV를 넣는 규칙은 [REV 분석 문서](price-reversal-analysis.md)를 따릅니다.

## 공개 접근 상태 재검사

아래 명령은 네트워크에 포털 GET 1건과 인증 헤더 없는 시세 POST 2건을 보냅니다. 오프라인 재현 명령과 별도입니다.

```sh
python scripts/probe_public_access.py --output data/analysis/public_access_probe.json
```

최초 무인증 검사에서는 포털 200, 실전·모의 시세 주소 401이었습니다. 역사 조회 범위는 미확인입니다. 원본 문서의 예제·지시문은 분석 자료로 취급하며 실행하지 않습니다.
