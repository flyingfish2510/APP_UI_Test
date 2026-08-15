"""
断言方法模块
提供常用的断言封装，失败时自动截图
"""

from core.logger import get_logger

logger = get_logger(__name__)


class Assertions:
    """断言工具类"""

    def __init__(self, page):
        self.page = page
        self.logger = get_logger(self.__class__.__name__)

    def element_exists(self, locator, message: str = None, timeout: int = 10):
        msg = message or f"元素不存在: {locator}"
        if not self.page.is_element_present(locator, timeout=timeout):
            self.page._take_screenshot("assert_element_not_found")
            raise AssertionError(msg)

    def element_visible(self, locator, message: str = None, timeout: int = 10):
        msg = message or f"元素不可见: {locator}"
        if not self.page.is_element_visible(locator, timeout=timeout):
            self.page._take_screenshot("assert_element_not_visible")
            raise AssertionError(msg)

    def text_equals(self, locator, expected: str, message: str = None, timeout: int = 10):
        actual = self.page.get_text(locator, timeout=timeout)
        msg = message or f"文本不匹配\n期望: {expected}\n实际: {actual}"
        if actual != expected:
            self.page._take_screenshot("assert_text_mismatch")
            raise AssertionError(msg)

    def text_contains(self, locator, expected: str, message: str = None, timeout: int = 10):
        actual = self.page.get_text(locator, timeout=timeout)
        msg = message or f"文本不包含'{expected}'\n实际: {actual}"
        if expected not in actual:
            self.page._take_screenshot("assert_text_not_contains")
            raise AssertionError(msg)

    def equal(self, actual, expected, message: str = None):
        msg = message or f"值不相等\n期望: {expected}\n实际: {actual}"
        if actual != expected:
            self.page._take_screenshot("assert_not_equal")
            raise AssertionError(msg)

    def true(self, condition: bool, message: str = None):
        msg = message or "条件为假"
        if not condition:
            self.page._take_screenshot("assert_not_true")
            raise AssertionError(msg)

    def false(self, condition: bool, message: str = None):
        msg = message or "条件为真"
        if condition:
            self.page._take_screenshot("assert_not_false")
            raise AssertionError(msg)

    def not_none(self, value, message: str = None):
        msg = message or "值为 None"
        if value is None:
            self.page._take_screenshot("assert_is_none")
            raise AssertionError(msg)