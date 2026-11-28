# Jenkins Windows agent 守护脚本
# 用法:
#   powershell -ExecutionPolicy Bypass -File scripts\jenkins-agent.ps1 -Action start
#   powershell -ExecutionPolicy Bypass -File scripts\jenkins-agent.ps1 -Action status
#   powershell -ExecutionPolicy Bypass -File scripts\jenkins-agent.ps1 -Action stop
param(
    [ValidateSet('start', 'status', 'stop')]
    [string]$Action = 'start',
    [string]$Url = 'http://localhost:8080/',
    [string]$AgentName = 'windows-host',
    [string]$WorkDir = 'C:\jenkins-agent'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$logFile = Join-Path $logDir 'jenkins-agent.log'
$pidFile = Join-Path $logDir 'jenkins-agent.pid'
$secretFile = Join-Path $WorkDir 'secret.txt'
$jarFile = Join-Path $WorkDir 'agent.jar'
$java = 'D:\java\jdk-21.0.11\bin\java.exe'
$mutexName = 'Local\JenkinsAgentSupervisor'

function Write-Log([string]$Message) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-AgentJava {
    Get-CimInstance Win32_Process -Filter "Name='java.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'agent\.jar' }
}

switch ($Action) {
    'status' {
        $procs = @(Get-AgentJava)
        "agent java 进程数: $($procs.Count)"
        $procs | ForEach-Object { "  pid=$($_.ProcessId)" }
        if (Test-Path $pidFile) { "supervisor pid: $(Get-Content $pidFile)" }
        break
    }

    'stop' {
        if (Test-Path $pidFile) {
            $svcPid = [int](Get-Content $pidFile)
            & taskkill /PID $svcPid /T /F *> $null
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
            Write-Log "已停止 agent supervisor（pid=$svcPid）"
        }
        foreach ($p in @(Get-AgentJava)) {
            & taskkill /PID $p.ProcessId /T /F *> $null
        }
        Write-Log 'Jenkins agent 已停止'
        break
    }

    'start' {
        $mutex = New-Object System.Threading.Mutex($false, $mutexName)
        if (-not $mutex.WaitOne(0)) {
            Write-Log '已有 agent supervisor 在运行，退出'
            break
        }
        if (-not (Test-Path $secretFile)) {
            Write-Log "缺少 secret 文件: $secretFile（从 /computer/$AgentName/jenkins-agent.jnlp 获取）"
            break
        }
        $secret = (Get-Content $secretFile -Raw).Trim()
        $PID | Set-Content -LiteralPath $pidFile -Encoding ascii
        Write-Log "agent supervisor 启动（pid=$PID, url=$Url, name=$AgentName）"

        while ($true) {
            if (-not (Test-Path $jarFile)) {
                try {
                    Invoke-WebRequest -Uri "$($Url.TrimEnd('/'))/jnlpJars/agent.jar" -OutFile $jarFile -UseBasicParsing -TimeoutSec 30
                    Write-Log '已下载 agent.jar'
                } catch {
                    Write-Log "下载 agent.jar 失败: $($_.Exception.Message)，10s 后重试"
                    Start-Sleep -Seconds 10
                    continue
                }
            }

            try {
                $proc = Start-Process -FilePath $java `
                    -ArgumentList @('-jar', $jarFile, '-url', $Url, '-secret', $secret, '-name', $AgentName, '-workDir', $WorkDir) `
                    -RedirectStandardOutput (Join-Path $WorkDir 'agent.log') `
                    -RedirectStandardError (Join-Path $WorkDir 'agent.err.log') `
                    -PassThru -WindowStyle Hidden
                Write-Log "agent 已拉起（pid=$($proc.Id)）"
                $proc.WaitForExit()
                Write-Log "agent 退出（code=$($proc.ExitCode)），10s 后重连"
            } catch {
                Write-Log "启动 agent 失败: $($_.Exception.Message)，10s 后重试"
            }
            Start-Sleep -Seconds 10
        }
    }
}
