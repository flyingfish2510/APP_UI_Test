# Jenkins锛圖ocker 鎺у埗鍣級+ Windows agent锛氬畾鏃惰繍琛?APP_UI_Test

> 宸查獙璇侊細鏋勫缓 #12 鍦?`windows-host` 涓婇€氳繃锛坄1 passed, 2 deselected`锛夛紝Appium 闅忔瀯寤鸿嚜鍚€佺粨鏉熷悗鑷姩鍋滄锛孉llure 鎶ュ憡鍦ㄥ涓绘満鐢熸垚骞跺綊妗ｃ€?
## 1. 鏋舵瀯

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€ Docker 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?        鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€ Windows 瀹夸富鏈?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?Jenkins 鎺у埗鍣?                 鈹? JNLP   鈹?Jenkins agent (scripts/jenkins-agent)  鈹?鈹?- 2.591 / 8080                  鈹?<鈹€鈹€鈹€鈹€鈹€> 鈹? - 鎵ц pytest锛堥」鐩?.venv锛?          鈹?鈹?- JCasC / 瀹氭椂浠诲姟 / Allure 鎻掍欢 鈹?        鈹? - Appium 闅忔瀯寤鸿嚜鍚紝缁撴潫鑷姩鍏抽棴      鈹?鈹?- /workspace = 椤圭洰鎸傝浇锛堝彧璇荤敤锛夆攤         鈹? - adb 鈫?USB 鐪熸満 619aae4              鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?        鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

- 鎺у埗鍣ㄥ彧璐熻矗璋冨害鍜屽睍绀猴紱**娴嬭瘯涓?Appium 閮借窇鍦ㄥ涓绘満**锛屽洜涓?Windows 涓婂鍣ㄦ棤娉曡闂?USB 璁惧銆?- `RUN_ENV=local`锛氭鏋跺湪 `pytest_sessionstart` 鍚姩 Appium锛坄appium.bind_host=0.0.0.0`锛夛紝`pytest_sessionfinish` 鍏抽棴骞舵潃杩涚▼鏍戙€?
## 2. 鏂囦欢璇存槑

| 鏂囦欢 | 璇存槑 |
|---|---|
| `docker/Dockerfile.jenkins` | 鎺у埗鍣ㄩ暅鍍忥紙Jenkins 2.591 + 闈㈡澘/鎻掍欢 + Allure锛?|
| `docker/plugins.lock` / `plugins.txt` | 82 涓彃浠跺強渚濊禆闂寘锛堟瀯寤烘椂 curl 涓嬭浇锛?|
| `docker-compose.yml` | 鎺у埗鍣ㄧ紪鎺掞紙8080銆佹暟鎹嵎銆丆asC 鎸傝浇锛?|
| `jenkins/casc.yaml` | 绠＄悊鍛樸€佹墽琛屽櫒銆乣windows-host` 鑺傜偣銆丄llure 宸ュ叿璺緞 |
| `jenkins/Jenkinsfile` | 娴佹按绾匡細鍑嗗 鈫?璁惧妫€鏌?鈫?pytest锛圥owerShell 姝ラ锛?|
| `jenkins/init/create-job.groovy` | 鍚姩鏃跺垱寤轰换鍔?`APP_UI_Test` + cron `H 13 * * *` |
| `scripts/jenkins-agent.ps1` | agent 瀹堟姢/鍚仠锛堣嚜鍔ㄩ噸杩烇級 |
| `scripts/start-appium-windows.ps1` | 鎵嬪姩鍚姩 Appium锛堣皟璇曠敤锛?|
| `scripts/gen_plugins_lock.py` | 鎻掍欢鍗囩骇鍚庨噸鏂扮敓鎴?lock |

## 3. 涓€娆℃€у噯澶?
```powershell
cd D:\DeepSeekTest\APP_UI_Test

# 1) 鏋勫缓骞跺惎鍔ㄦ帶鍒跺櫒
powershell -ExecutionPolicy Bypass -File scripts\build.ps1

# 2) 鍚姩 agent锛堝凡娉ㄥ唽鐧诲綍鑷惎璁″垝浠诲姟 JenkinsAgent锛?powershell -ExecutionPolicy Bypass -File scripts\jenkins-agent.ps1 -Action status
# 鑻ユ湭杩愯锛?powershell -ExecutionPolicy Bypass -File scripts\jenkins-agent.ps1 -Action start

# 3) 纭璁惧
adb devices
```

agent 鐨勬帴鍏ュ瘑閽ヤ繚瀛樺湪 `C:\jenkins-agent\secret.txt`锛涜嫢鍦?Jenkins 閲屽垹鎺夊苟閲嶅缓浜嗚妭鐐癸紝闇€浠?`/computer/windows-host/jenkins-agent.jnlp` 閲嶆柊鑾峰彇骞惰鐩栬鏂囦欢锛屽啀閲嶅惎 agent銆?
## 4. 鏃ュ父浣跨敤

