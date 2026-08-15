"""
接入设备页面对象
"""

from appium.webdriver.common.appiumby import AppiumBy
from core.base_page import BasePage, log_step, timeout
from core.logger import get_logger
from core.exceptions import ElementNotFoundError

logger = get_logger(__name__)


class AccessDevicePage(BasePage):
    """接入设备页面对象"""

    ONLINE_DEVICE_TAB = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, '在线设备')]")
    OFFLINE_DEVICE_TAB = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, '离线设备')]")
    BLACKLIST_DEVICE_TAB = (AppiumBy.XPATH, "//android.widget.TextView[contains(@text, '黑名单设备')]")

    DEVICE_NAME = (AppiumBy.XPATH,
                   "//android.widget.RelativeLayout[@resource-id='com.huawei.router:id/device_detail_title']"
                   "/android.widget.TextView")

    EDIT_NAME_BUTTON = (AppiumBy.XPATH,
                        "//android.widget.RelativeLayout[@resource-id='com.huawei.router:id/device_detail_title']"
                        "/android.widget.LinearLayout[2]/android.widget.ImageView")
    NAME_INPUT = (AppiumBy.ID, "com.huawei.router:id/common_ui_name_edittext")
    CONFIRM_BUTTON = (AppiumBy.ID, "com.huawei.router:id/common_ui_name_ok_btn")

    def __init__(self, driver):
        super().__init__(driver)
        self.logger = get_logger(self.__class__.__name__)

    @log_step("进入在线设备页面")
    @timeout(15)
    def enter_online_devices(self, timeout: int = 10) -> bool:
        """进入在线设备页面"""
        return self.click(self.ONLINE_DEVICE_TAB, timeout=timeout)

    @log_step("进入离线设备页面")
    @timeout(15)
    def enter_offline_devices(self, timeout: int = 10) -> bool:
        """进入离线设备页面"""
        return self.click(self.OFFLINE_DEVICE_TAB, timeout=timeout)

    @log_step("进入黑名单设备页面")
    @timeout(15)
    def enter_blacklist_devices(self, timeout: int = 10) -> bool:
        """进入黑名单设备页面"""
        return self.click(self.BLACKLIST_DEVICE_TAB, timeout=timeout)

    @log_step("获取设备名称")
    @timeout(20)
    def get_device_name(self, timeout: int = 10) -> str:
        """获取设备名称"""
        try:
            return self.get_text(self.DEVICE_NAME, timeout=timeout)
        except ElementNotFoundError:
            self.logger.error("未找到设备名称元素")
            return ""

    @log_step("进入指定设备管理页面")
    @timeout(20)
    def enter_device_by_name(self, device_name: str, timeout: int = 10) -> bool:
        """进入指定名称的设备管理页面"""
        self.logger.info(f"进入设备管理页面: {device_name}")

        locators = [
            (AppiumBy.XPATH, f"//android.widget.TextView[@text='{device_name}']"),
            (AppiumBy.XPATH, f"//android.widget.TextView[contains(@text, '{device_name}')]"),
        ]

        for locator in locators:
            if self.is_element_present(locator, timeout=3):
                return self.click(locator, timeout=timeout)

        self.logger.error(f"未找到设备: {device_name}")
        self._take_screenshot(f"device_not_found_{device_name}")
        return False

    @log_step("点击编辑名称按钮")
    def click_edit_name_button(self, timeout: int = 10) -> bool:
        """点击编辑名称按钮"""
        return self.click(self.EDIT_NAME_BUTTON, timeout=timeout)

    @log_step("输入新名称")
    def input_new_name(self, name: str, timeout: int = 10) -> bool:
        """输入新名称"""
        self.logger.info(f"输入新名称: {name}")
        return self.input_text(self.NAME_INPUT, name, clear_first=True, timeout=timeout)

    @log_step("点击确认按钮")
    def click_confirm_button(self, timeout: int = 10) -> bool:
        """点击确认按钮"""
        return self.click(self.CONFIRM_BUTTON, timeout=timeout)

    @log_step("修改设备名称")
    @timeout(60)
    def modify_device_name(self, new_name: str) -> bool:
        """修改设备名称"""
        self.logger.info(f"修改设备名称为: {new_name}")

        if not self.click_edit_name_button():
            self.logger.error("点击编辑按钮失败")
            return False

        if not self.input_new_name(new_name):
            self.logger.error("输入新名称失败")
            return False

        if not self.click_confirm_button():
            self.logger.error("点击确认按钮失败")
            return False

        self.logger.info(f"设备名称修改成功: {new_name}")
        return True