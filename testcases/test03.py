"""
智慧生活路由器设备测试用例 - Test03
"""

import pytest
import allure
from time import sleep
from core.logger import get_logger
from core.utils import Utils

logger = get_logger(__name__)


@allure.epic("智慧生活")
@allure.feature("路由器设备管理")
@allure.story("修改接入设备名称3")
@allure.tag("router", "device-management", "p1")
@pytest.mark.p1
class Test03:
    """路由器设备测试类"""

    @pytest.fixture
    def setup(self, smarthome_page, router_page, access_device_page):
        """前置和后置处理"""
        self.smarthome_page = smarthome_page
        self.router_page = router_page
        self.access_device_page = access_device_page

        xml_config = Utils.load_xml("config/app_config.xml")
        test_data = xml_config.get('test_data', {})
        self.original_name = test_data.get('original_name', 'iPhone')
        self.new_name = test_data.get('new_name', '')

        wifi_config = xml_config.get('wifi', {})
        self.wifi_ssid = wifi_config.get('ssid', '')
        self.wifi_password = wifi_config.get('password', '')

        self.default_device = xml_config.get('default_device', '')

        logger.info("前置条件：连接WiFi")
        self.smarthome_page.device.enable_wifi()
        sleep(2)

        logger.info(f"前置条件：进入'{self.default_device}'卡片")
        self.smarthome_page.click_device_card(self.default_device)

        yield

        logger.info("=" * 50)
        logger.info(f"后置处理：修改设备名称为'{self.original_name}'")
        self.access_device_page.modify_device_name(self.original_name)
        sleep(2)

    @pytest.mark.usefixtures("setup")
    @allure.title("修改路由器接入设备名称")
    @allure.description("验证路由器接入设备名称修改功能")
    @allure.severity(allure.severity_level.CRITICAL)
    def test03(self):
        """测试用例：修改路由器接入设备名称"""
        self.router_page.assert_that.true(
            self.router_page.enter_device_page(),
            "进入设备页面失败"
        )

        self.router_page.assert_that.true(
            self.router_page.enter_access_device_page(),
            "进入接入设备页面失败"
        )

        self.access_device_page.assert_that.true(
            self.access_device_page.enter_offline_devices(),
            "进入离线设备页面失败"
        )

        self.access_device_page.assert_that.true(
            self.access_device_page.enter_device_by_name(self.original_name),
            f"进入'{self.original_name}'设备管理页面失败"
        )

        self.access_device_page.assert_that.true(
            self.access_device_page.modify_device_name(self.new_name),
            f"修改设备名称为'{self.new_name}'失败"
        )

        logger.info("等待2秒")
        sleep(2)

        actual_name = self.access_device_page.get_device_name()
        logger.info(f"当前设备名称: {actual_name}")

        self.access_device_page.assert_that.equal(
            actual_name, self.new_name,
            f"设备名称不匹配，期望: {self.new_name}，实际: {actual_name}"
        )