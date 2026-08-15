"""
自定义异常模块
提供框架级别的异常类，用于更精确的异常处理和错误追踪
"""

from typing import Tuple, Any, Dict
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementNotVisibleException,
    WebDriverException
)


# ==================== 基础异常 ====================

class MobileAutoTestException(Exception):
    """移动端自动化测试框架基础异常类"""

    def __init__(self, message: str = None, error_code: str = None,
                 details: Dict = None):
        self.message = message or "移动端自动化测试异常"
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.error_code}] {self.message}"

    def to_dict(self) -> Dict:
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'exception_type': self.__class__.__name__
        }


# ==================== 配置异常 ====================

class ConfigException(MobileAutoTestException):
    """配置相关异常"""

    def __init__(self, message: str = None, config_key: str = None,
                 config_file: str = None):
        super().__init__(
            message=message or "配置文件异常",
            error_code="CONFIG_ERROR",
            details={'config_key': config_key, 'config_file': config_file}
        )


class ConfigFileNotFoundError(ConfigException):
    """配置文件未找到异常"""

    def __init__(self, file_path: str = None):
        super().__init__(
            message=f"配置文件未找到: {file_path}",
            config_file=file_path
        )
        self.error_code = "CONFIG_FILE_NOT_FOUND"
        self.file_path = file_path


class ConfigKeyNotFoundError(ConfigException):
    """配置键未找到异常"""

    def __init__(self, key: str = None, file_path: str = None):
        super().__init__(
            message=f"配置键未找到: {key} (文件: {file_path})",
            config_key=key,
            config_file=file_path
        )
        self.error_code = "CONFIG_KEY_NOT_FOUND"
        self.key = key


# ==================== 设备异常 ====================

class DeviceException(MobileAutoTestException):
    """设备相关异常"""

    def __init__(self, message: str = None, device_name: str = None,
                 udid: str = None, device_index: int = None):
        super().__init__(
            message=message or "设备异常",
            error_code="DEVICE_ERROR",
            details={
                'device_name': device_name,
                'udid': udid,
                'device_index': device_index
            }
        )


class DeviceNotFoundError(DeviceException):
    """设备未找到异常"""

    def __init__(self, device_name: str = None, udid: str = None,
                 device_index: int = None, message: str = None):
        identifier = device_name or udid or f"索引:{device_index}"
        super().__init__(
            message=message or f"设备未找到: {identifier}",
            device_name=device_name,
            udid=udid,
            device_index=device_index
        )
        self.error_code = "DEVICE_NOT_FOUND"


class DeviceConnectionError(DeviceException):
    """设备连接异常"""

    def __init__(self, device_name: str = None, udid: str = None,
                 original_error: str = None):
        super().__init__(
            message=f"设备连接失败: {device_name or udid} - {original_error}",
            device_name=device_name,
            udid=udid
        )
        self.error_code = "DEVICE_CONNECTION_ERROR"
        self.original_error = original_error


class DeviceOfflineError(DeviceException):
    """设备离线异常"""

    def __init__(self, device_name: str = None, udid: str = None):
        super().__init__(
            message=f"设备离线: {device_name or udid}",
            device_name=device_name,
            udid=udid
        )
        self.error_code = "DEVICE_OFFLINE"


class DeviceBusyError(DeviceException):
    """设备忙碌异常"""

    def __init__(self, device_name: str = None, udid: str = None):
        super().__init__(
            message=f"设备忙碌: {device_name or udid}",
            device_name=device_name,
            udid=udid
        )
        self.error_code = "DEVICE_BUSY"


# ==================== 设备操作异常 ====================

class DeviceOperationError(MobileAutoTestException):
    """设备操作异常"""

    def __init__(self, message: str = None, operation: str = None):
        super().__init__(
            message=message or "设备操作异常",
            error_code="DEVICE_OPERATION_ERROR",
            details={'operation': operation}
        )


class ScreenLockError(DeviceOperationError):
    """屏幕锁定/解锁异常"""

    def __init__(self, message: str = None, operation: str = None):
        super().__init__(
            message=message or "屏幕锁定/解锁异常",
            operation=operation
        )
        self.error_code = "SCREEN_LOCK_ERROR"


class NetworkOperationError(DeviceOperationError):
    """网络操作异常"""

    def __init__(self, message: str = None, operation: str = None):
        super().__init__(
            message=message or "网络操作异常",
            operation=operation
        )
        self.error_code = "NETWORK_OPERATION_ERROR"


