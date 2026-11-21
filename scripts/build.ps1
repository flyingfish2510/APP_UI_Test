$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host '[i] 已生成 .env，默认密码 ChangeMe_123（请修改）'
}

if ($args -contains 'appium') {
    $env:COMPOSE_PROFILES = 'appium'
    Write-Host '[i] 同时构建并启动 Appium 容器（仅 Linux）'
}

Write-Host '[i] 构建镜像（国内镜像源）...'
docker compose build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '[i] 启动容器...'
docker compose up -d --remove-orphans
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

docker compose ps
Write-Host ''
Write-Host '[OK] Jenkins: http://localhost:8080/  (账号 admin，密码见 .env)'
