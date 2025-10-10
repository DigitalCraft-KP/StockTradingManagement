# 📈 주식 매매 관리 시스템(STMS)


## 🛠️ 설치 및 실행 방법

### 설치 준비

  * **Python 설치**: PC에 Python 3 버전이 설치되어 있어야 합니다.
  * **필요 라이브러리 설치**: 터미널(명령 프롬프트)을 열고 아래 명령어를 실행하여 `yfinance` 라이브러리를 설치합니다.
    ```bash
    pip install yfinance
    ```
  * **프로그램 파일 준비**: `index.html`과 `STMS.py` 파일을 동일한 폴더에 위치시킵니다.

### 웹 서버 실행

  * 터미널에서 파일이 있는 폴더로 이동한 후, 아래 명령어를 입력하여 서버를 실행하거나, run_STMS.bat 파일을 클릭하여 실행합니다.
    ```bash
    python STMS.py
    ```
  * 서버가 정상적으로 실행되면 자동으로 기본 웹 브라우저에서 프로그램(`http://localhost:8000`)이 열립니다.

### 폴더 구조

실행 후 다음과 같은 폴더 및 파일 구조가 생성될 수 있습니다:

```
프로그램 폴더/
├── README.md          # 사용자 설명서
├── run_STMS.bat       # 메인 서버 프로그램을 실행하기 위한 배치 프로그램
├── STMS.py            # 메인 서버 프로그램
├── index.html         # 웹 인터페이스
└── stock_data/        # 기본 데이터 저장 폴더
    └── stock_data_YYYYMMDD_HHMMSS.json
```
