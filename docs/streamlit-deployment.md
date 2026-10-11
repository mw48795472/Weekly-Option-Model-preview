# Streamlit Community Cloud 배포

공개 저장소의 연구 대시보드를 배포하는 설정입니다. 아직 배포가 완료되지 않았다면 README의 로컬 주소는 공개 주소를 대신하지 않습니다. 실제 공개 주소는 앱 실행을 확인한 뒤 README에 기록합니다.

| 설정 | 값 |
|---|---|
| Repository | `mw48795472/Weekly-Option-Model-preview` |
| Main file path | `streamlit_app.py` |
| Python | `3.12` |
| Dependency file | `requirements.txt` |
| Secrets | 비워 둠 — 공개 연구 앱은 API 키를 사용하지 않음 |
| Sharing | Anyone / public |

배포 브랜치는 Cloud 화면에서 확인합니다. 검토 브랜치로 최초 배포한 경우 유지하고, 운영 브랜치를 변경할 때는 Cloud의 실제 설정과 문서를 함께 갱신합니다. 변경한 파일을 해당 브랜치에 push하면 Cloud가 다시 실행합니다.

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
