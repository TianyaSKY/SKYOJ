@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Build SKYOJ sandbox images:
rem   skyoj-runner     judge runtime
rem   skyoj-generator  testcase generator
rem
rem Usage:
rem   scripts\build-sandbox.bat
rem   scripts\build-sandbox.bat --no-cache
rem   scripts\build-sandbox.bat runner
rem   scripts\build-sandbox.bat generator

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
pushd "%ROOT_DIR%" >nul
if errorlevel 1 (
  echo [ERROR] Cannot enter project root: %ROOT_DIR%
  exit /b 1
)
set "ROOT_DIR=%CD%"
popd >nul

set "NO_CACHE=0"
set "TARGET=all"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--no-cache" set "NO_CACHE=1" & shift & goto parse_args
if /I "%~1"=="-h" goto show_help
if /I "%~1"=="--help" goto show_help
if /I "%~1"=="all" set "TARGET=all" & shift & goto parse_args
if /I "%~1"=="runner" set "TARGET=runner" & shift & goto parse_args
if /I "%~1"=="generator" set "TARGET=generator" & shift & goto parse_args
echo [ERROR] Unknown argument: %~1
echo Use --help for usage
exit /b 1

:show_help
echo Build SKYOJ sandbox images
echo.
echo Usage:
echo   scripts\build-sandbox.bat [all^|runner^|generator] [--no-cache]
echo.
echo Images:
echo   skyoj-runner     judge sandbox  (docker\runner)
echo   skyoj-generator  generator sandbox (docker\generator)
exit /b 0

:args_done
where docker >nul 2>&1
if errorlevel 1 (
  echo [ERROR] docker not found. Install and start Docker Desktop first.
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker daemon is not available. Start Docker Desktop first.
  exit /b 1
)

set "BUILD_FLAGS="
if "%NO_CACHE%"=="1" set "BUILD_FLAGS=--no-cache"

cd /d "%ROOT_DIR%"
if errorlevel 1 (
  echo [ERROR] Cannot enter project root: %ROOT_DIR%
  exit /b 1
)

echo Project root: %ROOT_DIR%
echo Build target: %TARGET%
echo.

if /I "%TARGET%"=="runner" goto build_runner_only
if /I "%TARGET%"=="generator" goto build_generator_only

call :build_image skyoj-runner "%ROOT_DIR%\docker\runner"
if errorlevel 1 exit /b 1
call :build_image skyoj-generator "%ROOT_DIR%\docker\generator"
if errorlevel 1 exit /b 1
goto finish

:build_runner_only
call :build_image skyoj-runner "%ROOT_DIR%\docker\runner"
if errorlevel 1 exit /b 1
goto finish

:build_generator_only
call :build_image skyoj-generator "%ROOT_DIR%\docker\generator"
if errorlevel 1 exit /b 1
goto finish

:finish
echo.
echo Related images:
docker images skyoj-runner
docker images skyoj-generator
echo.
echo Sandbox build finished. Next: docker compose up -d --build
exit /b 0

:build_image
set "IMG_NAME=%~1"
set "CTX=%~2"

if not exist "%CTX%\Dockerfile" (
  echo [ERROR] Dockerfile not found: %CTX%\Dockerfile
  exit /b 1
)

echo ========================================
echo  Building: %IMG_NAME%
echo  Context:  %CTX%
echo ========================================

if "%BUILD_FLAGS%"=="" (
  docker build -t "%IMG_NAME%" "%CTX%"
) else (
  docker build %BUILD_FLAGS% -t "%IMG_NAME%" "%CTX%"
)
if errorlevel 1 (
  echo [FAILED] %IMG_NAME%
  exit /b 1
)

echo [OK] %IMG_NAME%
echo.
exit /b 0
