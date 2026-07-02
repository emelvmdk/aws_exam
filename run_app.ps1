#Requires -Version 5.1
# AWS 문제풀이 - 데스크톱 앱(app_gui.py)을 콘솔 창 없이 실행한다.
#
# AWS문제풀이.exe가 Windows 스마트 앱 컨트롤(Smart App Control)에 막힐 때의
# 대안. python.exe/pythonw.exe는 이미 신뢰된 실행 파일이라 막히지 않는다.
# (.pyw 파일 자체를 더블클릭하면 쓰이는 Windows의 pyw.exe 런처가 환경에 따라
# 조용히 실패하는 경우가 있어, pythonw.exe를 직접 찾아서 실행한다.)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Find-Python {
    foreach ($candidate in @("python", "py")) {
        $cmdInfo = Get-Command $candidate -ErrorAction SilentlyContinue
        if (-not $cmdInfo) { continue }
        try {
            $output = & $candidate --version 2>&1
            if ($LASTEXITCODE -eq 0 -and $output -match "^Python \d") {
                return $cmdInfo.Source
            }
        } catch {
            continue
        }
    }
    return $null
}

$pythonPath = Find-Python
if (-not $pythonPath) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Python을 찾을 수 없습니다. https://www.python.org 에서 설치한 뒤(설치 시 " +
        "'Add python.exe to PATH' 체크) 다시 실행해주세요.",
        "AWS 문제풀이",
        "OK",
        "Error"
    ) | Out-Null
    exit 1
}

$pythonwPath = Join-Path (Split-Path $pythonPath -Parent) "pythonw.exe"
$scriptPath = Join-Path $PSScriptRoot "app_gui.pyw"

if (Test-Path $pythonwPath) {
    Start-Process -FilePath $pythonwPath -ArgumentList "`"$scriptPath`""
} else {
    Start-Process -FilePath $pythonPath -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden
}
