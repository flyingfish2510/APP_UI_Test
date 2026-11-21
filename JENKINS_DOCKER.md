# Docker 版 Jenkins：定时运行 APP_UI_Test

> 已在本机构建并验证：镜像 `app-ui-test/jenkins:2.591-py313`（1.39 GB），容器 `app-ui-jenkins` healthy，
> 任务 `APP_UI_Test` 已创建（cron `H 13 * * *`）。首次验证构建失败于「设备未连接」，属环境原因，不是容器问题。

## 1. 架构

```
┌──────────── Docker ────────────┐          ┌──────────────┐
│ Jenkins 容器 (jenkins 2.591)    │  HTTP    │ Appium 服务   │  ADB   ┌────────────┐
│  - Python 3.13 + /opt/venv      │ ───────> │ :4723        │ ─────> │ Android 设备 │
│  - Allure 插件 / CLI            │          │ 宿主机        │        └────────────┘
│  - /workspace = 项目挂载目录     │          └──────────────┘
└────────────────────────────────┘
```

- 测试代码跑在 **Jenkins 容器** 里，不需要 Docker-in-Docker。
- Windows 上 Appium 跑 **宿主机**；Linux 可选择跑容器（USB 直通）。
- `RUN_ENV=docker` 会让 `driver_manager` 跳过容器内不可用的 adb 检查，并读取 `APPIUM_HOST`（见 `.env`）。

## 2. 文件说明

| 文件 | 说明 |
|---|---|
| `docker/Dockerfile.jenkins` | 基于本机 `jenkins/jenkins:2.555.3-jdk21`，构建时下载 2.591 war 升级内核，装 Python venv + Allure + 82 个插件 |
| `docker/Dockerfile.appium` | Appium 2 + UiAutomator2 + adb（仅 Linux USB 场景） |
| `docker/plugins.txt` | 需要的插件名（输入） |
| `docker/plugins.lock` | 依赖闭包结果（name/version/url），构建时用 curl 逐个下载 |
| `docker/appium-entrypoint.sh` | 先起 adb server，再起 appium |
| `docker/daemon.json` | Docker Hub 镜像加速示例 |
| `docker-compose.yml` | Jenkins（+ 可选 appium）编排 |
| `jenkins/casc.yaml` | JCasC：管理员、执行器、全局环境变量、Allure 工具 |
| `jenkins/init/create-job.groovy` | 启动时创建/更新任务 `APP_UI_Test` 与 cron |
| `jenkins/Jenkinsfile` | 流水线：准备 → 环境检查 → pytest → Allure/JUnit |
| `.env.example` | 端口、密码、Appium 地址、通知 |
| `.dockerignore` | 构建上下文只保留 requirements.txt 和 docker/（构建 1 分钟内完成） |
| `scripts/build.ps1` / `build.sh` | 一键构建 + 启动 |
| `scripts/start-appium-windows.ps1` | Windows 宿主机启动 Appium |
| `scripts/gen_plugins_lock.py` | 改插件清单后重新生成 `plugins.lock` |

## 3. 日常使用

```powershell
# 构建 + 启动（已构建过则秒级）
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 宿主机启动 Appium（保持窗口）
powershell -ExecutionPolicy Bypass -File scripts\start-appium-windows.ps1

# 查看状态 / 日志
docker compose ps
docker logs -f app-ui-jenkins

# 停止 / 彻底重置（含 Jenkins 数据）
docker compose down
docker compose down -v
```

Jenkins：<http://localhost:8080>，账号 `admin`，密码见 `.env`（默认 `ChangeMe_123`，务必修改）。

## 4. 定时与参数

