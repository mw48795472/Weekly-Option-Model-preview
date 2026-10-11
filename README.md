# Weekly Option Research

**위클리옵션의 만기·포지션 정보가 이후 가격 반전과 변동성에 어떤 정보를 더하는가?** NH선물 REST API 명세와 공개 종목 마스터를 바탕으로 이 질문을 검증하는 연구 프로젝트입니다. 자료 구조·가용성을 분석하고, H1–H9/H9b 검증 설계와 대화형 PoC를 제공합니다.

**[Streamlit 대시보드 열기 · 로컬 실행 필요](http://127.0.0.1:8501/)** · [실행 방법](#streamlit-dashboard) · **[설치 없이 보는 HTML mock 다운로드](https://github.com/mw48795472/Weekly-Option-Model-preview/raw/fcd7aba982e7df532e4ea1c6c63afac44e13e4f4/docs/downloads/weekly_option_poc.zip)** · [Word 통합보고서 다운로드](https://github.com/mw48795472/Weekly-Option-Model-preview/raw/f5b1838bb316f1a093a1558cf5d1cd0dbdafb090/docs/downloads/weekly_option_hypotheses_review.docx)

> **자료 기준: 2026-10-11 KST.** 현재 단계는 공개 마스터 분석·연구 설계·수식 검증입니다. 실측 가격과 OI 이력이 없어 시장 효과·예측 성능·매매 수익은 추정하지 않았습니다. 아래 수치는 보존된 스냅샷의 결과입니다.

| 확보·진단 항목 | 결과 | 읽는 방법 |
|---|---:|---|
| 고유 옵션 계약 / 세션 원장 | **766개 / 1,258행** | 주간·야간 중복을 구분한 상장 후보 |
| 기초자산 × 만기일 후보 | **6개, 날짜는 3개** | 계약 수와 수익률 사건 수는 다름 |
| 완료 사건 / REV 실측 표본 | **0개 / 0개** | 기준시각 이후 만기만 보존됨 |
| REV에 필요한 가격 관측 | **0 / 30개** | 사건당 5개 시점의 가격이 필요 |

[계약 요약 원본](data/analysis/contracts/summary.json) · [REV 실행 명세](data/analysis/reversal/manifest.json) · [가설 진단 JSON](data/analysis/hypotheses/forecast_diagnostics.json)

## 핵심 그래프와 분석

### 1. 계약 수가 많아도 만기 효과를 검증할 사건 수는 늘지 않는다

![만기별 콜·풋 계약 수: 10월 12일 286개, 15일 252개, 19일 228개](docs/images/weekly_expiries.png)

**확인한 결과:** 만기별 계약은 10월 12일 286개, 15일 252개, 19일 228개이며 각 만기의 콜·풋 수는 같습니다. 행사가와 콜풋이 다른 766계약은 **두 기초자산 × 세 만기일의 6개 후보 사건**으로 축약됩니다.

**연구에 주는 의미:** 동일한 기초자산·만기일의 가격 경로를 계약마다 복제해 독립 표본으로 세면 안 됩니다. 만기 효과를 추정하려면 여러 과거 날짜와 비만기 대조일을 확보해야 합니다. 이 그래프는 계약 구성으로, 거래량이나 유동성을 뜻하지 않습니다. [사건 후보 CSV](data/analysis/reversal/event_candidates.csv)

### 2. 주간 마스터만 쓰면 후보의 35.8%가 빠진다

![상품군별 주간·야간 마스터 범위 비교](docs/images/session_coverage.png)

**확인한 결과:** 주간 492개, 야간 766개 중 **야간에만 있는 계약은 274개(전체 766개의 35.8%)**입니다. WKI/WKM은 코스피 위클리, WQI/WQM은 코스닥 위클리 상품군입니다.

**연구에 주는 의미:** 주간 마스터 하나로 분석 대상을 정하면 표본 범위가 달라집니다. 주간·야간의 추정 기준일이 각각 10월 7일·11일이어서 차이의 원인은 확정하지 않았습니다. 이 수치를 야간 거래 증가로 해석할 수 없으며, 시세를 합치기 전에 자료 기준일과 계약 식별자를 맞춰야 합니다. [종목·변수 분석](docs/contract-data.md)

### 3. 가격회귀율 분석의 다음 과제는 정확한 다섯 시점의 가격 확보다

![6개 후보 사건별 REV 가격 확보량: 각각 0/5](docs/images/reversal_feasibility.png)

**확인한 결과:** 각 사건에 필요한 가격은 만기일 마감 30분 전·종가와 다음 거래 세션의 시가·시가+1분·시가+30분입니다. 회색 막대는 **필요량 5개**이며, 실제 확보량은 모든 사건에서 **0/5**입니다.

**연구에 주는 의미:** 현재 실측 REV 표본은 0개입니다. 효과가 0이라는 결론이 아니라, 아직 추정할 자료가 없다는 뜻입니다. 역사 가격·실제 거래일 캘린더·비만기 대조군을 확보하면 구현된 계산 경로에 연결할 수 있습니다. [정의·실행 결과·실측 입력 규칙](docs/price-reversal-analysis.md)

### 4. PoC에서는 가격 반전과 지속이 지표에 어떻게 나타나는지 확인한다

![직접 지정한 가격 경로와 REV 계산 예시 — 시장 관측 아님](docs/images/reversal_formula_examples.png)

`REVh = −sign(Pc / P−30 − 1) × (Ph / Pc − 1) × 10,000` **(bp)**

`P−30`은 마감 30분 전 가격, `Pc`는 종가, `Ph`는 다음 세션의 평가시점 가격입니다. **양수는 만기 직전 움직임의 반전, 음수는 지속**입니다. 예를 들어 가정 가격 `100 → 101 → 100`은 약 +99.01bp이며, `100 → 101 → 102`는 약 −99.01bp입니다. 되돌린 비율(%)을 뜻하는 지표는 아닙니다.

그림은 직접 지정한 가격 경로로 수식을 확인한 예시입니다. Streamlit의 **PoC 실험실 → REV 가격회귀율**에서 다섯 가격을 바꿔볼 수 있습니다. 기준 움직임이 0이면 방향을 정의할 수 없어 결측으로 남깁니다. [수식 예시 CSV](data/analysis/reversal/formula_examples.csv)

다른 마스터 차트: [상품별 계약 구성](docs/images/weekly_products.png) · [행사가 범위](docs/images/strike_coverage.png)

## 가설 심화 검토에서 확인한 사항

현재 자료에서는 **관측 단위·비교군·미래 라벨을 먼저 정리**해야 합니다. 다음은 시장 효과 검정이 아니라, 보존된 자료와 기존 코드의 설계 진단입니다.

| 진단 | 실행 결과 | 분석 설계에 반영할 점 |
|---|---|---|
| 만기 효과 식별 | 설계행렬 rank **1/2** | 비만기 대조가 없어 상수와 만기 더미가 겹침 |
| 상품과 요일 분리 | 설계행렬 rank **4/5** | 현재 표본에서 `monday = WKM + WQM`; 역사자료에서 다시 점검 |
| H9 미래창 정렬 | 원본 식은 **t+4…t+8** | 목표가 다음 5일이면 t+1…t+5로 명시 |
| H9 미완성 라벨 | 마지막 **8개가 0으로 분류** | 미완결 미래 관측은 결측으로 남겨 학습·평가에서 제외 |

H9 진단은 정수 인덱스 마커로 재현했습니다. 수익률·변동성 관측이나 예측 성과가 아닙니다. [진단 결과와 재현 근거](docs/hypotheses-review.md) · [설계행렬 CSV](data/analysis/hypotheses/forecast_design_matrix.csv)

| 연구 축 | 다음에 검증할 질문 | 필요한 자료·조건 |
|---|---|---|
| **H5 만기 · H6 OI — 우선 착수** | HAR 기준보다 미래 실현변동성 예측 손실이 줄어드는가? | 역사 시세·OI 공표시각·완결된 미래 RV·비만기 대조 |
| H1 도입 · H4 국면 | 도입 효과와 사전 국면별 차이를 구분할 수 있는가? | 실제 발표·개시일, 대조군, 당시 이용 가능했던 상태 변수 |
| H2 해외 모델 전이 | 국내 단독 모형보다 전이가 유리한가? | 국내외 정렬 시계열; 해외 피처 추가와 모델 전이의 별도 비교 |
| H3 공급 · H7 집중 · H8 리밸런싱 | 포지션·보유·사건이 원래 가설을 뒷받침하는가? | 외부 보유·포지션·사건자료; NH 집계 수급은 공동 예측 실험으로 처리 |
| H9 RFQ · H9b 유동성 | RFQ의 추가 정보 또는 다음 5분 유동성 스트레스를 예측할 수 있는가? | 원 H9에는 RFQ 로그, H9b에는 시각이 정렬된 호가·잔량 이력 |

**연구 순서:** 자료 정합성과 HAR 기준모형 → H5·H6 추가 예측력 → 수급 정보 → 호가 확보 후 H9b. [통합 검토 보고서](docs/hypotheses-review.md) · [가설별 세부 노트](docs/research/hypotheses/README.md)

<a id="streamlit-dashboard"></a>
## Streamlit 대시보드

### [대시보드 열기 → http://127.0.0.1:8501](http://127.0.0.1:8501/)

**이 링크는 로컬 실행용입니다.** 링크를 여는 사람의 컴퓨터에서 아래 서버가 실행 중이어야 접속됩니다. 공개 인터넷 배포 주소는 아직 없습니다. 설치 없이 열어보려면 위의 **HTML mock ZIP**을 내려받아 압축을 풀고 `weekly_option_poc.html`을 실행하세요.

저장소 루트에서 Python 3.10 이상으로 실행합니다. 보존된 공개자료를 사용하므로 API 키가 필요하지 않습니다.

```sh
python -m pip install -e ".[streamlit]"
python -m streamlit run streamlit_app.py
```

| 화면 | 직접 해볼 수 있는 작업 |
|---|---|
| 연구 개요 | 만기별 구성, 주간·야간 범위와 연구 우선순위 확인 |
| 종목·변수 탐색 | 상품명·종목코드 검색, 만기·콜풋 필터, 선택·개별 CSV 다운로드 |
| 가설 검토 | H1–H9/H9b의 질문, 필수 관측, 상세 검토 읽기 |
| PoC 실험실 | H5 감마·잔존일, H6 OI·미래창, REV 가격, H9b 거래비용 변경 |
| 진단·다운로드 | 설계행렬, Word·CSV ZIP·HTML mock·PNG 저장 |

PoC는 입력 가정과 인덱스 마커에 대한 계산입니다. 각 차트에 해석과 한계를 표시하며, 카메라 아이콘으로 PNG를 저장할 수 있습니다. [실행·화면별 안내](docs/streamlit-dashboard.md)

## 데이터와 보고서

| 자료 | 구성·용도 |
|---|---|
| [전체 종목 CSV ZIP 다운로드](https://github.com/mw48795472/Weekly-Option-Model-preview/raw/fcd7aba982e7df532e4ea1c6c63afac44e13e4f4/docs/downloads/weekly_option_data.zip) | 통합본 + 상품군별 4개 + 계약코드별 766개 파일 |
| [계약 통합본](data/analysis/contracts/weekly_contracts.csv) · [세션 원장](data/analysis/contracts/weekly_contract_sessions.csv) | 상품명·한글 종목명·코드, 766계약 / 1,258세션 행 |
| [변수 사전](data/analysis/contracts/variable_dictionary.csv) · [값별 빈도](data/analysis/contracts/variable_value_counts.csv) | 62항목의 의미·단위·관측 범위·공란·분석 용도 |
| [분석 가용성](data/analysis/contracts/analysis_readiness.csv) · [PoC 가정값](data/analysis/contracts/poc_assumptions.csv) | 확보한 관측과 연구 입력 가정 구분 |
| [통합 보고서](docs/hypotheses-review.md) · [Word 다운로드](https://github.com/mw48795472/Weekly-Option-Model-preview/raw/f5b1838bb316f1a093a1558cf5d1cd0dbdafb090/docs/downloads/weekly_option_hypotheses_review.docx) | H1–H9/H9b 검토, 근거 링크와 후속 연구 설계 |
| [NH API 구조](docs/nh-api-architecture.md) · [49종 API·Excel 색인](docs/api-catalog.md) | 인증·요청 구조·제약과 보존된 공식 명세 |
| [자료 감사](docs/source-audit.md) · [연구 설계](docs/research-design.md) · [검증 기록](docs/verification.md) | 원 기획서 검토와 구현 범위 |

CSV는 UTF-8 BOM이며 미확보 현재가·OI·IV 등 23개 관측/연구 변수는 빈칸입니다. Excel에서 코드 열을 텍스트로 가져오면 앞자리 0을 유지할 수 있습니다. 다운로드 주소는 검증된 커밋에 고정돼 있어 브랜치 삭제 후에도 같은 파일을 가리킵니다.

## 재현과 후속 시세 연결

```sh
python -m pip install -e ".[dashboard,streamlit]"
python scripts/analyze_reversal.py
python scripts/analyze_hypotheses.py
python -m unittest discover -s tests -v
```

로컬 검증과 CI는 분석 경계조건, 자료 보존, Streamlit 다섯 화면을 검사합니다. 전체 산출물 재생성·HTML/Word 빌드·API 수집 절차는 [재현 및 운영 안내](docs/reproduction.md)에 정리했습니다.

보존된 검증 기록에서는 **모의 Access Token 발급 성공**, 국내 시세는 **403 / EGW016**이었습니다. 인증 성공과 시세 권한은 별도이며, 이번 README 정리에서는 권한 상태를 다시 확인하지 않았습니다. 시세 확보 후에도 거래일·가격 시각·계약 연결·비용을 검증한 뒤 성능을 평가합니다. 키·토큰·원본 시세 응답은 저장소에 포함하지 않습니다.
