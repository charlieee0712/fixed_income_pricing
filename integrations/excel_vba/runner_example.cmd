@echo off
REM ===========================================================================
REM Example pricing runner for the Excel bridge (v1, 2026-08-25).
REM
REM Copy this file somewhere stable (e.g. C:\RYSE\bin\ryse-fip.cmd), edit the two
REM paths below, then point the workbook's FIP_RunnerCommand cell at it:
REM
REM     FIP_RunnerCommand = C:\RYSE\bin\ryse-fip.cmd
REM
REM The bridge appends --input <file> --output <file>; %* passes them through.
REM Replacing this file with a packaged executable or an HTTP client wrapper is
REM the ONLY change needed when the engine moves off a local Python install —
REM the workbook and the JSON field meanings stay exactly as they are.
REM ===========================================================================

set REPO=C:\path\to\fixed_income_pricing
set PYTHON=C:\path\to\python.exe

cd /d "%REPO%" || exit /b 2
set PYTHONPATH=src
"%PYTHON%" scripts\price_json.py %*
