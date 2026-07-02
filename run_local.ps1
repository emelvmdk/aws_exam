#Requires -Version 5.1
# AWS 문제풀이 - 로컬 실행 스크립트 (Windows / PowerShell)
# run_local.bat 이 이 스크립트를 호출합니다. 직접 실행해도 됩니다:
#   powershell -ExecutionPolicy Bypass -File run_local.ps1 [PDF경로]

param(
    [string]$PdfPath
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location -Path $PSScriptRoot

Write-Host "==============================================="
Write-Host " AWS 문제풀이 - 로컬 실행 스크립트"
Write-Host "==============================================="

function Find-Python {
    foreach ($candidate in @(
        @{ Cmd = "python"; Args = @() },
        @{ Cmd = "py"; Args = @("-3") },
        @{ Cmd = "python3"; Args = @() }
    )) {
        $cmdInfo = Get-Command $candidate.Cmd -ErrorAction SilentlyContinue
        if (-not $cmdInfo) { continue }
        try {
            $output = & $candidate.Cmd @($candidate.Args) --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $output -match "^Python \d") {
                return $candidate
            }
        } catch {
            continue
        }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host ""
    Write-Host "[오류] Python을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "https://www.python.org 에서 Python을 설치한 뒤(설치 시 'Add python.exe to PATH' 체크) 다시 실행해주세요."
    Write-Host "(Windows에서 python 명령이 Microsoft Store를 열기만 한다면, 설정 > 앱 실행 별칭에서 python/python3 별칭을 꺼주세요.)"
    Read-Host "계속하려면 Enter를 누르세요"
    exit 1
}

Write-Host ""
Write-Host "[1/3] 필요한 패키지 설치 확인 중..."
& $python.Cmd @($python.Args) -m pip install -q -r (Join-Path $PSScriptRoot "parser\requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[오류] 패키지 설치에 실패했습니다." -ForegroundColor Red
    Read-Host "계속하려면 Enter를 누르세요"
    exit 1
}

if (-not $PdfPath) {
    Write-Host ""
    Write-Host "PDF 파일을 이 창으로 드래그 앤 드롭 한 뒤 Enter를 누르거나, 경로를 직접 입력하세요."
    $PdfPath = Read-Host "PDF 파일 경로"
}
$PdfPath = $PdfPath.Trim('"')

if (-not (Test-Path -LiteralPath $PdfPath)) {
    Write-Host "[오류] 파일을 찾을 수 없습니다: $PdfPath" -ForegroundColor Red
    Read-Host "계속하려면 Enter를 누르세요"
    exit 1
}

Write-Host ""
Write-Host "[2/3] PDF를 문제 데이터로 변환 중..."
& $python.Cmd @($python.Args) (Join-Path $PSScriptRoot "parser\parse_pdf.py") $PdfPath -o (Join-Path $PSScriptRoot "data\questions.json")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[오류] 변환에 실패했습니다. parser\parse_pdf.py의 정규식이 이 PDF 포맷과 맞지 않을 수 있습니다. README.md의 안내를 참고해주세요." -ForegroundColor Red
    Read-Host "계속하려면 Enter를 누르세요"
    exit 1
}

Write-Host ""
Write-Host "[3/3] 로컬 웹 서버 시작 후 브라우저를 엽니다... (이 창은 서버가 켜져 있는 동안 닫지 마세요)"
Start-Process "http://localhost:8765/web/index.html"
& $python.Cmd @($python.Args) -m http.server 8765
