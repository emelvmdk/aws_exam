@echo off
rem Thin launcher: all real logic lives in run_local.ps1 (PowerShell handles
rem Korean/UTF-8 text reliably; plain .bat parsing of non-ASCII text is
rem fragile and can silently corrupt the script on some systems).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_local.ps1" %*
