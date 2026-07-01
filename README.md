# AWS 자격증 문제풀이 프로그램

PDF 덤프 파일을 문제 데이터(JSON)로 변환하고, 문제 순서와 보기 순서를 매번
랜덤으로 섞어서 풀 수 있는 웹 기반 연습 프로그램입니다. **PDF 파일만 바꾸면
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

## 1. PDF를 문제 데이터로 변환하기

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
1. 상단에서 `data/questions.json`(또는 다른 시험용 JSON 파일)을 선택합니다.
2. 풀고 싶은 문제 수, 보기 순서 랜덤 여부를 설정합니다.
3. "시작하기"를 누르면 문제 순서와 보기 순서가 매번 새로 섞여서 출제됩니다.
4. 각 문제 제출 시 정답 여부를 바로 확인하고, 마지막에 전체 점수와 오답
   리뷰를 볼 수 있습니다.
5. "다시 풀기"를 누르면 같은 문제 세트를 다시 랜덤으로 섞어서 풀 수 있습니다.

## 다른 시험 준비 시 재사용하는 법

1. 새 시험의 PDF 덤프로 `python parse_pdf.py 새파일.pdf -o ../data/새시험.json` 실행
2. 웹 앱에서 파일 선택창으로 `새시험.json`을 선택하면 끝. 코드 수정 불필요.
