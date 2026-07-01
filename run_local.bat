@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===============================================
echo  AWS 문제풀이 - 로컬 실행 스크립트
echo ===============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [오류] python이 설치되어 있지 않거나 PATH에 없습니다.
    echo https://www.python.org 에서 Python을 설치한 뒤 다시 실행해주세요.
    pause
    exit /b 1
)

echo.
echo [1/3] 필요한 패키지 설치 확인 중...
python -m pip install -q -r "%~dp0parser\requirements.txt"

set "PDF_PATH=%~1"
if "%PDF_PATH%"=="" (
    echo.
    echo PDF 파일을 이 창으로 드래그 앤 드롭 한 뒤 Enter를 누르거나,
    echo 경로를 직접 입력하세요.
    set /p PDF_PATH=PDF 파일 경로:
)
set PDF_PATH=%PDF_PATH:"=%

if not exist "%PDF_PATH%" (
    echo [오류] 파일을 찾을 수 없습니다: %PDF_PATH%
    pause
    exit /b 1
)

echo.
echo [2/3] PDF를 문제 데이터로 변환 중...
python "%~dp0parser\parse_pdf.py" "%PDF_PATH%" -o "%~dp0data\questions.json"
if errorlevel 1 (
    echo [오류] 변환에 실패했습니다. parser\parse_pdf.py의 정규식이 이 PDF 포맷과
    echo 맞지 않을 수 있습니다. README.md의 안내를 참고해주세요.
    pause
    exit /b 1
)

echo.
echo [3/3] 로컬 웹 서버 시작 후 브라우저를 엽니다... (이 창은 서버가 켜져 있는 동안 닫지 마세요)
start "" http://localhost:8765/web/index.html
python -m http.server 8765

pause
