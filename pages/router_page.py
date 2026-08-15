"""
路由器设备页面对象
"""

from appium.webdriver.common.appiumby import AppiumBy
from time import sleep
from core.base_page import BasePage, log_step
from core.logger import get_logger
from core.exceptions import ElementNotFoundError

logger = get_logger(__name__)


class RouterPage(BasePage):
    """路由器设备页面对象"""

    DEVICE_ENTRY = (AppiumBy.XPATH, "//android.widget.TextView[@text='设备']")
    DEVICE_ENTRY_CONTAINS = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, '设备')]")

    ACCESS_DEVICE_ENTRY = (AppiumBy.XPATH, "//android.widget.TextView[@text='接入设备']")
    ACCESS_DEVICE_ENTRY_CONTAINS = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, '接入设备')]")

    DEVICE_COORDINATE = (0.5, 0.533)
    ACCESS_DEVICE_COORDINATE = (0.5, 0.645)

    def __init__(self, driver):
        super().__init__(driver)
        self.logger = get_logger(self.__class__.__name__)

    @log_step("进入设备页面")
    def enter_device_page(self, use_xpath: bool = False, wait_timeout: int = 10) -> bool:
        """点击进入设备页面"""
        self.logger.info("进入设备页面...")

        if not use_xpath:
            self.logger.info(f"等待3秒后使用相对坐标点击: {self.DEVICE_COORDINATE}")
            sleep(3)
            return self.click_by_coordinate(*self.DEVICE_COORDINATE)

        try:
            if self.is_element_present(self.DEVICE_ENTRY, wait_timeout=wait_timeout):
                return self.click(self.DEVICE_ENTRY, wait_timeout=wait_timeout)
        except ElementNotFoundError:
            pass

        try:
            if self.is_element_present(self.DEVICE_ENTRY_CONTAINS, wait_timeout=wait_timeout):
                return self.click(self.DEVICE_ENTRY_CONTAINS, wait_timeout=wait_timeout)
        except ElementNotFoundError:
            pass

        self.logger.warning(f"未找到'设备'元素，降级使用相对坐标点击: {self.DEVICE_COORDINATE}")
        sleep(3)
        return self.click_by_coordinate(*self.DEVICE_COORDINATE)

    @log_step("进入接入设备页面")
    def enter_access_device_page(self, use_xpath: bool = False, wait_timeout: int = 10) -> bool:
        """点击进入接入设备页面"""
        self.logger.info("进入接入设备页面...")

        if not use_xpath:
            self.logger.info(f"等待3秒后使用相对坐标点击: {self.ACCESS_DEVICE_COORDINATE}")
            sleep(3)
            return self.click_by_coordinate(*self.ACCESS_DEVICE_COORDINATE)

        try:
            if self.is_element_present(self.ACCESS_DEVICE_ENTRY, wait_timeout=wait_timeout):
                return self.click(self.ACCESS_DEVICE_ENTRY, wait_timeout=wait_timeout)
        except ElementNotFoundError:
            pass

        try:
            if self.is_element_present(self.ACCESS_DEVICE_ENTRY_CONTAINS, wait_timeout=wait_timeout):
                return self.click(self.ACCESS_DEVICE_ENTRY_CONTAINS, wait_timeout=wait_timeout)
        except ElementNotFoundError:
            pass

        self.logger.warning(f"未找到'接入设备'元素，降级使用相对坐标点击: {self.ACCESS_DEVICE_COORDINATE}")
        sleep(3)
        return self.click_by_coordinate(*self.ACCESS_DEVICE_COORDINATE)