class KeyEventError(DeviceOperationError):
    """按键事件异常"""

    def __init__(self, message: str = None, operation: str = None):
        super().__init__(
            message=message or "按键事件异常",
            operation=operation
        )
        self.error_code = "KEY_EVENT_ERROR"


class BatteryOperationError(DeviceOperationError):
    """电池操作异常"""

    def __init__(self, message: str = None, operation: str = None):
        super().__init__(
            message=message or "电池操作异常",
            operation=operation
        )
        self.error_code = "BATTERY_OPERATION_ERROR"


# ==================== Driver异常 ====================

class DriverException(MobileAutoTestException):
    """Driver相关异常"""

    def __init__(self, message: str = None, device_name: str = None,
                 session_id: str = None):
        super().__init__(
            message=message or "Driver异常",
            error_code="DRIVER_ERROR",
            details={'device_name': device_name, 'session_id': session_id}
        )


class DriverCreationError(DriverException):
    """Driver创建失败异常"""

    def __init__(self, device_name: str = None, original_error: str = None):
        super().__init__(
            message=f"Driver创建失败: {device_name} - {original_error}",
            device_name=device_name
        )
        self.error_code = "DRIVER_CREATION_ERROR"
        self.original_error = original_error


class DriverNotInitializedError(DriverException):
    """Driver未初始化异常"""

    def __init__(self, message: str = None, device_name: str = None):
        super().__init__(
            message=message or f"Driver未初始化: {device_name or '未知设备'}",
            device_name=device_name
        )
        self.error_code = "DRIVER_NOT_INITIALIZED"


class DriverSessionExpiredError(DriverException):
    """Driver会话过期异常"""

    def __init__(self, session_id: str = None, device_name: str = None):
        super().__init__(
            message=f"Driver会话已过期: {session_id}",
            device_name=device_name,
            session_id=session_id
        )
        self.error_code = "DRIVER_SESSION_EXPIRED"
        self.session_id = session_id


# ==================== 元素异常 ====================

class ElementException(MobileAutoTestException):
    """元素相关异常"""

    def __init__(self, message: str = None, locator: Tuple[str, str] = None,
                 element_name: str = None, page_name: str = None):
        super().__init__(
            message=message or "元素操作异常",
            error_code="ELEMENT_ERROR",
            details={
                'locator': str(locator) if locator else None,
                'element_name': element_name,
                'page_name': page_name
            }
        )


class ElementNotFoundError(ElementException):
    """元素未找到异常"""

    def __init__(self, locator: Tuple[str, str] = None, element_name: str = None,
                 timeout: int = None, page_name: str = None):
        super().__init__(
            message=f"元素未找到: {element_name or locator} (超时:{timeout}s)",
            locator=locator,
            element_name=element_name,
            page_name=page_name
        )
        self.error_code = "ELEMENT_NOT_FOUND"
        self.timeout = timeout


class ElementNotVisibleError(ElementException):
    """元素不可见异常"""

    def __init__(self, locator: Tuple[str, str] = None, element_name: str = None,
                 page_name: str = None):
        super().__init__(
            message=f"元素不可见: {element_name or locator}",
            locator=locator,
            element_name=element_name,
            page_name=page_name
        )
        self.error_code = "ELEMENT_NOT_VISIBLE"


class ElementNotClickableError(ElementException):
    """元素不可点击异常"""

    def __init__(self, locator: Tuple[str, str] = None, element_name: str = None,
                 page_name: str = None, reason: str = None):
        super().__init__(
            message=f"元素不可点击: {element_name or locator} - {reason}",
            locator=locator,
            element_name=element_name,
            page_name=page_name
        )
        self.error_code = "ELEMENT_NOT_CLICKABLE"
        self.reason = reason


class ElementStaleError(ElementException):
    """元素过时异常"""

    def __init__(self, locator: Tuple[str, str] = None, element_name: str = None,
                 page_name: str = None):
        super().__init__(
            message=f"元素已过时: {element_name or locator}",
            locator=locator,
            element_name=element_name,
            page_name=page_name
        )
        self.error_code = "ELEMENT_STALE"


# ==================== 页面异常 ====================

class PageException(MobileAutoTestException):
    """页面相关异常"""

    def __init__(self, message: str = None, page_name: str = None,
                 current_activity: str = None):
        super().__init__(
            message=message or "页面异常",
            error_code="PAGE_ERROR",
            details={'page_name': page_name, 'current_activity': current_activity}
        )


