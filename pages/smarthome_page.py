"""
智慧生活首页页面对象
参数值从 config/app_config.xml 读取
"""

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import TimeoutException
from core.base_page import BasePage, log_step
from core.logger import get_logger
from core.exceptions import PageLoadTimeoutError, ElementNotFoundError
from core.utils import Utils

logger = get_logger(__name__)


class SmartHomePage(BasePage):
    """
    智慧生活首页页面对象
    """

    def __init__(self, driver, config_path: str = "config/config.yaml"):
        super().__init__(driver, config_path)
        self.logger = get_logger(self.__class__.__name__)

        xml_path = "config/app_config.xml"
        xml_config = Utils.load_xml(xml_path)

        app_config = xml_config.get('app', {})
        page_load_config = xml_config.get('page_load', {})
        nav_config = xml_config.get('navigation', {})

        self.APP_PACKAGE = app_config.get('package', '')
        self.HOME_TAB_NAME = page_load_config.get('home_tab_name', '')
        self.PAGE_LOAD_TIMEOUT = int(page_load_config.get('timeout', 30))
        self.DEFAULT_DEVICE_NAME = xml_config.get('default_device', '')

        self.NAV_HOME_TAB = nav_config.get('home_tab', '')
        self.NAV_PRODUCT_TAB = nav_config.get('product_tab', '')
        self.NAV_DISCOVER_TAB = nav_config.get('discover_tab', '')
        self.NAV_SCENE_TAB = nav_config.get('scene_tab', '')
        self.NAV_ME_TAB = nav_config.get('me_tab', '')

    @property
    def HOME_TAB(self):
        return AppiumBy.XPATH, f"//android.widget.TextView[@text='{self.HOME_TAB_NAME}']"

    @property
    def HOME_TAB_CONTAINS(self):
        return AppiumBy.XPATH, f"//android.widget.TextView[contains(@text, '{self.HOME_TAB_NAME}')]"

    @property
    def BOTTOM_NAV_HOME(self):
        return AppiumBy.XPATH, f"//android.widget.TextView[@text='{self.NAV_HOME_TAB}']"

    @property
    def BOTTOM_NAV_PRODUCT(self):
        return AppiumBy.XPATH, f"//android.widget.TextView[@text='{self.NAV_PRODUCT_TAB}']"

    @property
    def BOTTOM_NAV_DISCOVER(self):
        return AppiumBy.XPATH, f"//android.widget.TextView[@text='{self.NAV_DISCOVER_TAB}']"

    @property
    def BOTTOM_NAV_SCENE(self):
        return AppiumBy.XPATH, f"//android.widget.TextView[@text='{self.NAV_SCENE_TAB}']"

    @property
    def BOTTOM_NAV_ME(self):
        return AppiumBy.XPATH, f"//android.widget.TextView[@text='{self.NAV_ME_TAB}']"

    LOADING_INDICATOR = (AppiumBy.XPATH, "//android.widget.ProgressBar")

    @log_step("启动应用")
    def launch_app(self) -> bool:
        """启动应用"""
        self.logger.info(f"正在启动应用: {self.APP_PACKAGE}")

        self.device.wake_and_unlock()
        self.go_home()
        self.device.close_app(self.APP_PACKAGE)

        if not self.device.launch_app(self.APP_PACKAGE):
            self.logger.error(f"启动应用失败: {self.APP_PACKAGE}")
            return False

        try:
            self.wait_for_page_load()
            self.logger.info(f"应用启动成功: {self.APP_PACKAGE}")
            return True
        except PageLoadTimeoutError:
            self.logger.error(f"应用页面加载超时: {self.APP_PACKAGE}")
            return False

    def wait_for_page_load(self, timeout: int = None):
        """等待页面加载完成"""
        timeout = timeout or self.PAGE_LOAD_TIMEOUT
        self.logger.info(f"等待页面加载，标识元素: '{self.HOME_TAB_NAME}'...")

        try:
            self.wait_for_element_disappear(self.LOADING_INDICATOR, timeout=10)
        except (ElementNotFoundError, TimeoutException):
            self.logger.debug("未检测到加载指示器或等待超时")

        try:
            if self.is_element_present(self.HOME_TAB, timeout=5):
                self.find_element(self.HOME_TAB, timeout=timeout)
                self.logger.info(f"页面加载完成（找到'{self.HOME_TAB_NAME}'元素）")
                return
        except ElementNotFoundError:
            pass

        try:
            self.find_element(self.HOME_TAB_CONTAINS, timeout=timeout)
            self.logger.info(f"页面加载完成（contains匹配'{self.HOME_TAB_NAME}'元素）")
            return
        except ElementNotFoundError as e:
            raise PageLoadTimeoutError(
                page_name=self.__class__.__name__,
                timeout=timeout,
                expected_element=f"名称为'{self.HOME_TAB_NAME}'的元素"
            ) from e

    @log_step("点击设备卡片")
    def click_device_card(self, device_name: str, timeout: int = 10) -> bool:
        """点击指定名称的设备卡片"""
        self.logger.info(f"点击设备卡片: {device_name}")

        locators = [
            (AppiumBy.XPATH, f"//android.widget.TextView[@text='{device_name}']"),
            (AppiumBy.XPATH, f"//android.widget.TextView[contains(@text, '{device_name}')]"),
        ]

        for locator in locators:
            if self.is_element_present(locator, timeout=3):
                return self.click(locator, timeout=timeout)

        locator_xpath = AppiumBy.XPATH, f"//android.widget.TextView[@text='{device_name}']"
        if self.scroll_to_element(locator_xpath):
            return self.click(locator_xpath, timeout=timeout)

        self.logger.error(f"未找到设备卡片: {device_name}")
        self._take_screenshot(f"device_not_found_{device_name}")
        return False

    @log_step("点击默认设备卡片")
    def click_default_device(self) -> bool:
        """点击 XML 配置中指定的默认设备卡片"""
        if not self.DEFAULT_DEVICE_NAME:
            self.logger.warning("未配置默认设备名称")
            return False
        return self.click_device_card(self.DEFAULT_DEVICE_NAME)

    def is_on_home_tab(self) -> bool:
        """判断当前是否在首页标签页"""
        return self.is_element_present(self.HOME_TAB, timeout=3) or \
               self.is_element_present(self.HOME_TAB_CONTAINS, timeout=3)

    def is_device_card_present(self, device_name: str) -> bool:
        """判断指定名称的设备卡片是否存在"""
        locator = AppiumBy.XPATH, f"//android.widget.TextView[@text='{device_name}']"
        locator_contains = AppiumBy.XPATH, f"//android.widget.TextView[contains(@text, '{device_name}')]"
        return self.is_element_present(locator, timeout=3) or \
               self.is_element_present(locator_contains, timeout=3)

    @log_step("切换标签")
    def switch_to_home_tab(self) -> bool:
        return self.click(self.BOTTOM_NAV_HOME)

    @log_step("切换标签")
    def switch_to_product_tab(self) -> bool:
        return self.click(self.BOTTOM_NAV_PRODUCT)

    @log_step("切换标签")
    def switch_to_discover_tab(self) -> bool:
        return self.click(self.BOTTOM_NAV_DISCOVER)

    @log_step("切换标签")
    def switch_to_scene_tab(self) -> bool:
        return self.click(self.BOTTOM_NAV_SCENE)

    @log_step("切换标签")
    def switch_to_me_tab(self) -> bool:
        return self.click(self.BOTTOM_NAV_ME)