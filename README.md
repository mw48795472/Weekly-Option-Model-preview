# Weekly-Option-Model-preview

NH선물 REST API 명세와 공개 종목 마스터를 기반으로 위클리옵션을 연구하는 저장소입니다. **모의 인증, 읽기 전용 수집기, 공개 마스터 분석 대시보드**를 제공합니다. 기준일은 **2026-10-11 KST**입니다.

## 현재 확인된 결과

- 모의 Access Token 발급 성공: `scopes=S`, 유효기간 86,400초. 키·토큰은 저장소에 포함하지 않습니다.
- 국내 현재가·일봉·분봉·옵션전체시세는 `403 / EGW016`(국내 시세조회 권한 필요). 시세 수집 및 모델 성능 평가는 아직 완료하지 않았습니다.
- 공개 마스터의 위클리 후보는 주간·야간 합계 1,258행, 중복 제거 후 **766종목**입니다.
- 상품별 고유 코드: WKI 216, WKM 440, WQI 36, WQM 74. WKI/WKM은 코스피, WQI/WQM은 코스닥 위클리 이름에 대응합니다.
- 만기별 고유 코드: **2026-10-12 286개 / 10-15 252개 / 10-19 228개**. 각 만기의 콜·풋 개수는 같습니다. 종목 수는 유동성이나 거래 활성도의 지표가 아닙니다.

![만기별 위클리 후보](docs/images/weekly_expiries.png)

[상품별 분포](docs/images/weekly_products.png) · [행사가 분포](docs/images/strike_coverage.png) · [주간·야간 분포](docs/images/session_coverage.png)

## 대시보드 실행

저장소 루트에서 실행합니다. 키 없이 공개 마스터 차트 4개, 계약 검색, CSV·JSON·PNG 다운로드가 생성됩니다. Plotly가 HTML에 포함되므로 인터넷 연결 없이도 열립니다.

```sh
python -m pip install -e ".[dashboard]"
python scripts/render_dashboard.py
```

생성된 `artifacts/private/dashboard/index.html`을 브라우저에서 엽니다. 필요하면 다음 서버를 실행하고 `http://127.0.0.1:8765`로 접속합니다. 키 파일이 있는 저장소 루트는 서버 디렉터리로 사용하지 않습니다.

```sh
python -m http.server 8765 --bind 127.0.0.1 --directory artifacts/private/dashboard
```

## 권한 승인 후 시세 수집

`.env.example`을 저장소 루트의 `.env`로 복사하고 `NH_APPKEY`, `NH_APPSECRET`에 모의 키를 입력합니다. `NH_ENV=demo`를 유지합니다. `.env`는 Git에서 제외되며, 수집기가 이 파일을 읽습니다. 같은 이름의 환경변수가 있으면 환경변수가 우선합니다.

```sh
python scripts/collect_demo.py
python scripts/render_dashboard.py --snapshot data/private/demo_snapshot.json
```

수집기는 모의 서버만 사용하고 주문·잔고 조회는 허용하지 않습니다. 토큰은 실행 중 메모리에만 보관합니다. 원본 시세 응답과 로컬 분석은 Git 제외 경로에 저장합니다. 수집 성공 여부는 종료 코드뿐 아니라 snapshot의 `failures` 및 데이터셋 목록으로 확인하세요. 인증 성공만으로 시세 수집 성공을 뜻하지 않습니다.

시세가 수집되면 유효 OHLC 관측치의 일봉·분봉과 20개 수익률 관측치 기반 역사적 변동성을 추가로 표시합니다. 이 경로는 현재 권한 문제로 실제 응답 검증이 남아 있습니다. 종목 선택은 보존된 마스터를 사용하므로 이후 실행 전 최신 마스터 또는 `--symbol`을 확인해야 합니다. 전체 세션 검증, 거래비용 및 독립 표본 평가 전에는 모델 성능을 보고하지 않습니다.

- [API 구조·인증·운영 한도](docs/nh-api-architecture.md)
- [49종 API와 개별 Excel 원본 색인](docs/api-catalog.md)
- [모델 연구 설계와 가설별 데이터 매핑](docs/research-design.md)
- [기존 Weekly Option 자료 검토](docs/source-audit.md)
- [실제 수행한 검증과 남은 확인 사항](docs/verification.md)

공식 사이트에서 받은 개별 Excel **49개**, 사용자가 제공한 통합 Excel **1개**, 공개 국내 종목 마스터 **3개**를 `vendor/nh/2026-10-11/`에 보존했습니다. 통합본과 개별본의 메타데이터·필드 정의는 일치합니다. 예제 형식의 차이는 `data/catalog/audit.json`에 남깁니다.

지수 마스터의 이름 기반 위클리 후보는 **1,258행 / 고유 종목코드 766개**입니다. 주간·야간 자료의 기준일 불일치 가능성이 있어 현재 거래 가능 계약이나 시세 품질을 확정한 결과로 해석하지 않습니다. 실제 예측 성능은 아직 평가하지 않았습니다.

## 오프라인 재현

Python 3.10 이상을 사용합니다. 전체 테스트와 대시보드에는 `dashboard` 추가 의존성이 필요합니다. 저장소 루트에서 실행합니다.

```sh
python -m pip install -e ".[dashboard]"
python scripts/build_catalog.py
python scripts/analyze_masters.py
python -m unittest discover -s tests -v
nh-research doctor
nh-research plan --api domestic/price --params examples/price_query.json
```

`doctor`는 `NH_APPKEY`·`NH_APPSECRET`의 설정 유무만 표시합니다. `plan`은 환경변수의 키를 사용하지 않고 전송하지 않은 요청의 요약만 만듭니다. `examples/price_query.json`의 코드는 다운로드 당시 마스터에서 확인한 예시이며 재사용 전에 최신 마스터로 교체해야 합니다.

`contracts.py`는 요청 구성기, `client.py`는 모의 인증·읽기 전용 HTTP 전송기입니다. WebSocket은 메시지 구성만 지원하며 실시간 수집은 아직 구현하지 않았습니다. `doctor`와 `plan`은 `.env`를 자동 로드하지 않지만 `collect_demo.py`는 로드합니다.

명시적으로 공개 접근 상태를 다시 검사하려면 다음을 실행합니다. 포털 GET 1건과 인증 헤더 없는 시세 POST 2건만 발생합니다.

```sh
python scripts/probe_public_access.py --output data/analysis/public_access_probe.json
```

최초 무인증 검사에서는 포털 `200`, 실전·모의 시세 주소 `401`이었습니다. 이후 모의 인증은 성공했고 국내 시세는 권한 부족 `403`을 확인했습니다. 역사 조회 범위는 아직 미확인입니다. 원본 문서의 예제나 지시문은 분석 자료로 취급하며 실행하지 않습니다.
