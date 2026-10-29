@echo off
setlocal

rem Test build of updater_gui.exe with PyInstaller (fast iteration; the shipped
rem release still comes from scripts\build_gui.bat / Nuitka).
rem
rem Environment contract (docs/specs/gui_folder_dialog_spec.md section 1):
rem   pywebview must be 6.2.1 - the folder dialog only exists as
rem   Window.create_file_dialog(webview.FileDialog.FOLDER) on that line, and an
rem   unpinned dependency is what broke the 1.5.0 "browse" button.
rem
rem The console stays attached on purpose: a test build must show import errors
rem instead of dying silently the way console=disable did in 1.5.0.

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
set VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe
rem Thin launcher, not app.py itself: the entry file is frozen as __main__ whose
rem __file__ is the bundle root, which would break app.py's frontend lookup.
set SOURCE_FILE=%SCRIPT_DIR%entry_gui.py
set FRONTEND_DIR=%ROOT_DIR%\src\updater\gui\frontend
set OUTPUT_DIR=%ROOT_DIR%\dist
set PYI_OUT=%OUTPUT_DIR%\pyinstaller_build
set PYI_DIST=%OUTPUT_DIR%\pyinstaller
set REQUIRED_PYWEBVIEW=6.2.1

if not exist "%VENV_PYTHON%" (
    echo [ERROR] venv not found at %VENV_PYTHON%
    echo Please create the venv first: python -m venv .venv
    pause
    exit /b 1
)

echo Checking pywebview %REQUIRED_PYWEBVIEW% ...
"%VENV_PYTHON%" -c "import sys,importlib.metadata as md; v=md.version('pywebview'); print('pywebview', v); sys.exit(0 if v=='%REQUIRED_PYWEBVIEW%' else 1)"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] pywebview must be %REQUIRED_PYWEBVIEW%.
    echo         Run: "%VENV_PYTHON%" -m pip install "pywebview==%REQUIRED_PYWEBVIEW%"
    pause
    exit /b 1
)

echo Checking PyInstaller ...
"%VENV_PYTHON%" -m PyInstaller --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller not installed. Run: pip install pyinstaller
    pause
    exit /b 1
)

echo.
echo Building frontend...
cd "%FRONTEND_DIR%"
call npm run build
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b 1
)
cd "%ROOT_DIR%"

if not exist "%FRONTEND_DIR%\dist\index.html" (
    echo [ERROR] Frontend dist missing: %FRONTEND_DIR%\dist\index.html
    pause
    exit /b 1
)

if exist "%PYI_OUT%" rmdir /s /q "%PYI_OUT%"
if exist "%PYI_DIST%" rmdir /s /q "%PYI_DIST%"

echo.
echo Building updater_gui.exe ^(PyInstaller onedir^)...
rem app.py resolves the UI as Path(__file__).parent / "frontend" / "dist".  With
rem scripts\entry_gui.py as the entry, app.py is an imported module whose __file__
rem is _internal\updater\gui\app.py, so --add-data mirrors the package location
rem (PyInstaller docs, runtime-information: the destination "should mirror" it).
rem NOTE: the Nuitka build (build_gui.bat) still freezes app.py as its main
rem module and therefore maps the same folder to "frontend/dist" - keep the two
rem in sync if that entry ever changes.
"%VENV_PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --name updater_gui ^
    --paths "%ROOT_DIR%\src" ^
    --add-data "%FRONTEND_DIR%\dist;updater\gui\frontend\dist" ^
    --hidden-import webview.platforms.winforms ^
    --exclude-module webview.platforms.gtk ^
    --exclude-module webview.platforms.cocoa ^
    --exclude-module webview.platforms.qt ^
    --exclude-module webview.platforms.android ^
    --distpath "%PYI_DIST%" ^
    --workpath "%PYI_OUT%\build" ^
    --specpath "%PYI_OUT%" ^
    "%SOURCE_FILE%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

if not exist "%PYI_DIST%\updater_gui\updater_gui.exe" (
    echo [ERROR] output not found: %PYI_DIST%\updater_gui\updater_gui.exe
    pause
    exit /b 1
)

echo.
echo Built: %PYI_DIST%\updater_gui\updater_gui.exe
echo Test:  "%PYI_DIST%\updater_gui\updater_gui.exe" --project C:\Test_Matrix
echo.
pause