1. 鎵撳紑 <http://localhost:8080>锛宍admin` / `.env` 鐨?`JENKINS_ADMIN_PASSWORD`銆?2. 浠诲姟 `APP_UI_Test` 鈫?**Build with Parameters**锛?   - `TEST_MARKER`锛歚smoke` / `regression` / `p0`~`p3` / `all`
   - `RERUNS`銆乣PYTEST_TIMEOUT`銆乣CLEAN_ARTIFACTS`
3. 鐪嬬粨鏋滐細Console Output銆丄llure Report銆乀est Result銆丄rtifacts锛坄logs/*.log`銆乣reports/junit.xml`锛夈€?
瀹氭椂锛氭瘡澶?13 鐐规。锛坄H 13 * * *`锛孉sia/Shanghai锛夛紝鍙傛暟鍙栦换鍔￠粯璁ゅ€笺€?
## 5. Appium 鐢熷懡鍛ㄦ湡

| 鏃舵満 | 琛屼负 |
|---|---|
| 鏋勫缓寮€濮嬶紙sessionstart锛?| `autostart: true` 鈫?鍚姩 `appium --address 0.0.0.0 --port 4723`锛岃疆璇?`/status` 鏈€澶?60s |
| 鏋勫缓缁撴潫锛坰essionfinish锛?| 鍋滄鏈繘绋嬪惎鍔ㄧ殑 Appium锛屽苟鏉€鎺?`node` 瀛愯繘绋?|
| 鍚姩澶辫触 | 鐩存帴 `pytest.exit`锛屾瀯寤哄揩閫熷け璐ワ紙涓嶄細璺戜竴鍗婏級 |

鐩稿叧閰嶇疆鍦?`config/config.yaml`锛?
```yaml
appium:
  autostart: true
  bind_host: "0.0.0.0"
  startup_timeout: 60          # 鍙敤鐜鍙橀噺 APPIUM_STARTUP_TIMEOUT 瑕嗙洊
  log_file: "./logs/appium.log"
```

## 6. 鏀瑰摢閲屻€佹€庝箞鐢熸晥

| 鏀瑰姩 | 鐢熸晥鏂瑰紡 |
|---|---|
| 娴嬭瘯浠ｇ爜 / `config/` | 涓嬫鏋勫缓鍗冲彲锛坅gent 鐩存帴鐢ㄩ」鐩洰褰曪級 |
| `jenkins/Jenkinsfile` | `docker compose restart jenkins`锛堣剼鏈湪鍚姩鏃舵敞鍏ヤ换鍔★級 |
| `jenkins/casc.yaml` | `docker compose restart jenkins` |
| `scripts/jenkins-agent.ps1` | `-Action stop` 鍐?`-Action start` |
| 鎻掍欢 | 鏀?`docker/plugins.txt` 鈫?`python scripts/gen_plugins_lock.py` 鈫?`docker compose build` |
| 绔彛 / 鎸傝浇 | 鏀?`docker-compose.yml` 鈫?`docker compose up -d --force-recreate jenkins` |

## 7. 鎺掗敊

| 鐜拌薄 | 澶勭悊 |
|---|---|
| 鏋勫缓涓€鐩存帓闃?/ 鎶ユ病鏈?`windows-host` 鎵ц鍣?| agent 鎺夌嚎锛歚scripts\jenkins-agent.ps1 -Action status`锛岀湅 `logs/jenkins-agent.log`銆乣C:\jenkins-agent\agent.log` |
| `Authentication failed` / secret 閿欒 | 閲嶆柊鑾峰彇 secret 鍐欏叆 `C:\jenkins-agent\secret.txt`锛岄噸鍚?agent |
| `娌℃湁鍙敤璁惧` | `adb devices` 涓虹┖鎴栨湭鎺堟潈锛涙彃绾垮悗鎵嬫満鐐光€滃厑璁?USB 璋冭瘯鈥?|
| `Appium鏈嶅姟鍚姩澶辫触` | 鐪?`logs/appium.log`锛涚‘璁?4723 鏈鍗犵敤銆乣appium` 涓?`uiautomator2` 宸插畨瑁?|
| 鏋勫缓閫氳繃浣?Appium 娌″叧 | 妫€鏌?`logs/appium.log` 灏鹃儴鏄惁琚仠姝紱纭娌℃湁澶栭儴鍚姩鐨?Appium 鍗犵敤 4723 |
| Allure 鎶ュ憡绌虹櫧 | 纭 `D:\allure-2.32.2\bin\allure.bat` 瀛樺湪锛坈asC 鐨?`tool.allure.home`锛?|
| 8080 琚崰 | 鏀?`.env` 鐨?`JENKINS_HTTP_PORT` |

## 8. 甯哥敤鍛戒护

```powershell
docker compose ps
docker logs -f app-ui-jenkins
docker compose restart jenkins
docker compose down            # 淇濈暀鏁版嵁鍗?docker compose down -v         # 杩炴暟鎹嵎涓€璧峰垹锛堜换鍔′細鐢?init 鑴氭湰閲嶅缓锛?
powershell -ExecutionPolicy Bypass -File scripts\jenkins-agent.ps1 -Action status
powershell -ExecutionPolicy Bypass -File scripts\jenkins-agent.ps1 -Action stop
schtasks /Run /TN JenkinsAgent
```
