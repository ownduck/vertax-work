#!/bin/bash
export DSH_BUILD_CLIENT_PROFILE=official
export DSH_BUNDLED_SKILL_DIR="$(cd "$(dirname "$0")" && pwd)/skills"
pnpm run dev:web
