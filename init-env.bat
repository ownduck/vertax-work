@echo off
setlocal EnableExtensions

rem Copy this script's sibling .env into %%DSH_HOME%%\.env (default %%USERPROFILE%%\.dsh).
rem If sibling .env is missing, create an empty one first, then copy.

set "SRC_DIR=%~dp0"
set "SRC_ENV=%SRC_DIR%.env"

if not defined DSH_HOME set "DSH_HOME=%USERPROFILE%\.dsh"
if "%DSH_HOME%"=="" set "DSH_HOME=%USERPROFILE%\.dsh"

for %%I in ("%SRC_ENV%") do set "SRC_ABS=%%~fI"
for %%I in ("%DSH_HOME%\.env") do set "DST_ABS=%%~fI"

if not exist "%DSH_HOME%\" (
  mkdir "%DSH_HOME%" 2>nul
  if errorlevel 1 (
    echo init-env: failed to create DSH_HOME "%DSH_HOME%"
    goto :done_fail
  )
)

if not exist "%SRC_ENV%" (
  type nul > "%SRC_ENV%"
  if errorlevel 1 (
    echo init-env: failed to create "%SRC_ABS%"
    goto :done_fail
  )
  echo init-env: created empty "%SRC_ABS%"
)

echo init-env: copy
echo   from: %SRC_ABS%
echo   to:   %DST_ABS%
copy /Y "%SRC_ENV%" "%DSH_HOME%\.env" >nul
if errorlevel 1 (
  echo init-env: copy failed
  goto :done_fail
)

echo init-env: done
goto :done_ok

:done_fail
pause
exit /b 1

:done_ok
pause
exit /b 0