class PageLoadTimeoutError(PageException):
    """页面加载超时异常"""

    def __init__(self, page_name: str = None, timeout: int = None,
                 expected_element: str = None):
        super().__init__(
            message=f"页面加载超时: {page_name} (超时:{timeout}s, 期望元素:{expected_element})",
            page_name=page_name
        )
        self.error_code = "PAGE_LOAD_TIMEOUT"
        self.timeout = timeout
        self.expected_element = expected_element


class PageNotLoadedError(PageException):
    """页面未加载异常"""

    def __init__(self, page_name: str = None, reason: str = None):
        super().__init__(
            message=f"页面未加载: {page_name} - {reason}",
            page_name=page_name
        )
        self.error_code = "PAGE_NOT_LOADED"
        self.reason = reason


class PageNavigationError(PageException):
    """页面导航异常"""

    def __init__(self, from_page: str = None, to_page: str = None,
                 reason: str = None):
        super().__init__(
            message=f"页面导航失败: {from_page} -> {to_page} - {reason}",
            page_name=to_page
        )
        self.error_code = "PAGE_NAVIGATION_ERROR"
        self.from_page = from_page
        self.to_page = to_page


# ==================== 应用异常 ====================

class AppException(MobileAutoTestException):
    """应用相关异常"""

    def __init__(self, message: str = None, app_package: str = None,
                 app_activity: str = None):
        super().__init__(
            message=message or "应用异常",
            error_code="APP_ERROR",
            details={'app_package': app_package, 'app_activity': app_activity}
        )


class AppNotInstalledError(AppException):
    """应用未安装异常"""

    def __init__(self, app_package: str = None):
        super().__init__(
            message=f"应用未安装: {app_package}",
            app_package=app_package
        )
        self.error_code = "APP_NOT_INSTALLED"


class AppLaunchError(AppException):
    """应用启动失败异常"""

    def __init__(self, app_package: str = None, reason: str = None):
        super().__init__(
            message=f"应用启动失败: {app_package} - {reason}",
            app_package=app_package
        )
        self.error_code = "APP_LAUNCH_ERROR"
        self.reason = reason


class AppCrashError(AppException):
    """应用崩溃异常"""

    def __init__(self, app_package: str = None, crash_log: str = None):
        super().__init__(
            message=f"应用崩溃: {app_package}",
            app_package=app_package
        )
        self.error_code = "APP_CRASH"
        self.crash_log = crash_log


# ==================== Appium服务异常 ====================

class AppiumServiceException(MobileAutoTestException):
    """Appium服务相关异常"""

    def __init__(self, message: str = None, service_url: str = None):
        super().__init__(
            message=message or "Appium服务异常",
            error_code="APPIUM_SERVICE_ERROR",
            details={'service_url': service_url}
        )


class AppiumServiceStartError(AppiumServiceException):
    """Appium服务启动失败异常"""

    def __init__(self, service_url: str = None, reason: str = None):
        super().__init__(
            message=f"Appium服务启动失败: {service_url} - {reason}",
            service_url=service_url
        )
        self.error_code = "APPIUM_SERVICE_START_ERROR"
        self.reason = reason


class AppiumConnectionError(AppiumServiceException):
    """Appium连接失败异常"""

    def __init__(self, service_url: str = None, reason: str = None):
        super().__init__(
            message=f"Appium连接失败: {service_url} - {reason}",
            service_url=service_url
        )
        self.error_code = "APPIUM_CONNECTION_ERROR"
        self.reason = reason


# ==================== 测试数据异常 ====================

class TestDataException(MobileAutoTestException):
    """测试数据相关异常"""

    def __init__(self, message: str = None, data_key: str = None,
                 data_file: str = None):
        super().__init__(
            message=message or "测试数据异常",
            error_code="TEST_DATA_ERROR",
            details={'data_key': data_key, 'data_file': data_file}
        )


class TestDataNotFoundError(TestDataException):
    """测试数据未找到异常"""

    def __init__(self, data_key: str = None, data_file: str = None):
        super().__init__(
            message=f"测试数据未找到: {data_key} (文件: {data_file})",
            data_key=data_key,
            data_file=data_file
        )
        self.error_code = "TEST_DATA_NOT_FOUND"


