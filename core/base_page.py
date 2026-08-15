"""
Page Object基类（集成自定义异常版本和设备操作）
所有Page Object类都应继承此类
提供统一的操作方法和异常处理
"""

import os
import time
import functools
from datetime import datetime
from typing import Optional, Tuple, List
import allure
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementNotVisibleException,
    WebDriverException
)
from core.logger import get_logger
from core.exceptions import (
    ElementNotFoundError,
    ElementNotVisibleError,
    ElementNotClickableError,
    ElementStaleError,
    ScreenshotSaveError,
    handle_exceptions
)
from core.exception_handler import (
    global_exception_handler,
    global_retry_handler
)
from core.device_operations import DeviceOperations

logger = get_logger(__name__)


def log_step(step_name: str):
    """步骤装饰器，同时在日志和Allure报告中体现"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.logger.info(f"步骤：{step_name}")
            with allure.step(step_name):
                result = func(self, *args, **kwargs)
            return result
        return wrapper
    return decorator


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """元素操作重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(self, *args, **kwargs)
                except (ElementStaleError, ElementNotClickableError, WebDriverException) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        self.logger.warning(
                            f"操作失败，重试 {attempt + 1}/{max_attempts - 1}: "
                            f"{func.__name__} - {str(e)}"
                        )
                        time.sleep(delay * (attempt + 1))
                    else:
                        self.logger.error(f"操作最终失败: {func.__name__}")
                        raise
            raise last_exception
        return wrapper
    return decorator


def method_timeout(seconds: int):
    """方法级超时装饰器"""
    import threading

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = []
            exception = []

            def target():
                try:
                    result.append(func(self, *args, **kwargs))
                except Exception as e:
                    exception.append(e)

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)

            if thread.is_alive():
                self.logger.error(f"方法 {func.__name__} 执行超时 ({seconds}s)")
                self._take_screenshot(f"timeout_{func.__name__}")
                raise TimeoutError(f"方法 {func.__name__} 执行超时 ({seconds}s)")

            if exception:
                raise exception[0]

            return result[0] if result else None
        return wrapper
    return decorator


