#!/bin/bash
sh build-clean.sh
export DSH_DESKTOP_APP_ID='com.vertax.work'
export DOWNLOAD_TEST_ORIGIN='https://example.com'
export DSH_BUILD_CLIENT_PROFILE=official
export DSH_CLIENT_TITLE='Vertax Work'
pnpm run package:desktop:win:x64:dir
