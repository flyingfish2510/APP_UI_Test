"""
Appium Driver管理器（集成自定义异常版本）
负责创建、管理和销毁Appium Driver实例
支持本地Windows和Docker环境自动切换
"""

import os
import time
import yaml
import subprocess
from typing import Dict, Optional, List
import allure
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.appium_service import AppiumService
from core.logger import get_logger
from core.exceptions import (
    ConfigFileNotFoundError,
    DeviceNotFoundError,
    DeviceOfflineError,
    DeviceBusyError,
    DriverCreationError,
    DriverNotInitializedError,
    AppiumServiceStartError,
    AppiumConnectionError
)
from core.config_validator import ConfigValidator

logger = get_logger(__name__)


class DriverManager:
    """Appium Driver 管理器"""

    def __init__(self, config_path: str = "config/config.yaml",
                 device_config_path: str = "config/device_config.yaml"):
        try:
            self.config = self._load_config(config_path)
            self.devices_config = self._load_config(device_config_path)
        except ConfigFileNotFoundError:
            raise

        ConfigValidator.validate_yaml(self.config)

        self.appium_service: Optional[AppiumService] = None
        self.appium_process = None
        self.drivers: Dict[str, webdriver.Remote] = {}
        self.active_drivers: List[str] = []
        self.run_env = self._get_run_environment()
        logger.info(f"当前运行环境: {self.run_env}")
        self._validate_device_config()

    @staticmethod
    def _load_config(config_path: str) -> dict:
        """加载 YAML 配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None:
                    logger.warning(f"配置文件为空: {config_path}")
                    return {}
                return config
        except FileNotFoundError:
            raise ConfigFileNotFoundError(file_path=config_path)
        except yaml.YAMLError:
            raise ConfigFileNotFoundError(file_path=config_path)

    def _validate_device_config(self):
        """验证设备配置"""
        devices = self.devices_config.get('devices', [])
        if not devices:
            logger.warning("设备配置列表为空，请检查device_config.yaml")
            return
        for i, device in enumerate(devices):
            if 'device_name' not in device and 'udid' not in device:
                logger.warning(f"设备 {i} 缺少device_name或udid字段")

    def _get_run_environment(self) -> str:
        """判断当前运行环境"""
        env = os.getenv('RUN_ENV')
        if env:
            return env.lower()
        if os.getenv('CI', '').lower() == 'true':
            logger.info("检测到CI环境")
            return 'docker'
        return self.config.get('environment', {}).get('run_env', 'local')

    def _get_appium_url(self) -> str:
        """根据运行环境获取 Appium 服务地址"""
        appium_config = self.config.get('appium', {})
        if self.run_env == 'docker':
            docker_host = os.getenv('APPIUM_HOST', appium_config.get('docker_host', 'http://appium:4723'))
            return docker_host
        else:
            return appium_config.get('local_host', 'http://127.0.0.1:4723')

    def _get_appium_host_port(self) -> tuple:
        """从 Appium URL 解析 host 和 port"""
        appium_url = self._get_appium_url()
        url_without_protocol = appium_url.replace('http://', '').replace('https://', '')
        parts = url_without_protocol.split(':')
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 4723
        return host, port

    def _get_adb_devices(self) -> List[str]:
        """
        获取 ADB 已连接设备列表

        Returns:
            List[str]: 已连接的设备 UDID 列表
        """
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                logger.error(f"adb devices 命令执行失败: {result.stderr}")
                return []

            lines = result.stdout.strip().split('\n')[1:]
            devices = []
            for line in lines:
                line = line.strip()
                if line and '\t' in line:
                    udid, status = line.split('\t')
                    if status == 'device':
                        devices.append(udid)
            return devices
        except FileNotFoundError:
            logger.error("adb 未安装或不在 PATH 中")
            return []
        except subprocess.TimeoutExpired:
            logger.error("adb devices 命令执行超时")
            return []
        except Exception as e:
            logger.error(f"获取 ADB 设备列表异常: {e}")
            return []

    def _check_device_connected(self, udid: str) -> bool:
        """
        检查指定设备是否通过 ADB 连接

        Args:
            udid: 设备 UDID

        Returns:
            bool: True 表示设备已连接且状态正常
        """
        if not udid:
            logger.warning("UDID 为空，跳过设备健康检查")
            return True

        connected_devices = self._get_adb_devices()
        if udid in connected_devices:
            logger.info(f"设备健康检查通过: {udid}")
            return True
        else:
            logger.warning(f"设备健康检查失败: {udid} 未在 ADB 设备列表中")
            logger.debug(f"当前已连接设备: {connected_devices}")
            return False

    def _check_device_online(self, udid: str) -> bool:
        """
        检查设备是否在线（非 offline 状态）

        通过 adb -s <udid> get-state 获取设备状态。

        Args:
            udid: 设备 UDID

        Returns:
            bool: True 表示设备在线
        """
        if not udid:
            return True

        try:
            result = subprocess.run(
                ['adb', '-s', udid, 'get-state'],
                capture_output=True,
                text=True,
                timeout=10
            )
            state = result.stdout.strip()
            if state == 'device':
                logger.info(f"设备状态正常: {udid} (state={state})")
                return True
            else:
                logger.warning(f"设备状态异常: {udid} (state={state})")
                return False
        except FileNotFoundError:
            logger.error("adb 未安装或不在 PATH 中")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"检查设备状态超时: {udid}")
            return False
        except Exception as e:
            logger.error(f"检查设备状态异常: {e}")
            return False

    @staticmethod
    def _create_capabilities(device_config: dict) -> UiAutomator2Options:
        """根据设备配置创建 Appium Capabilities"""
        options = UiAutomator2Options()
        options.platform_name = device_config.get('platform_name', 'Android')
        options.automation_name = device_config.get('automation_name', 'UiAutomator2')
        options.device_name = device_config.get('device_name', 'Android Emulator')
        if 'udid' in device_config:
            options.udid = device_config['udid']
        if 'platform_version' in device_config:
            options.platform_version = device_config['platform_version']
        options.no_reset = device_config.get('no_reset', True)
        options.full_reset = device_config.get('full_reset', False)
        options.new_command_timeout = device_config.get('new_command_timeout', 600)
        if device_config.get('auto_grant_permissions', True):
            options.auto_grant_permissions = True
        if device_config.get('skip_server_installation', True):
            options.skip_server_installation = True
        if device_config.get('skip_device_initialization', False):
            options.skip_device_initialization = True
        return options

    @allure.step("启动Appium服务")
    def start_appium_service(self):
        """启动 Appium 服务（仅本地环境）"""
        if self.run_env == 'docker':
            self.wait_for_appium_ready()
            return

        import requests

        host, port = self._get_appium_host_port()
        appium_config = self.config.get('appium', {})
        allow_insecure = appium_config.get('allow_insecure', 'uiautomator2:adb_shell')

        try:
            logger.info(f"正在启动Appium服务... (host={host}, port={port})")
            cmd = f'appium --address {host} --port {port} --allow-insecure {allow_insecure}'
            self.appium_process = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            status_url = f'http://{host}:{port}/status'
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(status_url, timeout=1)
                    if response.status_code == 200:
                        logger.info("Appium服务已启动")
                        return
                except requests.ConnectionError:
                    pass
                time.sleep(2)
            raise AppiumServiceStartError(service_url=status_url, reason="服务启动超时")
        except AppiumServiceStartError:
            raise
        except Exception as e:
            raise AppiumServiceStartError(service_url=f'http://{host}:{port}', reason=str(e)) from e

    def wait_for_appium_ready(self):
        """等待 Appium 服务就绪（Docker 环境）"""
        import requests
        appium_url = self._get_appium_url()
        for i in range(30):
            try:
                response = requests.get(f"{appium_url}/status", timeout=2)
                if response.status_code == 200:
                    logger.info(f"Appium服务已就绪: {appium_url}")
                    return True
            except requests.ConnectionError:
                pass
            time.sleep(2)
        raise AppiumConnectionError(service_url=appium_url, reason="Appium服务未就绪")

    @allure.step("停止Appium服务")
    def stop_appium_service(self):
        """停止 Appium 服务"""
        if self.appium_process:
            try:
                self.appium_process.terminate()
                logger.info("Appium服务已停止")
            except Exception as e:
                logger.error(f"停止Appium服务失败: {e}")

    @allure.step("创建Driver (设备索引: {device_index})")
    def create_driver(self, device_index: int = 0) -> webdriver.Remote:
        """为指定设备创建 Driver 实例"""
        device_name = None
        udid = None
        try:
            devices = self.devices_config.get('devices', [])
            if not devices:
                raise DeviceNotFoundError(message="设备配置列表为空")
            if device_index >= len(devices):
                raise DeviceNotFoundError(device_index=device_index,
                                          message=f"设备索引 {device_index} 超出范围")

            device_config = devices[device_index]
            device_name = device_config.get('device_name', f'device_{device_index}')
            udid = device_config.get('udid', 'N/A')

            # ========== 设备健康检查 ==========
            if not self._check_device_connected(udid):
                raise DeviceOfflineError(
                    device_name=device_name,
                    udid=udid
                )

            if not self._check_device_online(udid):
                raise DeviceOfflineError(
                    device_name=device_name,
                    udid=udid
                )
            # ========== 健康检查结束 ==========

            logger.info(f"正在为设备 [{device_name}] (UDID: {udid}) 创建Driver...")
            options = self._create_capabilities(device_config)
            appium_url = self._get_appium_url()
            driver = webdriver.Remote(command_executor=appium_url, options=options)
            if not driver.session_id:
                raise DriverCreationError(device_name=device_name, original_error="Session ID为空")
            implicit_wait = self.config.get('timeout', {}).get('implicit_wait', 10)
            driver.implicitly_wait(implicit_wait)
            self.drivers[device_name] = driver
            self.active_drivers.append(device_name)
            logger.info(f"设备 [{device_name}] Driver创建成功")
            return driver
        except DeviceNotFoundError:
            raise
        except DeviceOfflineError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if 'connection' in error_msg or 'refused' in error_msg:
                raise AppiumConnectionError(service_url=self._get_appium_url(), reason=str(e)) from e
            elif 'offline' in error_msg:
                raise DeviceOfflineError(device_name=device_name, udid=udid) from e
            elif 'not found' in error_msg:
                raise DeviceNotFoundError(device_name=device_name, udid=udid, device_index=device_index) from e
            elif 'busy' in error_msg:
                raise DeviceBusyError(device_name=device_name, udid=udid) from e
            else:
                raise DriverCreationError(device_name=device_name, original_error=str(e)) from e

    def get_driver(self, device_name: str = None) -> Optional[webdriver.Remote]:
        """获取指定设备的 Driver"""
        if not self.drivers:
            raise DriverNotInitializedError(message="没有可用的Driver实例")
        if device_name:
            if device_name not in self.drivers:
                raise DeviceNotFoundError(device_name=device_name)
            return self.drivers[device_name]
        if self.active_drivers:
            return self.drivers[self.active_drivers[0]]
        raise DriverNotInitializedError(message="没有活跃的Driver实例")

    def quit_driver(self, device_name: str = None):
        """关闭指定设备的 Driver"""
        if device_name:
            if device_name in self.drivers:
                try:
                    self.drivers[device_name].quit()
                    logger.info(f"设备 [{device_name}] Driver已关闭")
                except Exception as e:
                    logger.error(f"关闭设备 [{device_name}] Driver失败: {e}")
                finally:
                    del self.drivers[device_name]
                    if device_name in self.active_drivers:
                        self.active_drivers.remove(device_name)
        else:
            for name in list(self.drivers.keys()):
                self.quit_driver(name)

    @allure.step("关闭所有Driver")
    def quit_all_drivers(self):
        """关闭所有 Driver"""
        logger.info("正在关闭所有Driver...")
        self.quit_driver()
        logger.info("所有Driver已关闭")

    def get_device_count(self) -> int:
        """获取设备数量"""
        return len(self.devices_config.get('devices', []))

    def get_device_info(self, device_index: int = None) -> List[Dict]:
        """获取设备配置信息"""
        devices = self.devices_config.get('devices', [])
        if device_index is not None:
            if device_index < len(devices):
                return [devices[device_index]]
            return []
        return devices

    def is_device_connected(self, device_name: str) -> bool:
        """检查设备是否已连接"""
        return device_name in self.drivers and device_name in self.active_drivers


driver_manager = DriverManager()