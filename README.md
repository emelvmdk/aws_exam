# AWS 자격증 문제풀이 프로그램

PDF 덤프 파일을 문제 데이터(JSON)로 변환하고, 보기 순서를 랜덤으로 섞어서
(원하면 문제 순서도) 풀 수 있는 웹 기반 연습 프로그램입니다. **PDF 파일만 바꾸면
SAP, SAA, DVA 등 다른 시험 준비에도 그대로 재사용**할 수 있도록
`parser`(PDF → JSON 변환)와 `web`(퀴즈 앱)을 분리해두었습니다.

## 구조

```
parser/           PDF 덤프를 JSON으로 변환하는 스크립트
  parse_pdf.py
  requirements.txt
data/
  questions.sample.json   동작 확인용 샘플 문제 (실제 덤프 없이도 테스트 가능)
  questions.json          parse_pdf.py 실행 후 생성되는 실제 문제 데이터 (git에는 포함하지 않는 것을 권장)
web/              브라우저에서 바로 여는 문제풀이 앱
  index.html
  app.js
  style.css
```

## 빠른 시작 (Windows, 추천): 데스크톱 앱

`AWS문제풀이.exe`를 더블클릭하면 됩니다. Python 설치가 필요 없습니다.

- **최근 시험 목록**에서 예전에 변환해 둔 시험을 골라 "▶ 시작하기"만 누르면
  바로 브라우저로 문제풀이가 열립니다. (PDF를 매번 다시 선택할 필요 없음)
- **PDF 추가** 버튼으로 새 시험 덤프 PDF를 등록하면 자동으로 변환되어
  목록에 추가됩니다. 여러 시험(SAP, SAA, DVA 등)을 동시에 등록해두고
  목록에서 골라 전환할 수 있습니다.
- **다시 변환**: 원본 PDF 내용이 바뀌었을 때 같은 이름으로 다시 변환합니다.
- **이름 변경 / 삭제**로 목록을 정리할 수 있습니다.
- exe 파일은 반드시 `web/`, `parser/`, `data/` 폴더와 같은 위치(이 저장소
  루트)에 있어야 합니다. exe만 따로 복사해서 옮기면 동작하지 않습니다.

exe가 없다면 아래 "데스크톱 앱 직접 빌드하기"를 참고해 만들 수 있습니다.

**exe가 실행이 안 되고 "Application Control policy가 이 파일을 차단했습니다"
같은 오류가 뜬다면**, Windows 스마트 앱 컨트롤(Smart App Control)이 새로
빌드된(서명되지 않은) 실행 파일을 막은 것입니다. 이 설정은 시스템 전체에
적용되고 한번 끄면 되돌리기 어려워서(재설치 필요) 끄는 것을 권장하지
않습니다. 대신 `run_app.bat`을 더블클릭하세요 - Python이 설치되어 있으면
(이미 신뢰된 실행 파일인 `pythonw.exe`로) 콘솔 창 없이 똑같은 앱 화면이
뜹니다.

### 데스크톱 앱 직접 빌드하기

```bash
pip install pyinstaller
pip install -r parser/requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --name "AWS문제풀이" \
  --collect-all pdfplumber --collect-all pdfminer --collect-all pypdfium2 app_gui.py
```

`dist/AWS문제풀이.exe`가 생성되면 저장소 루트로 옮겨서 사용하세요.

## 스크립트로 실행하기 (앱 없이, 또는 Mac/Linux)

PDF 덤프는 **본인 PC에서 딱 한 번만 변환**하면 됩니다. 이후에는 변환된
JSON 파일만 계속 재사용하면 되고, 매번 PDF를 다시 올리거나 변환할 필요가
없습니다. (참고: 이 저장소는 PDF 원본과 변환된 실제 문제 JSON을 git에
커밋하지 않도록 `.gitignore`에 등록되어 있습니다. 개인 시험 덤프 자료를
공개 저장소에 올리지 않기 위함입니다.)

1. 이 저장소를 PC에 클론(또는 다운로드)합니다.
2. Windows는 `run_local.bat`(내부적으로 `run_local.ps1` 호출), Mac/Linux는
   `run_local.sh`를 실행합니다.
   - PDF 파일을 스크립트 위로 드래그 앤 드롭하거나, 실행 후 경로를 입력하면 됩니다.
   - 스크립트가 자동으로 `data/questions.json`을 생성하고, 로컬 웹 서버를 띄운 뒤
     브라우저로 문제풀이 화면을 엽니다.
3. 그 다음부터는 스크립트를 다시 실행할 필요 없이 `web/index.html`을
   (로컬 서버로) 열기만 하면 이전에 변환된 `data/questions.json`을 자동으로
   불러옵니다. 다른 시험 PDF로 바꾸고 싶을 때만 스크립트를 다시 실행하세요.

