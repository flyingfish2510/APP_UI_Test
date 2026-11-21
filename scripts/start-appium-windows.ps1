# 在 Windows 宿主机启动 Appium（设备连在 Windows 上时用这个）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\start-appium-windows.ps1
$ErrorActionPreference = 'Stop'

$npm = if (Get-Command npm.cmd -ErrorAction SilentlyContinue) { 'npm.cmd' } else { 'npm' }
$appium = if (Get-Command appium.cmd -ErrorAction SilentlyContinue) { 'appium.cmd' } else { 'appium' }

Write-Host '[i] 使用 npmmirror 源'
& $npm config set registry https://registry.npmmirror.com

if (-not (Get-Command appium.cmd -ErrorAction SilentlyContinue)) {
    Write-Host '[i] 安装 Appium 2 ...'
    & $npm install -g appium@2 --no-fund --no-audit
}

$installed = (& $appium driver list --installed 2>&1 | Out-String)
if ($installed -notmatch 'uiautomator2') {
    Write-Host '[i] 安装 uiautomator2 driver ...'
    & $appium driver install uiautomator2
}

Write-Host '[i] 当前 adb 设备：'
adb devices

Write-Host '[i] 启动 Appium：0.0.0.0:4723（保持此窗口运行）'
& $appium --address 0.0.0.0 --port 4723 --allow-insecure uiautomator2:adb_shell --log-level info
