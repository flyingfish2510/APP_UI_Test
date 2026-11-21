#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[i] 已生成 .env，默认密码 ChangeMe_123（请修改）"
fi

if [ "${1:-}" = "appium" ]; then
  export COMPOSE_PROFILES=appium
  echo "[i] 同时构建并启动 Appium 容器（Linux + USB 直通）"
fi

echo "[i] 构建镜像（国内镜像源）..."
docker compose build

echo "[i] 启动容器..."
docker compose up -d --remove-orphans
docker compose ps

echo
echo "[OK] Jenkins: http://localhost:${JENKINS_HTTP_PORT:-8080}/"
echo "     账号 admin，密码见 .env 的 JENKINS_ADMIN_PASSWORD"
