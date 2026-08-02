@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Start Profile Intelligence Platform — backend (FastAPI) + frontend (Vite).
REM
REM   scripts\start.bat
REM
REM Backend:  http://127.0.0.1:8000
REM Frontend: http://localhost:5173
REM Swagger:  http://127.0.0.1:8000/api/docs

cd /d "%~dp0.."
set "ROOT=%CD%"

if "%PIP_HOST%"=="" set "PIP_HOST=127.0.0.1"
if "%PIP_PORT%"=="" set "PIP_PORT=8000"
if "%PIP_FRONTEND_HOST%"=="" set "PIP_FRONTEND_HOST=localhost"
if "%PIP_FRONTEND_PORT%"=="" set "PIP_FRONTEND_PORT=5173"
if "%PIP_OPEN_BROWSER%"=="" set "PIP_OPEN_BROWSER=1"

set "BACKEND_URL=http://%PIP_HOST%:%PIP_PORT%"
set "FRONTEND_URL=http://%PIP_FRONTEND_HOST%:%PIP_FRONTEND_PORT%"

echo Profile Intelligence Platform — starting...

if exist "%ROOT%\.venv\Scripts\activate.bat" (
  call "%ROOT%\.venv\Scripts\activate.bat"
)

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found. Install Python 3.12+ first.
  exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 (
  echo Python 3.12+ required.
  exit /b 1
)

python -c "import profile_intelligence, fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
  echo Installing Python package ^(editable + dev^)...
  python -m pip install -U pip
  python -m pip install -e ".[dev]"
)

set "PYTHONPATH=%ROOT%\src;%PYTHONPATH%"

echo Starting backend on %BACKEND_URL% ...
start "PIP-Backend" /b cmd /c "uvicorn profile_intelligence.api.main:app --host %PIP_HOST% --port %PIP_PORT% --reload"

echo Waiting for backend health...
set /a ATTEMPTS=0
:wait_backend
set /a ATTEMPTS+=1
curl -fsS "%BACKEND_URL%/api/health" >nul 2>&1
if not errorlevel 1 goto backend_ready
if %ATTEMPTS% GEQ 60 (
  echo Backend did not become healthy in time.
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_backend

:backend_ready
echo Backend ready.

set "HAS_FRONTEND=0"
if exist "%ROOT%\frontend\package.json" (
  where npm >nul 2>&1
  if not errorlevel 1 (
    if not exist "%ROOT%\frontend\node_modules\" (
      echo Installing frontend dependencies...
      pushd "%ROOT%\frontend"
      call npm install
      popd
    )
    echo Starting frontend on %FRONTEND_URL% ...
    start "PIP-Frontend" /b cmd /c "cd /d \"%ROOT%\frontend\" && npm run dev -- --host %PIP_FRONTEND_HOST% --port %PIP_FRONTEND_PORT%"
    set "HAS_FRONTEND=1"
  ) else (
    echo npm not found; skipping React dev server.
  )
)

echo.
echo Backend:  %BACKEND_URL%/
echo API docs: %BACKEND_URL%/api/docs
if "%HAS_FRONTEND%"=="1" echo Frontend: %FRONTEND_URL%/
echo Press Ctrl+C in this window after stopping child consoles, or close the PIP-* windows.
echo.

set "OPEN_URL=%FRONTEND_URL%"
if "%HAS_FRONTEND%"=="0" set "OPEN_URL=%BACKEND_URL%/"

if not "%PIP_OPEN_BROWSER%"=="0" (
  start "" "%OPEN_URL%"
)

REM Keep the launcher alive so Ctrl+C is meaningful.
:idle
timeout /t 3600 /nobreak >nul
goto idle
