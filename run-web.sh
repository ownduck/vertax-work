#!/bin/bash
export DSH_BUNDLED_SKILL_DIR="$(cd "$(dirname "$0")" && pwd)/skills"
sh build-web.sh
pnpm dsh web
