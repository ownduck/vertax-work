@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "Get-ChildItem -Path . -Directory -Filter node_modules -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }"
pnpm install
if errorlevel 1 exit /b %errorlevel%
pnpm run build:artifacts