## 1. PDF를 문제 데이터로 변환하기 (수동으로 직접 하고 싶을 때)

```bash
cd parser
pip install -r requirements.txt
python parse_pdf.py /path/to/your-dump.pdf -o ../data/questions.json
```

`parse_pdf.py`는 다음과 같은 흔한 덤프 PDF 포맷을 인식합니다.

```
QUESTION 1
문제 내용이 여러 줄에
걸쳐 있을 수 있습니다.

A. 보기 1
B. 보기 2
C. 보기 3
D. 보기 4

Correct Answer: B
```

- `QUESTION 12`, `NEW QUESTION 12` 둘 다 인식
- 보기가 여러 줄로 이어져도 인식
- 정답이 여러 개인 경우도 지원: `Correct Answer: B D`, `Correct Answer: BD`, `Answer: B, D` 등

만약 갖고 계신 PDF의 포맷이 다르다면(예: 문제 번호 표기, 보기 기호,
"Correct Answer" 문구가 다름), `parser/parse_pdf.py` 상단의
`QUESTION_RE`, `OPTION_RE`, `ANSWER_RE` 정규식만 PDF 포맷에 맞게 수정하면
됩니다. 나머지 로직과 웹 앱은 그대로 사용할 수 있습니다.

실행 후 몇 개 문제가 인식되지 않았다고 나오면(스킵된 문제 번호가 출력됩니다),
해당 문제만 `data/questions.json`을 열어 수동으로 추가/수정하면 됩니다.

### 영문 원본 PDF도 함께 쓰기 (실전 모드의 "View in English")

같은 시험의 한글판과 영문판 PDF를 둘 다 가지고 있다면, `--en-pdf` 옵션으로
함께 변환할 수 있습니다. 문제 번호(예: `QUESTION 12`)가 같은 문제끼리
자동으로 매칭됩니다.

```bash
python parse_pdf.py 한글덤프.pdf --en-pdf 영문덤프.pdf -o ../data/questions.json
```

이렇게 만든 JSON은 웹앱 실전 모드에서 "🌐 View in English" 버튼을 누르면
영문 원본을 팝업으로 보여줍니다. 데스크톱 앱(`AWS문제풀이.exe`)의 "PDF
추가"에서도 영문 PDF를 함께 등록할 수 있습니다.

### 문제 데이터(JSON) 형식

다른 방식(수동 정리 등)으로 문제를 준비하고 싶다면 아래 형식만 맞추면
`parser` 없이 바로 웹 앱에서 사용할 수 있습니다.

```json
[
  {
    "id": 1,
    "question": "문제 내용",
    "options": ["보기 1", "보기 2", "보기 3", "보기 4"],
    "correct": [1]
  }
]
```

- `correct`는 정답인 보기의 인덱스(0부터 시작) 배열입니다. 정답이 여러 개면
  `[0, 2]`처럼 여러 인덱스를 넣으면 되고, 앱이 자동으로 체크박스형 문제로
  표시합니다.

## 2. 문제풀이 앱 실행하기

`web/index.html`을 브라우저로 열면 바로 시작할 수 있습니다.

```bash
cd web
python3 -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

(`file://`로 직접 열어도 대부분 동작하지만, 브라우저 정책상 기본 샘플 JSON
자동 로드가 안 될 수 있습니다. 이 경우 화면의 파일 선택창으로
`data/questions.json`을 직접 선택하면 됩니다.)

앱 사용법:
1. `data/questions.json`이 자동으로 로드됩니다. (다른 JSON 파일을 쓰고 싶으면
   화면 아래 "고급: 다른 문제 파일 사용"을 펼쳐서 선택하세요.)
2. 풀고 싶은 문제 수와 순서 섞기 옵션을 설정합니다. 기본값은 **문제는 파일에
   있는 순서 그대로, 보기만 랜덤으로 섞기**입니다. "문제 순서 랜덤으로 섞기"를
   체크하면 문제 순서도 매번 새로 섞입니다.
3. "시작하기"를 누르면 설정한 옵션대로 출제됩니다.
4. 각 문제 제출 시 정답 여부를 바로 확인하고, 마지막에 전체 점수와 오답
   리뷰를 볼 수 있습니다.
5. "다시 풀기"를 누르면 같은 문제 세트를 설정한 옵션대로 다시 풀 수 있습니다.

## 다른 시험 준비 시 재사용하는 법

1. 새 시험의 PDF 덤프로 `python parse_pdf.py 새파일.pdf -o ../data/새시험.json` 실행
2. 웹 앱에서 파일 선택창으로 `새시험.json`을 선택하면 끝. 코드 수정 불필요.
