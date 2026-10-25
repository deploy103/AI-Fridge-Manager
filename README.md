# AI-Fridge-Manager

냉장 보관 여부를 AI로 판단하고, 현재 재료 기준으로 메뉴를 추천해 주는 프로젝트입니다.  
GUI와 CLI가 같은 로직을 사용합니다.

## 의존성

외부 라이브러리는 최소로 유지했습니다.

- `openai`만 설치하면 됩니다.
- `tkinter`는 Windows 기본 Python에 포함되어 있어서 따로 설치하지 않습니다.

## 실행 전에 먼저 할 것

PowerShell 기준입니다.

1. 가상환경 생성(선택)

```powershell
python -m venv .venv
```

2. 가상환경 활성화(선택)

```powershell
.venv\Scripts\Activate.ps1
```

3. 라이브러리 설치

```powershell
pip install -r requirements.txt
```

4. 환경 파일 만들기

```powershell
Copy-Item .env.example .env
```

5. `.env` 파일 수정

```env
OPENAI_API_KEY=sk-your-api-key
OPENAI_MODEL=gpt-5.4
```

## GUI 실행 방법

아래 명령을 실행하기 전에 반드시 위의 `실행 전에 먼저 할 것` 단계를 끝내세요.

```powershell
python gui.py
```

## CLI 실행 방법

아래 명령을 실행하기 전에 반드시 위의 `실행 전에 먼저 할 것` 단계를 끝내세요.

```powershell
python cli.py
```

## 환경 파일 위치

프로그램은 아래 순서로 설정 파일을 찾습니다.

1. `FRIDGE_ENV_FILE` 환경 변수로 지정한 파일
2. 프로젝트 루트의 `fridge.env`
3. 프로젝트 루트의 `.env`
4. 프로젝트 루트의 `.env\.env`

## 현재 기능

- 식품 이름을 입력하면 냉장 보관 필요 여부를 판단합니다.
- 식품별 유통기한을 입력하고, 기한 지남/임박/미설정 상태를 한눈에 확인합니다.
- 냉장고 목록에 들어간 재료를 기준으로 메뉴를 추천합니다.
- 냉장고 목록은 `fridge_inventory.json`에 자동 저장되어 다음 실행 때 다시 불러옵니다.
- 식품명, 보관 사유, 유통기한으로 목록을 검색할 수 있습니다.
- 선택한 식품 삭제와 전체 비우기를 GUI에서 바로 처리할 수 있습니다.
- GUI와 CLI 모두 최근 판정 결과, 현재 목록, 추천 결과를 확인할 수 있습니다.
- 한글 식품명을 기준으로 사용할 수 있습니다.
