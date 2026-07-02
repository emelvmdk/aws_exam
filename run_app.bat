@echo off
rem AWS문제풀이.exe가 Windows 스마트 앱 컨트롤에 막힐 때 쓰는 대안 실행기.
rem 콘솔 창 없이 GUI 앱만 뜬다.
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0run_app.ps1"
