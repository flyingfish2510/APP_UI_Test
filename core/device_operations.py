"""
设备操作模块
提供常用的手机操作方法：息屏、锁屏、解锁、按键、网络管理等
支持 Android 设备操作
"""

import os
import time
from datetime import datetime
from typing import Optional, Dict, Any
import allure
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

from core.logger import get_logger
from core.exceptions import (
    ScreenLockError,
    NetworkOperationError,
    KeyEventError
)

logger = get_logger(__name__)


class DeviceOperations:
    """
    设备操作类

    提供常用的手机操作方法，包括：
    - 屏幕操作：锁屏、解锁、息屏、亮屏、亮度调节
    - 按键操作：Home、返回、菜单、电源、音量等
    - 应用管理：启动、关闭、安装、卸载、清除数据
    - 网络操作：WiFi、移动数据、飞行模式
    - 设备信息：电量、屏幕尺寸、设备时间
    - 其他：截图、录屏、剪贴板、GPS定位、摇动
    """

    class AndroidKey:
        """Android 按键码"""
        HOME = 3
        BACK = 4
        VOLUME_UP = 24
        VOLUME_DOWN = 25
        POWER = 26
        MENU = 82
        RECENT_APPS = 187
        ENTER = 66
        DELETE = 67

    def __init__(self, driver):
        """
        初始化设备操作实例

        Args:
            driver: Appium WebDriver 实例
        """
        self.driver: WebDriver = driver
        self.logger = get_logger(self.__class__.__name__)
        self.platform_name = str(driver.capabilities.get('platformName', 'Android')).lower()
        self._key = self.AndroidKey()

    # ==================== 屏幕操作 ====================

    @allure.step("锁定屏幕")
    def lock_screen(self, seconds: int = None) -> bool:
        """锁定屏幕（息屏）"""
        try:
            if seconds:
                self.driver.lock(seconds)
            else:
                self.driver.lock()
            self.logger.info("屏幕已锁定")
            return True
        except WebDriverException as e:
            raise ScreenLockError(message=f"锁定屏幕失败: {str(e)}", operation="lock_screen")

    @allure.step("解锁屏幕")
    def unlock_screen(self) -> bool:
        """解锁屏幕"""
        try:
            if self.is_screen_locked():
                self.driver.unlock()
                self.logger.info("屏幕已解锁")
            else:
                self.logger.info("屏幕已经是解锁状态")
            return True
        except WebDriverException as e:
            raise ScreenLockError(message=f"解锁屏幕失败: {str(e)}", operation="unlock_screen")

    def is_screen_locked(self) -> bool:
        """检查屏幕是否锁定"""
        try:
            current_package = getattr(self.driver, 'current_package', '')
            return current_package == 'com.android.systemui'
        except WebDriverException:
            try:
                result = self.driver.execute_script('mobile: isLocked')
                return bool(result)
            except WebDriverException:
                return False

    @allure.step("唤醒并解锁屏幕")
    def wake_and_unlock(self) -> bool:
        """唤醒并解锁屏幕"""
        try:
            if self.is_screen_locked():
                self.logger.info("屏幕已锁定，正在解锁...")
                self.unlock_screen()
            else:
                self.logger.info("屏幕已处于解锁状态")
            return True
        except Exception as e:
            self.logger.error(f"唤醒解锁失败: {e}")
            return False

    @allure.step("关闭屏幕")
    def turn_screen_off(self) -> bool:
        """关闭屏幕"""
        try:
            self.press_power()
            self.logger.info("屏幕已关闭")
            return True
        except WebDriverException as e:
            raise ScreenLockError(message=f"关闭屏幕失败: {str(e)}", operation="turn_screen_off")

    @allure.step("打开屏幕")
    def turn_screen_on(self) -> bool:
        """打开屏幕"""
        try:
            if self.is_screen_locked():
                self.press_power()
                time.sleep(0.5)
            self.logger.info("屏幕已打开")
            return True
        except WebDriverException as e:
            raise ScreenLockError(message=f"打开屏幕失败: {str(e)}", operation="turn_screen_on")

    @allure.step("唤醒设备")
    def wake_up(self) -> bool:
        """唤醒设备"""
        try:
            self.press_power()
            self.logger.info("设备已唤醒（电源键）")
            return True
        except Exception as e:
            self.logger.error(f"唤醒设备失败: {e}")
            return False

    @allure.step("获取屏幕亮度")
    def get_screen_brightness(self) -> Optional[int]:
        """获取屏幕亮度"""
        try:
            brightness = self.driver.execute_script('mobile: deviceInfo')
            return int(brightness.get('brightness', 0))
        except (WebDriverException, ValueError, TypeError) as e:
            self.logger.error(f"获取屏幕亮度失败: {e}")
            return None

    @allure.step("设置屏幕亮度: {brightness}")
    def set_screen_brightness(self, brightness: int) -> bool:
        """设置屏幕亮度"""
        try:
            brightness = max(0, min(255, brightness))
            self.execute_adb_command('settings', ['put', 'system', 'screen_brightness', str(brightness)])
            self.logger.info(f"屏幕亮度已设置为: {brightness}")
            return True
        except Exception as e:
            self.logger.error(f"设置屏幕亮度失败: {e}")
            return False

    # ==================== 按键操作 ====================

    @allure.step("发送按键: {key_code}")
    def press_key(self, key_code: int, meta_state: int = None) -> bool:
        """发送按键事件"""
        try:
            if meta_state is not None:
                self.driver.press_keycode(key_code, meta_state)
            else:
                self.driver.press_keycode(key_code)
            self.logger.debug(f"按键已发送: {key_code}")
            return True
        except WebDriverException as e:
            raise KeyEventError(message=f"发送按键失败: {str(e)}", operation=f"press_key({key_code})")

    @allure.step("长按按键: {key_code}")
    def long_press_key(self, key_code: int, meta_state: int = None) -> bool:
        """长按按键"""
        try:
            if meta_state is not None:
                self.driver.long_press_keycode(key_code, meta_state)
            else:
                self.driver.long_press_keycode(key_code)
            self.logger.debug(f"长按按键已发送: {key_code}")
            return True
        except WebDriverException as e:
            raise KeyEventError(message=f"长按按键失败: {str(e)}", operation=f"long_press_key({key_code})")

    @allure.step("按Home键")
    def press_home(self) -> bool:
        return self.press_key(self._key.HOME)

    @allure.step("按返回键")
    def press_back(self) -> bool:
        return self.press_key(self._key.BACK)

    @allure.step("按菜单键")
    def press_menu(self) -> bool:
        return self.press_key(self._key.MENU)

    @allure.step("按电源键")
    def press_power(self) -> bool:
        return self.press_key(self._key.POWER)

    @allure.step("按音量+键")
    def press_volume_up(self) -> bool:
        return self.press_key(self._key.VOLUME_UP)

    @allure.step("按音量-键")
    def press_volume_down(self) -> bool:
        return self.press_key(self._key.VOLUME_DOWN)

    @allure.step("按最近应用键")
    def press_recent_apps(self) -> bool:
        return self.press_key(self._key.RECENT_APPS)

    @allure.step("按回车键")
    def press_enter(self) -> bool:
        return self.press_key(self._key.ENTER)

    @allure.step("按删除键")
    def press_delete(self) -> bool:
        return self.press_key(self._key.DELETE)

    @allure.step("返回主屏幕")
    def go_home(self) -> bool:
        """回到主屏幕"""
        try:
            self.driver.execute_script('mobile: pressHome')
            self.logger.info("已回到主屏幕（Appium命令）")
            return True
        except WebDriverException:
            pass
        try:
            self.press_home()
            self.logger.info("已回到主屏幕（按键方式）")
            return True
        except (KeyEventError, WebDriverException):
            pass
        try:
            self.execute_adb_command('input', ['keyevent', '3'])
            self.logger.info("已回到主屏幕（ADB命令）")
            return True
        except Exception as e:
            self.logger.error(f"回到主屏幕失败: {e}")
            return False

    # ==================== 应用管理 ====================

    @allure.step("获取当前包名")
    def get_current_package(self) -> str:
        """获取当前运行的包名"""
        try:
            return str(getattr(self.driver, 'current_package', ''))
        except WebDriverException as e:
            self.logger.error(f"获取当前包名失败: {e}")
            return ""

    @allure.step("获取当前Activity")
    def get_current_activity(self) -> str:
        """获取当前 Activity"""
        try:
            return str(getattr(self.driver, 'current_activity', ''))
        except WebDriverException as e:
            self.logger.error(f"获取当前Activity失败: {e}")
            return ""

    @allure.step("启动应用: {package}")
    def launch_app(self, package: str = None) -> bool:
        """启动应用"""
        try:
            if package:
                self.driver.activate_app(package)
            else:
                package = self.driver.capabilities.get('appPackage')
                if package:
                    self.driver.activate_app(str(package))
                else:
                    self.logger.error("未指定应用包名")
                    return False
            self.logger.info(f"应用已启动: {package}")
            return True
        except WebDriverException as e:
            self.logger.error(f"启动应用失败: {e}")
            return False

    @allure.step("关闭应用: {package}")
    def close_app(self, package: str = None) -> bool:
        """关闭应用"""
        try:
            if package:
                self.driver.terminate_app(package)
            else:
                package = self.driver.capabilities.get('appPackage')
                if package:
                    self.driver.terminate_app(str(package))
            self.logger.info(f"应用已关闭: {package}")
            return True
        except WebDriverException as e:
            self.logger.error(f"关闭应用失败: {e}")
            return False

    def is_app_installed(self, package: str) -> bool:
        """检查应用是否已安装"""
        try:
            return self.driver.is_app_installed(package)
        except WebDriverException as e:
            self.logger.error(f"检查应用安装状态失败: {e}")
            return False

    @allure.step("安装应用: {app_path}")
    def install_app(self, app_path: str, replace: bool = True) -> bool:
        """安装应用"""
        try:
            self.driver.install_app(app_path, replace=replace)
            self.logger.info(f"应用已安装: {app_path}")
            return True
        except WebDriverException as e:
            self.logger.error(f"安装应用失败: {e}")
            return False

    @allure.step("卸载应用: {package}")
    def uninstall_app(self, package: str) -> bool:
        """卸载应用"""
        try:
            self.driver.remove_app(package)
            self.logger.info(f"应用已卸载: {package}")
            return True
        except WebDriverException as e:
            self.logger.error(f"卸载应用失败: {e}")
            return False

    @allure.step("清除应用数据")
    def clear_app_data(self, package: str = None) -> bool:
        """清除应用数据"""
        try:
            if not package:
                package = str(self.driver.capabilities.get('appPackage', ''))
            if package:
                self.driver.execute_script('mobile: shell', {'command': 'pm', 'args': ['clear', package]})
                self.logger.info(f"应用数据已清除: {package}")
                return True
            return False
        except WebDriverException as e:
            self.logger.error(f"清除应用数据失败: {e}")
            return False

    def get_app_state(self, package: str = None) -> int:
        """获取应用状态"""
        try:
            if not package:
                package = str(self.driver.capabilities.get('appPackage', ''))
            if package:
                state = self.driver.query_app_state(package)
                return int(state) if state is not None else -1
            return -1
        except WebDriverException as e:
            self.logger.error(f"获取应用状态失败: {e}")
            return -1

    # ==================== 网络操作 ====================

    @allure.step("开启WiFi")
    def enable_wifi(self) -> bool:
        """开启 WiFi"""
        try:
            if not self.is_wifi_enabled():
                self.driver.toggle_wifi()
            self.logger.info("WiFi已开启")
            return True
        except WebDriverException as e:
            raise NetworkOperationError(message=f"开启WiFi失败: {str(e)}", operation="enable_wifi")

    @allure.step("关闭WiFi")
    def disable_wifi(self) -> bool:
        """关闭 WiFi"""
        try:
            if self.is_wifi_enabled():
                self.driver.toggle_wifi()
            self.logger.info("WiFi已关闭")
            return True
        except WebDriverException as e:
            raise NetworkOperationError(message=f"关闭WiFi失败: {str(e)}", operation="disable_wifi")

    def is_wifi_enabled(self) -> bool:
        """检查 WiFi 是否开启"""
        try:
            result = self.driver.execute_script(
                'mobile: shell', {'command': 'settings', 'args': ['get', 'global', 'wifi_on']}
            )
            return str(result).strip() == '1'
        except WebDriverException as e:
            self.logger.error(f"检查WiFi状态失败: {e}")
            return False

    @allure.step("开启移动数据")
    def enable_mobile_data(self) -> bool:
        """开启移动数据"""
        try:
            if not self.is_mobile_data_enabled():
                toggle_method = getattr(self.driver, 'toggle_data', None)
                if toggle_method:
                    toggle_method()
                else:
                    self.driver.execute_script('mobile: toggleData')
            self.logger.info("移动数据已开启")
            return True
        except WebDriverException as e:
            raise NetworkOperationError(message=f"开启移动数据失败: {str(e)}", operation="enable_mobile_data")

    @allure.step("关闭移动数据")
    def disable_mobile_data(self) -> bool:
        """关闭移动数据"""
        try:
            if self.is_mobile_data_enabled():
                toggle_method = getattr(self.driver, 'toggle_data', None)
                if toggle_method:
                    toggle_method()
                else:
                    self.driver.execute_script('mobile: toggleData')
            self.logger.info("移动数据已关闭")
            return True
        except WebDriverException as e:
            raise NetworkOperationError(message=f"关闭移动数据失败: {str(e)}", operation="disable_mobile_data")

    def is_mobile_data_enabled(self) -> bool:
        """检查移动数据是否开启"""
        try:
            result = self.driver.execute_script(
                'mobile: shell', {'command': 'settings', 'args': ['get', 'global', 'mobile_data']}
            )
            return str(result).strip() == '1'
        except WebDriverException as e:
            self.logger.error(f"检查移动数据状态失败: {e}")
            return False

    @allure.step("开启飞行模式")
    def enable_airplane_mode(self) -> bool:
        """开启飞行模式"""
        try:
            if self.is_wifi_enabled():
                self.disable_wifi()
            if self.is_mobile_data_enabled():
                self.disable_mobile_data()
            self.driver.execute_script(
                'mobile: shell', {'command': 'settings', 'args': ['put', 'global', 'airplane_mode_on', '1']}
            )
            self.driver.execute_script(
                'mobile: shell', {'command': 'am', 'args': ['broadcast', '-a', 'android.intent.action.AIRPLANE_MODE']}
            )
            self.logger.info("飞行模式已开启")
            return True
        except WebDriverException as e:
            raise NetworkOperationError(message=f"开启飞行模式失败: {str(e)}", operation="enable_airplane_mode")

    @allure.step("关闭飞行模式")
    def disable_airplane_mode(self) -> bool:
        """关闭飞行模式"""
        try:
            self.driver.execute_script(
                'mobile: shell', {'command': 'settings', 'args': ['put', 'global', 'airplane_mode_on', '0']}
            )
            self.driver.execute_script(
                'mobile: shell', {'command': 'am', 'args': ['broadcast', '-a', 'android.intent.action.AIRPLANE_MODE']}
            )
            self.logger.info("飞行模式已关闭")
            return True
        except WebDriverException as e:
            raise NetworkOperationError(message=f"关闭飞行模式失败: {str(e)}", operation="disable_airplane_mode")

    @allure.step("设置网络连接类型: {connection_type}")
    def set_network_connection(self, connection_type: int) -> bool:
        """设置网络连接类型"""
        try:
            self.driver.set_network_connection(connection_type)
            self.logger.info(f"网络连接类型已设置为: {connection_type}")
            return True
        except WebDriverException as e:
            self.logger.error(f"设置网络连接类型失败: {e}")
            return False

    def get_network_connection(self) -> int:
        """获取当前网络连接类型"""
        try:
            return int(self.driver.network_connection)
        except (WebDriverException, ValueError, TypeError) as e:
            self.logger.error(f"获取网络连接类型失败: {e}")
            return -1

    # ==================== 通知 ====================

    @allure.step("打开通知栏")
    def open_notifications(self) -> bool:
        """打开通知栏"""
        try:
            self.driver.open_notifications()
            self.logger.info("通知栏已打开")
            return True
        except WebDriverException as e:
            self.logger.error(f"打开通知栏失败: {e}")
            return False

    @allure.step("关闭通知栏")
    def close_notifications(self) -> bool:
        """关闭通知栏"""
        try:
            self.press_back()
            self.logger.info("通知栏已关闭")
            return True
        except (KeyEventError, WebDriverException) as e:
            self.logger.error(f"关闭通知栏失败: {e}")
            return False

    # ==================== 设备信息 ====================

    def get_device_time(self) -> str:
        """获取设备当前时间"""
        try:
            return str(self.driver.device_time)
        except WebDriverException as e:
            self.logger.error(f"获取设备时间失败: {e}")
            return ""

    @allure.step("获取设备信息")
    def get_device_info(self) -> Dict[str, Any]:
        """获取设备基本信息"""
        info: Dict[str, Any] = {}
        try:
            capabilities = self.driver.capabilities
            info['deviceName'] = str(capabilities.get('deviceName', 'Unknown'))
            info['platformVersion'] = str(capabilities.get('platformVersion', 'Unknown'))
            info['udid'] = str(capabilities.get('udid', 'Unknown'))
            info['automationName'] = str(capabilities.get('automationName', 'Unknown'))
            return info
        except WebDriverException as e:
            self.logger.error(f"获取设备信息失败: {e}")
            return info

    @allure.step("获取电池信息")
    def get_battery_info(self) -> Dict[str, Any]:
        """获取电池信息"""
        info: Dict[str, Any] = {}
        try:
            result = self.driver.execute_script('mobile: shell', {'command': 'dumpsys', 'args': ['battery']})
            for line in str(result).split('\n'):
                line = line.strip()
                if 'level:' in line:
                    info['level'] = int(line.split(':')[1].strip())
                elif 'status:' in line:
                    status_map = {'1': 'unknown', '2': 'charging', '3': 'discharging', '4': 'not_charging', '5': 'full'}
                    info['state'] = status_map.get(line.split(':')[1].strip(), 'unknown')
            return info
        except WebDriverException as e:
            self.logger.error(f"获取电池信息失败: {e}")
            return info

    def get_battery_level(self) -> Optional[int]:
        """获取电池电量百分比"""
        return self.get_battery_info().get('level')

    def get_window_size(self) -> Dict[str, int]:
        """获取窗口尺寸"""
        try:
            size = self.driver.get_window_size()
            return {'width': int(size.get('width', 0)), 'height': int(size.get('height', 0))}
        except (WebDriverException, ValueError, TypeError) as e:
            self.logger.error(f"获取窗口尺寸失败: {e}")
            return {'width': 0, 'height': 0}

    # ==================== 截图和录制 ====================

    @allure.step("截图保存")
    def take_screenshot_and_save(self, filename: str = None) -> Optional[str]:
        """截图并保存到本地"""
        try:
            screenshot_dir = './screenshots'
            os.makedirs(screenshot_dir, exist_ok=True)
            if not filename:
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            filepath = os.path.join(screenshot_dir, f"{filename}.png")
            self.driver.save_screenshot(filepath)
            self.logger.info(f"截图已保存: {filepath}")
            return filepath
        except (WebDriverException, OSError) as e:
            self.logger.error(f"截图保存失败: {e}")
            return None

    @allure.step("开始屏幕录制")
    def start_recording_screen(self, **options) -> bool:
        """开始录制屏幕"""
        try:
            self.driver.start_recording_screen(**options)
            self.logger.info("屏幕录制已开始")
            return True
        except WebDriverException as e:
            self.logger.error(f"开始屏幕录制失败: {e}")
            return False

    @allure.step("停止屏幕录制")
    def stop_recording_screen(self) -> Optional[str]:
        """停止录制屏幕"""
        try:
            video = self.driver.stop_recording_screen()
            self.logger.info("屏幕录制已停止")
            return str(video) if video else None
        except WebDriverException as e:
            self.logger.error(f"停止屏幕录制失败: {e}")
            return None

    # ==================== 其他 ====================

    @allure.step("设置剪贴板文本")
    def set_clipboard_text(self, text: str) -> bool:
        """设置剪贴板文本"""
        try:
            self.driver.set_clipboard_text(text)
            return True
        except WebDriverException as e:
            self.logger.error(f"设置剪贴板文本失败: {e}")
            return False

    @allure.step("获取剪贴板文本")
    def get_clipboard_text(self) -> str:
        """获取剪贴板文本"""
        try:
            return str(self.driver.get_clipboard_text())
        except WebDriverException as e:
            self.logger.error(f"获取剪贴板文本失败: {e}")
            return ""

    @allure.step("摇动设备")
    def shake(self) -> bool:
        """模拟摇动设备"""
        try:
            self.driver.shake()
            self.logger.info("设备已摇动")
            return True
        except WebDriverException as e:
            self.logger.error(f"摇动设备失败: {e}")
            return False

    @allure.step("设置GPS位置: ({latitude}, {longitude})")
    def set_location(self, latitude: float, longitude: float, altitude: float = 0) -> bool:
        """设置 GPS 位置"""
        try:
            self.driver.set_location(latitude, longitude, altitude)
            self.logger.info(f"GPS位置已设置: ({latitude}, {longitude})")
            return True
        except WebDriverException as e:
            self.logger.error(f"设置GPS位置失败: {e}")
            return False

    def execute_adb_command(self, command: str, args: list = None) -> Optional[str]:
        """执行 ADB 命令"""
        try:
            params: Dict[str, Any] = {'command': command}
            if args:
                params['args'] = args
            result = self.driver.execute_script('mobile: shell', params)
            return str(result) if result else None
        except WebDriverException as e:
            self.logger.error(f"执行ADB命令失败: {e}")
            return None


def create_device_operations(driver) -> DeviceOperations:
    """创建设备操作实例的便捷函数"""
    return DeviceOperations(driver)