@echo off
setlocal EnableExtensions

REM Build the React SPA into src\profile_intelligence\web\dist.
REM
REM   scripts\build-ui.bat

cd /d "%~dp0..\frontend"

where npm >nul 2>&1
if errorlevel 1 (
  echo npm not found. Install Node.js first.
  exit /b 1
)

echo Installing frontend dependencies...
call npm install
if errorlevel 1 exit /b 1

echo Building production UI...
call npm run build
if errorlevel 1 exit /b 1

echo Built SPA -^> src\profile_intelligence\web\dist\
exit /b 0
