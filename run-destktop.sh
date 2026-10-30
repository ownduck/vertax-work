#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

export DSH_BUILD_CLIENT_PROFILE=official
export DSH_BUNDLED_SKILL_DIR="$(pwd)/skills"

if [[ ! -f packages/boot/app-boot/lib/index.js || ! -f apps/desktop/lib/main.js ]]; then
  echo "run-destktop: artifacts missing, building first..."
  pnpm run build:artifacts
  pnpm --filter @deepseek-ai/dsh-desktop run build
else
  echo "run-destktop: artifacts present, skip rebuild"
fi

pnpm run start:desktop
