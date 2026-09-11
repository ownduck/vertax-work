#!/bin/bash
export DSH_BUNDLED_SKILL_DIR="$(cd "$(dirname "$0")" && pwd)/skills"
pnpm dsh web
