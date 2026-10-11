# Streamlit 위클리옵션 연구 대시보드

저장된 공개 마스터와 가설 진단을 탐색하고 가정 기반 PoC를 실행하는 연구 대시보드입니다. **[공개 대시보드 열기](https://weekly-option-model-preview.streamlit.app/)**에서 로그인이나 설치 없이 사용할 수 있습니다. NH API를 호출하거나 `.env`·키·토큰·계좌자료를 읽지 않습니다. 기준일 이후의 실시간 자료로 오인하지 않도록 2026-10-11 스냅샷을 화면에 표시합니다.

## 로컬 실행

저장소 루트에서 Python 3.10 이상으로 실행합니다.

```sh
python -m pip install -e ".[streamlit]"
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

브라우저에서 `http://127.0.0.1:8501`을 엽니다. 이미 포트를 사용하는 앱이 있으면 `--server.port 8502`를 붙입니다. 위 명령은 로컬 컴퓨터에만 바인딩합니다. 사용 통계 전송과 정적 파일 제공은 꺼져 있습니다. HTML mock과 달리 Streamlit은 Python 서버가 실행 중이어야 합니다. 클라우드에서는 호스팅 환경의 바인딩 설정을 사용합니다. [공개 배포 설정](streamlit-deployment.md)

## 다섯 화면

| 화면 | 가능한 작업 | 해석 범위 |
|---|---|---|
| 연구 개요 | 만기별 구성, 주간·야간 범위, 연구 우선순위 | 계약 수는 거래량이나 독립 사건 수가 아님 |
| 종목·변수 탐색 | 상품명·종목명·코드 검색, 콜풋·만기 필터, 선택·개별 CSV, 변수 사전 | 공란은 0으로 채우지 않음 |
| 가설 검토 | H1–H9/H9b의 질문·추정 대상·필수 관측과 전체 검토 | 원인 가설과 NH 대체 예측 실험 구분 |
| PoC 실험실 | H5 감마, H6 OI·미래창, REV, H9b 비용 입력 실험 | 가정·정수 마커를 사용하며 시장 성과가 아님 |
| 진단·다운로드 | rank·H9 인덱스 진단, Word·Markdown·CSV·HTML mock·PNG | 보존된 기준일의 실행 결과 |

H5는 유럽형 Black–Scholes, r=q=0, 달력일/365 가정입니다. H6는 전기 OI가 0이면 변화율을 정의하지 않고 미완결 미래창을 결측으로 표시합니다. REV는 기존 `rev_bp`를 사용하며 기준 움직임이 0이면 결측입니다. H9b 비용 시연은 동일 기준가격 bp의 1차 근사이며 양 시점의 전체 스프레드가 같다는 가정을 사용합니다. 실제 스트레스 예측모형이나 체결 검증은 아닙니다.

다운로드 버튼은 저장소의 공개 배포 파일과 선택한 공개자료만 제공합니다. Plotly 그래프 오른쪽 위 카메라 버튼으로 PNG를 저장할 수 있습니다. 저장자료에 없는 현재가·OI·IV의 임의 생성, 학습 성능·p값·매매 손익 추정 기능은 포함하지 않습니다.

## 검증과 유지

```sh
python -m pip install -e ".[dashboard,streamlit]"
python -m unittest discover -s tests -v
```

Streamlit [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest)로 다섯 화면, 종목 검색의 빈 결과, 모든 가설, PoC 입력 경계를 확인합니다. [다운로드 버튼](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button)은 세션에 파일 바이트를 제공합니다. 테스트 외에 실제 브라우저에서 페이지와 차트를 확인합니다. 캐시된 파일을 교체했다면 서버를 재시작해 새 스냅샷을 읽습니다.

배포 Word의 내용은 [통합 보고서](hypotheses-review.md)와 같고, 가설 화면은 해당 Markdown 절을 읽어 표시합니다. 근거 링크는 검토한 커밋으로 고정돼 있으며 자료를 갱신할 때는 보고서·진단과 함께 기준일 및 링크도 검토해야 합니다.
