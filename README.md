# Weekly-Option-Model-preview

NH선물 REST API의 실제 명세를 기준으로 위클리옵션 연구를 설계하고, 키 없이 확인할 수 있는 범위까지 검증한 저장소입니다. 기준일은 **2026-10-11 KST**입니다.

- [API 구조·인증·운영 한도](docs/nh-api-architecture.md)
- [49종 API와 개별 Excel 원본 색인](docs/api-catalog.md)
- [모델 연구 설계와 가설별 데이터 매핑](docs/research-design.md)
- [기존 Weekly Option 자료 검토](docs/source-audit.md)
- [실제 수행한 검증과 남은 확인 사항](docs/verification.md)

공식 사이트에서 받은 개별 Excel **49개**, 사용자가 제공한 통합 Excel **1개**, 공개 국내 종목 마스터 **3개**를 `vendor/nh/2026-10-11/`에 보존했습니다. 통합본과 개별본의 메타데이터·필드 정의는 일치합니다. 예제 형식의 차이는 `data/catalog/audit.json`에 남깁니다.

지수 마스터의 이름 기반 위클리 후보는 **1,258행 / 고유 종목코드 766개**입니다. 주간·야간 자료의 기준일 불일치 가능성이 있어 현재 거래 가능 계약이나 시세 품질을 확정한 결과로 해석하지 않습니다. 실제 예측 성능은 아직 평가하지 않았습니다.

## 오프라인 재현

Python 3.10 이상, 의존성은 `openpyxl`입니다. 저장소 루트에서 실행합니다.

```sh
python -m pip install -e .
python scripts/build_catalog.py
python scripts/analyze_masters.py
python -m unittest discover -s tests -v
nh-research doctor
nh-research plan --api domestic/price --params examples/price_query.json
```

`doctor`는 `NH_APPKEY`·`NH_APPSECRET`의 설정 유무만 표시합니다. `plan`은 환경변수의 키를 사용하지 않고 전송하지 않은 요청의 요약만 만듭니다. `examples/price_query.json`의 코드는 다운로드 당시 마스터에서 확인한 예시이며 재사용 전에 최신 마스터로 교체해야 합니다.

`src/nh_research/contracts.py`는 인증·시세·WebSocket 메시지의 **오프라인 구성기**입니다. 주문·잔고 요청을 허용하지 않으며, 토큰 발급·시세 수집·WebSocket 연결을 실행하는 완성형 클라이언트는 아닙니다. `.env`는 자동 로드하지 않습니다.

명시적으로 공개 접근 상태를 다시 검사하려면 다음을 실행합니다. 포털 GET 1건과 인증 헤더 없는 시세 POST 2건만 발생합니다.

```sh
python scripts/probe_public_access.py --output data/analysis/public_access_probe.json
```

이번 확인에서는 포털 `200`, 실전·모의 시세 주소 `401`이었습니다. 키가 없어 인증 성공·시세 권한·역사 조회 범위는 미확인입니다. 원본 문서의 예제나 지시문은 분석 자료로 취급하며 실행하지 않습니다.