class TestDataFormatError(TestDataException):
    """测试数据格式错误异常"""

    def __init__(self, data_key: str = None, expected_format: str = None,
                 actual_value: Any = None):
        super().__init__(
            message=f"测试数据格式错误: {data_key}, 期望:{expected_format}, 实际:{actual_value}",
            data_key=data_key
        )
        self.error_code = "TEST_DATA_FORMAT_ERROR"
        self.expected_format = expected_format
        self.actual_value = actual_value


# ==================== 截图异常 ====================

class ScreenshotException(MobileAutoTestException):
    """截图相关异常"""

    def __init__(self, message: str = None, file_path: str = None):
        super().__init__(
            message=message or "截图异常",
            error_code="SCREENSHOT_ERROR",
            details={'file_path': file_path}
        )


class ScreenshotSaveError(ScreenshotException):
    """截图保存失败异常"""

    def __init__(self, file_path: str = None, reason: str = None):
        super().__init__(
            message=f"截图保存失败: {file_path} - {reason}",
            file_path=file_path
        )
        self.error_code = "SCREENSHOT_SAVE_ERROR"
        self.reason = reason


# ==================== 平台异常 ====================

class PlatformException(MobileAutoTestException):
    """平台相关异常"""

    def __init__(self, message: str = None, platform: str = None):
        super().__init__(
            message=message or "平台异常",
            error_code="PLATFORM_ERROR",
            details={'platform': platform}
        )


class UnsupportedPlatformError(PlatformException):
    """不支持的平台异常"""

    def __init__(self, platform: str = None, operation: str = None):
        super().__init__(
            message=f"不支持的平台操作: {platform} - {operation}",
            platform=platform
        )
        self.error_code = "UNSUPPORTED_PLATFORM"
        self.operation = operation


# ==================== Docker异常 ====================

class DockerException(MobileAutoTestException):
    """Docker相关异常"""

    def __init__(self, message: str = None, container_id: str = None):
        super().__init__(
            message=message or "Docker环境异常",
            error_code="DOCKER_ERROR",
            details={'container_id': container_id}
        )


class DockerConnectionError(DockerException):
    """Docker连接异常"""

    def __init__(self, container_id: str = None, reason: str = None):
        super().__init__(
            message=f"Docker连接失败: {container_id} - {reason}",
            container_id=container_id
        )
        self.error_code = "DOCKER_CONNECTION_ERROR"
        self.reason = reason


# ==================== 工具函数 ====================

def handle_exceptions(default_error_code: str = "UNKNOWN_ERROR",
                      reraise: bool = True):
    """
    异常处理装饰器
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except MobileAutoTestException:
                if reraise:
                    raise
                return None
            except TimeoutException as e:
                if reraise:
                    raise MobileAutoTestException(
                        message=f"操作超时: {str(e)}",
                        error_code="TIMEOUT_ERROR"
                    ) from e
                return None
            except NoSuchElementException as e:
                if reraise:
                    raise MobileAutoTestException(
                        message=f"元素不存在: {str(e)}",
                        error_code="ELEMENT_NOT_FOUND"
                    ) from e
                return None
            except StaleElementReferenceException as e:
                if reraise:
                    raise MobileAutoTestException(
                        message=f"元素过时: {str(e)}",
                        error_code="ELEMENT_STALE"
                    ) from e
                return None
            except ElementNotVisibleException as e:
                if reraise:
                    raise MobileAutoTestException(
                        message=f"元素不可见: {str(e)}",
                        error_code="ELEMENT_NOT_VISIBLE"
                    ) from e
                return None
            except WebDriverException as e:
                if reraise:
                    raise MobileAutoTestException(
                        message=f"WebDriver异常: {str(e)}",
                        error_code="DRIVER_ERROR"
                    ) from e
                return None
            except Exception as e:
                if reraise:
                    raise MobileAutoTestException(
                        message=str(e),
                        error_code=default_error_code
                    ) from e
                return None
        return wrapper
    return decorator


def exception_to_dict(exception: Exception) -> Dict:
    """
    将异常转换为字典格式
    """
    if isinstance(exception, MobileAutoTestException):
        return exception.to_dict()
    else:
        import traceback
        return {
            'error_code': 'UNKNOWN_ERROR',
            'message': str(exception),
            'details': {
                'exception_type': type(exception).__name__,
                'traceback': traceback.format_exc()
            },
            'exception_type': type(exception).__name__
        }