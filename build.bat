@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

chcp 65001 >nul 2>nul

echo === RouteManager Build ===

rem 1) activate venv if exists
if exist "venv\Scripts\activate.bat" (
  echo [info] venv detected, activating...
  call "venv\Scripts\activate.bat"
) else (
  echo [info] no venv, using system Python...
)

rem 2) install deps
echo [step] installing dependencies...
python -m pip install -U pip || goto :fail
python -m pip install -r requirements.txt || goto :fail

rem 3) clean
echo [step] cleaning...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

rem 4) build
echo [step] pyinstaller...
if exist "RouteManager.spec" (
  python -m PyInstaller "RouteManager.spec" || goto :fail
) else (
  echo [warn] RouteManager.spec not found, using default options...
  python -m PyInstaller -F -n RouteManager -i assets\app.ico src\main.py || goto :fail
)

rem 5) verify
if exist "dist\RouteManager.exe" (
  echo [ok] build success: dist\RouteManager.exe
  goto :end
)

:fail
echo [err] build failed. See logs above.

:end
pause
endlocal