- 任务 `APP_UI_Test` 由 `jenkins/init/create-job.groovy` 在启动时创建。
- 默认 cron：`H 13 * * *`（每天 13 点档，容器时区 `Asia/Shanghai`）。
- **改 cron**：编辑 `jenkins/init/create-job.groovy` → `docker compose restart jenkins`（启动脚本会重写任务）。
- **改流水线**：编辑 `jenkins/Jenkinsfile` → `docker compose restart jenkins`（脚本内容在启动时写入任务）。
- 运行参数：`TEST_MARKER`（smoke/regression/p0..p3/all）、`RERUNS`、`PYTEST_TIMEOUT`、`CLEAN_ARTIFACTS`。
- 报告：`BUILD_URL/allure/`（Allure 插件），JUnit 在 `reports/junit.xml`，产物归档在 `/workspace`。

## 5. Linux 全容器（USB 直通）

```bash
adb kill-server                 # 宿主机先释放 USB
bash scripts/build.sh appium    # 同时构建 appium 容器
# 把 .env 里的 APPIUM_HOST 改成 http://appium:4723 后
docker compose up -d
```

要求：Linux 宿主机、`/dev/bus/usb` 可访问、容器 `privileged`。

## 6. 国内镜像与构建策略

| 环节 | 来源 | 位置 |
|---|---|---|
| Debian apt | 清华 TUNA | 两个 Dockerfile |
| pip | 清华 PyPI | Dockerfile.jenkins |
| npm | npmmirror | Dockerfile.appium、Windows 脚本 |
| Jenkins 内核 war | 华为云 `jenkins/war/2.591/jenkins.war` | Dockerfile.jenkins |
| Jenkins 插件 | 华为云镜像（`plugins.lock` 记录 URL，curl 下载） | Dockerfile.jenkins |
| Allure CLI | 阿里云 Maven（回退 Maven Central） | Dockerfile.jenkins |
| Docker Hub | daemon.json 的 registry-mirrors | Docker 引擎配置 |

**为什么不用 `jenkins-plugin-cli`**：在本机网络下它把镜像返回的 hpi 判为 invalid ZIP，并回退到不可达的 `archives.jenkins.io`。改为先用 `scripts/gen_plugins_lock.py` 在宿主机解析依赖、生成 lock，构建时用 curl 直接下载，稳定且可复现。

**为什么升级内核**：基础镜像 2.555.3 低于当前插件的 `requiredCore`（2.589），构建时下载 2.591 war 覆盖 `/usr/share/jenkins/jenkins.war`。

**Python 3.13 兼容**：基础镜像是 Debian 13（Python 3.13），`requirements.txt` 已锁定 `psutil==7.2.2`、`PyYAML==6.0.2`（均提供 cp313 wheel），构建时不再改写版本。

## 7. 与项目代码的适配点

1. **不调用 `run_tests.py`**：其 `--reruns/--maxfail/--timeout/--parallel` 未真正传给 pytest；流水线直接调 `python -m pytest`。
2. **`customWorkspace '/workspace'`**：项目依赖 `config/config.yaml` 等相对路径，必须在项目根目录运行。
3. **`RUN_ENV=docker`**：跳过 adb 检查，改用 `APPIUM_HOST`；Appium 需带 `--allow-insecure uiautomator2:adb_shell`。
4. **Allure 结果目录**统一为 `reports/allure-results`，与 `pytest.ini` 一致。

## 8. 排错

| 现象 | 处理 |
|---|---|
| 构建报 `Appium 不可达` | 宿主机 Appium 未启动或 4723 未监听；`curl http://127.0.0.1:4723/status` 自查 |
| 构建报 `Could not find a connected Android device` | 设备未连接：改 `config/device_config.yaml` 的 `udid`，或连上真机后 `adb devices` 确认 |
| 8080 被占用 | 改 `.env` 的 `JENKINS_HTTP_PORT` |
| 改了 Jenkinsfile / cron 没生效 | `docker compose restart jenkins`（内容在启动时注入任务） |
| 插件要升级 | 改 `docker/plugins.txt` → `python scripts/gen_plugins_lock.py` → `docker compose build` |
| 任务没创建 | 看 `docker logs app-ui-jenkins | grep "\[init\]"` |
| Linux 下 reports 属 root | `sudo chown -R $USER reports logs screenshots allure-report` |
