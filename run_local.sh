#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==============================================="
echo " AWS 문제풀이 - 로컬 실행 스크립트"
echo "==============================================="

if ! command -v python3 >/dev/null 2>&1; then
  echo "[오류] python3이 설치되어 있지 않습니다. https://www.python.org 에서 설치해주세요."
  exit 1
fi

echo
echo "[1/3] 필요한 패키지 설치 확인 중..."
python3 -m pip install -q -r parser/requirements.txt

PDF_PATH="$1"
if [ -z "$PDF_PATH" ]; then
  read -rp "PDF 파일 경로: " PDF_PATH
fi

if [ ! -f "$PDF_PATH" ]; then
  echo "[오류] 파일을 찾을 수 없습니다: $PDF_PATH"
  exit 1
fi

echo
echo "[2/3] PDF를 문제 데이터로 변환 중..."
python3 parser/parse_pdf.py "$PDF_PATH" -o data/questions.json

echo
echo "[3/3] 로컬 웹 서버 시작 (종료하려면 Ctrl+C)"
( sleep 1 && (open "http://localhost:8765/web/index.html" 2>/dev/null || xdg-open "http://localhost:8765/web/index.html" 2>/dev/null || true) ) &
python3 -m http.server 8765
