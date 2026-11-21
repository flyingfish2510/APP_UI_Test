#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] 启动 adb server ..."
adb start-server || true

echo "[entrypoint] 当前设备列表："
adb devices || true

exec appium \
  --address 0.0.0.0 \
  --port "${APPIUM_PORT:-4723}" \
  --allow-insecure uiautomator2:adb_shell \
  --log-level "${APPIUM_LOG_LEVEL:-info}"
