# Streamlit Community Cloud 배포

**공개 주소: [weekly-option-model-preview.streamlit.app](https://weekly-option-model-preview.streamlit.app/)**

2026-10-11 KST에 Community Cloud 앱 실행과 공개 공유 설정을 확인했습니다. 로그인 쿠키를 전달하지 않은 별도 HTTP 클라이언트에서 루트 페이지와 앱 상태 주소가 모두 200으로 응답했고 상태 값은 `ok`였습니다. 로컬 실행 주소는 개발용으로만 유지합니다.

| 설정 | 값 |
|---|---|
| Repository | `mw48795472/Weekly-Option-Model-preview` |
| Branch | `codex/streamlit-public-deployment` |
| Main file path | `streamlit_app.py` |
| Python | `3.12` |
| Dependency file | `requirements.txt` |
| Secrets | 비워 둠 — 공개 연구 앱은 API 키를 사용하지 않음 |
| Sharing | Anyone / public |

현재 공개 앱은 위 배포 브랜치를 따라갑니다. PR 병합만으로 Cloud의 대상 브랜치가 바뀌지는 않습니다. `main`으로 전환할 때는 Cloud의 저장소 설정을 함께 변경한 후 공개 앱을 다시 확인합니다. 전환 전에는 배포 브랜치를 삭제하지 않습니다. 변경한 파일을 배포 브랜치에 push하면 Cloud가 다시 실행합니다.

## 배포 순서

1. [Streamlit Community Cloud](https://share.streamlit.io/)에서 로그인하고 저장소를 선택합니다.
2. Create app에서 위 저장소·배포 브랜치·`streamlit_app.py`를 지정합니다.
3. Advanced settings의 Python을 3.12로 정하고 Secrets는 비워 둡니다.
4. Deploy 후 앱이 열리면 공유 범위가 public인지 확인합니다.
5. 인증하지 않은 접속에서도 연구 개요·종목 검색·PoC·다운로드가 동작하는지 확인한 후 실제 URL로 README 링크를 바꿉니다.

Community Cloud는 저장소의 `requirements.txt`를 우선해 런타임을 설치합니다. 이 파일은 검증한 Streamlit·NumPy·pandas·Plotly 버전을 고정합니다. `pyproject.toml`은 로컬 패키지와 추가 연구 도구 설치용으로 유지합니다. Linux/Python 3.12 CI도 같은 `requirements.txt`를 설치해 화면 테스트를 실행합니다.

앱은 저장소에 포함된 공개 CSV·JSON·Markdown·Word·HTML·PNG만 읽습니다. `.env`, 비공개 시세 폴더, 주문·계좌 API를 연결하지 않습니다. `.streamlit/secrets.toml`도 Git에서 제외합니다. `.streamlit/config.toml`은 호스트 주소를 고정하지 않으며 로컬 실행은 다음처럼 제한합니다.

```sh
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.address 127.0.0.1
```

배포 시 오류가 나면 Cloud 관리 로그에서 패키지 설치와 Python 버전, 지정한 브랜치·진입 파일을 확인합니다. 파일 갱신 후 캐시가 남으면 앱을 재시작합니다.

공식 안내: [의존성 설치](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) · [배포와 Python 설정](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