class BasePage:
    """页面基类"""

    def __init__(self, driver, config_path: str = "config/config.yaml"):
        self.driver = driver
        self.config = self._load_config(config_path)
        self.default_timeout = self.config.get('timeout', {}).get('explicit_wait', 20)
        self.screenshot_config = self.config.get('screenshot', {})
        self.logger = get_logger(self.__class__.__name__)
        self.exception_handler = global_exception_handler
        self.retry_handler = global_retry_handler
        self._device_ops = None

    @property
    def device(self) -> DeviceOperations:
        if self._device_ops is None:
            self._device_ops = DeviceOperations(self.driver)
        return self._device_ops

    @property
    def assert_that(self):
        from core.assertions import Assertions
        return Assertions(self)

    @staticmethod
    def _load_config(config_path: str) -> dict:
        import yaml
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except (FileNotFoundError, yaml.YAMLError):
            logger.error(f"加载配置文件失败: {config_path}")
            return {}

    @handle_exceptions(default_error_code="ELEMENT_FIND_ERROR")
    @allure.step("查找元素: {locator}")
    def find_element(self, locator: Tuple[str, str], wait_timeout: Optional[int] = None,
                     condition=EC.visibility_of_element_located) -> WebElement:
        """查找单个元素，使用显式等待"""
        wait_timeout = wait_timeout or self.default_timeout
        try:
            element = WebDriverWait(self.driver, wait_timeout).until(condition(locator))
            self.logger.debug(f"成功找到元素: {locator}")
            return element
        except TimeoutException:
            self.logger.error(f"查找元素超时 [{wait_timeout}s]: {locator}")
            self._take_screenshot(f"timeout_{locator[1].replace('/', '_')}")
            raise ElementNotFoundError(locator=locator, timeout=wait_timeout, page_name=self.__class__.__name__)
        except ElementNotVisibleException:
            self.logger.error(f"元素不可见: {locator}")
            self._take_screenshot(f"not_visible_{locator[1].replace('/', '_')}")
            raise ElementNotVisibleError(locator=locator, page_name=self.__class__.__name__)

    @allure.step("查找多个元素: {locator}")
    def find_elements(self, locator: Tuple[str, str], wait_timeout: Optional[int] = None) -> List[WebElement]:
        """查找多个元素"""
        wait_timeout = wait_timeout or self.default_timeout
        try:
            elements = WebDriverWait(self.driver, wait_timeout).until(EC.presence_of_all_elements_located(locator))
            self.logger.debug(f"成功找到 {len(elements)} 个元素")
            return elements
        except TimeoutException:
            self.logger.warning(f"查找多个元素超时 [{wait_timeout}s]: {locator}")
            return []
        except WebDriverException as e:
            self.logger.error(f"查找多个元素异常: {e}")
            return []

    @retry_on_failure(max_attempts=3, delay=1.0)
    @handle_exceptions(default_error_code="ELEMENT_CLICK_ERROR")
    @allure.step("点击元素: {locator}")
    def click(self, locator: Tuple[str, str], wait_timeout: Optional[int] = None) -> bool:
        """点击元素"""
        wait_timeout = wait_timeout or self.default_timeout
        try:
            element = WebDriverWait(self.driver, wait_timeout).until(EC.element_to_be_clickable(locator))
            element.click()
            self.logger.info(f"成功点击元素: {locator}")
            return True
        except TimeoutException:
            self.logger.error(f"元素不可点击: {locator}")
            self._take_screenshot(f"click_failed_{locator[1].replace('/', '_')}")
            raise ElementNotClickableError(locator=locator, page_name=self.__class__.__name__, reason="元素在超时时间内不可点击")
        except StaleElementReferenceException:
            self.logger.warning(f"元素过时，尝试重新查找: {locator}")
            self._take_screenshot(f"stale_{locator[1].replace('/', '_')}")
            try:
                element = WebDriverWait(self.driver, wait_timeout).until(EC.element_to_be_clickable(locator))
                element.click()
                self.logger.info(f"重试点击成功: {locator}")
                return True
            except (TimeoutException, StaleElementReferenceException):
                raise ElementStaleError(locator=locator, page_name=self.__class__.__name__)

    @retry_on_failure(max_attempts=3, delay=0.5)
    @allure.step("输入文本到元素: {locator}")
    def input_text(self, locator: Tuple[str, str], text: str,
                   clear_first: bool = True, wait_timeout: Optional[int] = None) -> bool:
        """输入文本"""
        wait_timeout = wait_timeout or self.default_timeout
        try:
            element = self.find_element(locator, wait_timeout)
            if clear_first:
                element.clear()
            element.send_keys(text)
            self.logger.info(f"成功输入文本到元素: {locator}")
            return True
        except ElementNotFoundError:
            self.logger.error(f"输入文本失败，元素未找到: {locator}")
            return False
        except WebDriverException as e:
            self.logger.error(f"输入文本失败: {e}")
            self._take_screenshot(f"input_failed_{locator[1].replace('/', '_')}")
            return False

    @retry_on_failure(max_attempts=2, delay=0.5)
    @allure.step("获取元素文本: {locator}")
    def get_text(self, locator: Tuple[str, str], wait_timeout: Optional[int] = None) -> str:
        """获取元素文本"""
        wait_timeout = wait_timeout or self.default_timeout
        try:
            element = self.find_element(locator, wait_timeout)
            text = element.text
            self.logger.debug(f"获取元素文本: {text}")
            return text
        except ElementNotFoundError:
            self.logger.warning(f"获取文本失败，元素未找到: {locator}")
            return ""
        except WebDriverException as e:
            self.logger.error(f"获取文本失败: {e}")
            return ""

    @retry_on_failure(max_attempts=2, delay=0.5)
    @allure.step("获取元素属性 {attribute}: {locator}")
    def get_attribute(self, locator: Tuple[str, str], attribute: str,
                      wait_timeout: Optional[int] = None) -> str:
        """获取元素属性"""
        wait_timeout = wait_timeout or self.default_timeout
        try:
            element = self.find_element(locator, wait_timeout)
            value = element.get_attribute(attribute)
            self.logger.debug(f"获取元素属性 {attribute}: {value}")
            return value or ""
        except ElementNotFoundError:
            self.logger.warning(f"获取属性失败，元素未找到: {locator}")
            return ""
        except WebDriverException as e:
            self.logger.error(f"获取属性失败: {e}")
            return ""

    def is_element_present(self, locator: Tuple[str, str], wait_timeout: Optional[int] = None) -> bool:
        """判断元素是否存在"""
        wait_timeout = wait_timeout or min(self.default_timeout, 5)
        try:
            self.find_element(locator, wait_timeout, EC.presence_of_element_located)
            return True
        except (ElementNotFoundError, WebDriverException):
            return False

    def is_element_visible(self, locator: Tuple[str, str], wait_timeout: Optional[int] = None) -> bool:
        """判断元素是否可见"""
        wait_timeout = wait_timeout or min(self.default_timeout, 5)
        try:
            self.find_element(locator, wait_timeout, EC.visibility_of_element_located)
            return True
        except (ElementNotFoundError, ElementNotVisibleError, WebDriverException):
            return False

    @allure.step("等待元素消失: {locator}")
    def wait_for_element_disappear(self, locator: Tuple[str, str],
                                   wait_timeout: Optional[int] = None) -> bool:
        """等待元素消失"""
        wait_timeout = wait_timeout or self.default_timeout
        try:
            WebDriverWait(self.driver, wait_timeout).until(EC.invisibility_of_element_located(locator))
            self.logger.info(f"元素已消失: {locator}")
            return True
        except TimeoutException:
            self.logger.warning(f"等待元素消失超时: {locator}")
            return False
        except WebDriverException as e:
            self.logger.error(f"等待元素消失异常: {e}")
            return False

    @allure.step("滚动查找元素: {locator}")
    def scroll_to_element(self, locator: Tuple[str, str], max_scrolls: int = 10) -> bool:
        """滚动查找元素"""
        for i in range(max_scrolls):
            if self.is_element_visible(locator, wait_timeout=2):
                self.logger.info(f"滚动找到元素: {locator}")
                return True
            size = self.driver.get_window_size()
            start_x = size['width'] // 2
            start_y = int(size['height'] * 0.8)
            end_y = int(size['height'] * 0.2)
            self.driver.swipe(start_x, start_y, start_x, end_y, 800)
            self.logger.debug(f"执行第 {i+1} 次滚动")
        self.logger.warning(f"滚动 {max_scrolls} 次后未找到元素: {locator}")
        return False

    @allure.step("向上滑动")
    def swipe_up(self, duration: int = 800):
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = int(size['height'] * 0.8)
        end_y = int(size['height'] * 0.2)
        self.driver.swipe(start_x, start_y, start_x, end_y, duration)
        self.logger.debug("执行向上滑动")

    @allure.step("向下滑动")
    def swipe_down(self, duration: int = 800):
        size = self.driver.get_window_size()
        start_x = size['width'] // 2
        start_y = int(size['height'] * 0.2)
        end_y = int(size['height'] * 0.8)
        self.driver.swipe(start_x, start_y, start_x, end_y, duration)
        self.logger.debug("执行向下滑动")

    @allure.step("向左滑动")
    def swipe_left(self, duration: int = 800):
        size = self.driver.get_window_size()
        start_x = int(size['width'] * 0.8)
        start_y = size['height'] // 2
        end_x = int(size['width'] * 0.2)
        self.driver.swipe(start_x, start_y, end_x, start_y, duration)
        self.logger.debug("执行向左滑动")

    @allure.step("向右滑动")
    def swipe_right(self, duration: int = 800):
        size = self.driver.get_window_size()
        start_x = int(size['width'] * 0.2)
        start_y = size['height'] // 2
        end_x = int(size['width'] * 0.8)
        self.driver.swipe(start_x, start_y, end_x, start_y, duration)
        self.logger.debug("执行向右滑动")

    @allure.step("返回上一页")
    def go_back(self):
        self.driver.back()
        self.logger.debug("执行返回操作")

    @allure.step("返回主屏幕")
    def go_home(self) -> bool:
        return self.device.go_home()

    @allure.step("点击相对坐标: ({x_ratio}, {y_ratio})")
    def click_by_coordinate(self, x_ratio: float, y_ratio: float) -> bool:
        try:
            size = self.driver.get_window_size()
            x = int(size['width'] * x_ratio)
            y = int(size['height'] * y_ratio)
            self.logger.info(f"点击坐标: ({x}, {y})")
            self.driver.tap([(x, y)])
            return True
        except WebDriverException as e:
            self.logger.error(f"点击坐标失败: {e}")
            self._take_screenshot(f"coordinate_click_failed_{x_ratio}_{y_ratio}")
            return False

    @allure.step("长按相对坐标: ({x_ratio}, {y_ratio})")
    def long_press_by_coordinate(self, x_ratio: float, y_ratio: float, duration: int = 1000) -> bool:
        try:
            size = self.driver.get_window_size()
            x = int(size['width'] * x_ratio)
            y = int(size['height'] * y_ratio)
            self.logger.info(f"长按坐标: ({x}, {y})")
            self.driver.tap([(x, y)], duration)
            return True
        except WebDriverException as e:
            self.logger.error(f"长按坐标失败: {e}")
            return False

    @allure.step("滑动: ({start_x_ratio}, {start_y_ratio}) -> ({end_x_ratio}, {end_y_ratio})")
    def swipe_by_coordinates(self, start_x_ratio: float, start_y_ratio: float,
                             end_x_ratio: float, end_y_ratio: float,
                             duration: int = 800) -> bool:
        try:
            size = self.driver.get_window_size()
            start_x = int(size['width'] * start_x_ratio)
            start_y = int(size['height'] * start_y_ratio)
            end_x = int(size['width'] * end_x_ratio)
            end_y = int(size['height'] * end_y_ratio)
            self.logger.info(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y})")
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            return True
        except WebDriverException as e:
            self.logger.error(f"滑动失败: {e}")
            return False

    def _take_screenshot(self, name: str = None) -> Optional[str]:
        if not self.screenshot_config.get('on_failure', True):
            return None
        filepath = None
        try:
            save_path = self.screenshot_config.get('save_path', './screenshots')
            os.makedirs(save_path, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{name or 'screenshot'}_{timestamp}.png"
            filepath = os.path.join(save_path, filename)
            self.driver.save_screenshot(filepath)
            self.logger.info(f"截图已保存: {filepath}")
            return filepath
        except OSError as e:
            self.logger.error(f"截图保存失败: {e}")
            raise ScreenshotSaveError(file_path=filepath, reason=str(e)) from e
        except WebDriverException as e:
            self.logger.error(f"截图失败: {e}")
            raise ScreenshotSaveError(file_path=filepath, reason=str(e)) from e

    @allure.step("截图: {name}")
    def take_screenshot(self, name: str = None) -> Optional[str]:
        try:
            return self._take_screenshot(name)
        except ScreenshotSaveError:
            return None

    def wait_for_page_load(self, wait_timeout: int = 15):
        self.logger.info(f"等待{self.__class__.__name__}页面加载...")

    @allure.step("处理弹窗")
    def handle_alert(self, accept: bool = True, wait_timeout: int = 5) -> bool:
        try:
            alert = WebDriverWait(self.driver, wait_timeout).until(EC.alert_is_present())
            if accept:
                alert.accept()
                self.logger.info("弹窗已接受")
            else:
                alert.dismiss()
                self.logger.info("弹窗已取消")
            return True
        except TimeoutException:
            self.logger.debug("未检测到弹窗")
            return False
        except WebDriverException as e:
            self.logger.error(f"处理弹窗失败: {e}")
            return False