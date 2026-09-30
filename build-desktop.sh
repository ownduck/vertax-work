#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

sh build-clean.sh
export DSH_BUILD_CLIENT_PROFILE=official
export ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
pnpm run package:desktop:win:x64:unsigned

OUT=apps/desktop/.desktop-build/targets/win-x64/unsigned-artifacts
EXE=$(ls -1t "$OUT"/*-win-x64-unsigned.exe 2>/dev/null | head -n 1)
UNPACKED="$OUT/win-unpacked"
APP=$(ls -1 "$UNPACKED"/*.exe 2>/dev/null | head -n 1)

[[ -n "${EXE:-}" && -f "$EXE" && -s "$EXE" ]] || { echo "ERROR: 安装包缺失: $OUT/*-win-x64-unsigned.exe"; exit 1; }
[[ -n "${APP:-}" && -f "$APP" ]] || { echo "ERROR: win-unpacked 主程序缺失: $UNPACKED"; exit 1; }

echo
echo "======== 校验通过 ========"
echo "安装包: $(pwd)/$EXE"
echo "主程序: $(pwd)/$APP"
echo
echo "真实使用请拷贝："
echo "  1) 安装包（给用户安装）: $(pwd)/$EXE"
echo "  2) 免安装目录（可选，整目录拷走）: $(pwd)/$UNPACKED"
echo "=========================="
read -r -p "按回车结束..."
