"""
Pytest配置文件（根目录版本）
提供测试夹具（fixtures）和钩子函数
"""

import os
import sys
from datetime import datetime
from typing import Dict, Generator

import pytest
from _pytest.config import Config
from appium.webdriver.webdriver import WebDriver

from pages.access_device_page import AccessDevicePage
from pages.router_page import RouterPage

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.driver_manager import driver_manager
from core.logger import get_logger
from core.utils import Utils
from core.exceptions import (
    DriverCreationError,
    DeviceNotFoundError,
    AppiumConnectionError,
    AppiumServiceStartError
)
from core.exception_handler import (
    global_exception_handler,
    global_recovery_manager
)
from core.device_operations import DeviceOperations
from pages.smarthome_page import SmartHomePage

logger = get_logger(__name__)


def pytest_configure(config: Config):
    """Pytest配置钩子"""
    dirs_to_create = ['screenshots', 'reports/allure-results', 'logs']
    for dir_path in dirs_to_create:
        Utils.ensure_dir(os.path.join(project_root, dir_path))

    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")
    config.addinivalue_line("markers", "p0: 优先级P0")
    config.addinivalue_line("markers", "p1: 优先级P1")
    config.addinivalue_line("markers", "p2: 优先级P2")


def pytest_sessionstart(session):
    """Pytest会话开始钩子"""
    logger.info("=" * 60)
    logger.info("测试会话开始")
    logger.info(f"运行环境: {driver_manager.run_env}")
    logger.info(f"设备数量: {driver_manager.get_device_count()}")

    devices = driver_manager.get_device_info()
    for i, device in enumerate(devices):
        logger.info(f"设备 {i}: {device.get('device_name', 'Unknown')} "
                    f"(UDID: {device.get('udid', 'N/A')})")
    logger.info("=" * 60)

    if driver_manager.run_env == 'local':
        try:
            driver_manager.start_appium_service()
        except (AppiumServiceStartError, AppiumConnectionError) as e:
            logger.error(f"启动Appium服务失败: {e}")
            pytest.exit(str(e))


def pytest_sessionfinish(session, exitstatus):
    """Pytest会话结束钩子"""
    logger.info("=" * 60)
    logger.info(f"测试会话结束，退出状态: {exitstatus}")

    exception_summary = global_exception_handler.get_exception_summary()
    if exception_summary['total_exceptions'] > 0:
        logger.info(f"异常总数: {exception_summary['total_exceptions']}")

    logger.info("=" * 60)

    driver_manager.quit_all_drivers()
    if driver_manager.run_env == 'local':
        driver_manager.stop_appium_service()
    global_exception_handler.clear_history()


@pytest.fixture(scope="function")
def driver(request) -> Generator[WebDriver, None, None]:
    """WebDriver fixture"""
    device_index = getattr(request, 'param', 0)
    if hasattr(request.config, 'option') and hasattr(request.config.option, 'device_index'):
        device_index = request.config.option.device_index

    driver_instance = None
    device_name = None

    try:
        driver_instance = driver_manager.create_driver(device_index)
        devices = driver_manager.devices_config.get('devices', [])
        if device_index < len(devices):
            device_name = devices[device_index].get('device_name', f'device_{device_index}')

        logger.info(f"测试用例 [{request.node.name}] 开始执行 (设备: {device_name})")
        global_recovery_manager.driver_getter = lambda: driver_instance

    except DeviceNotFoundError:
        logger.error("设备未找到")
        pytest.skip("跳过测试 - 设备未找到")
    except DriverCreationError:
        logger.error("Driver创建失败")
        pytest.fail("Driver创建失败")
    except AppiumConnectionError:
        logger.error("Appium连接失败")
        pytest.fail("Appium连接失败")

    yield driver_instance

    logger.info(f"测试用例 [{request.node.name}] 执行完毕")
    if driver_instance:
        try:
            current_device_name = None
            for name, drv in driver_manager.drivers.items():
                if drv == driver_instance:
                    current_device_name = name
                    break
            if current_device_name:
                driver_manager.quit_driver(current_device_name)
            else:
                driver_instance.quit()
        except Exception as e:
            logger.error(f"关闭Driver异常: {e}")


@pytest.fixture(scope="function")
def device_ops(driver) -> DeviceOperations:
    """DeviceOperations fixture"""
    return DeviceOperations(driver)


@pytest.fixture(scope="function")
def test_data(request) -> Dict:
    """测试数据 fixture"""
    marker = request.node.get_closest_marker('test_data')
    if marker:
        return marker.args[0] if marker.args else {}
    return {}


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """测试报告钩子，用于失败截图"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get('driver') if hasattr(item, 'funcargs') else None

        if driver:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_name = f"failure_{item.name}_{timestamp}"
                screenshot_path = os.path.join(project_root, 'screenshots', f"{screenshot_name}.png")
                driver.save_screenshot(screenshot_path)
                logger.info(f"失败截图已保存: {screenshot_path}")

                error_text = str(report.longrepr) if hasattr(report, 'longrepr') else ""
                logger.error(f"测试失败 [{item.name}]: {error_text}")
            except Exception as e:
                logger.error(f"失败截图处理异常: {e}")


def pytest_addoption(parser):
    parser.addoption("--device-index", action="store", default=0, type=int, help="设备索引")
    parser.addoption("--run-env", action="store", default=None, choices=['local', 'docker'], help="运行环境")
    parser.addoption("--no-screenshot", action="store_true", default=False, help="禁用失败截图")
    parser.addoption("--test-log-level", action="store", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help="日志级别")


def pytest_runtest_setup(item):
    log_level = item.config.getoption("--test-log-level", default="INFO")
    from core.logger import logger_manager
    logger_manager.set_global_level(log_level)

@pytest.fixture(autouse=True)
def manage_smarthome_app(driver):
    """自动管理智慧生活应用生命周期"""
    from core.device_operations import DeviceOperations
    from pages.smarthome_page import SmartHomePage

    device = DeviceOperations(driver)
    smarthome = SmartHomePage(driver)

    smarthome.launch_app()

    yield

    try:
        device.close_app("com.huawei.smarthome")
        logger.info("已自动关闭智慧生活应用")
    except Exception as e:
        logger.debug(f"关闭智慧生活应用异常: {e}")

@pytest.fixture(scope="function")
def smarthome_page(driver) -> SmartHomePage:
    """SmartHomePage fixture"""
    return SmartHomePage(driver)

@pytest.fixture(scope="function")
def router_page(driver) -> RouterPage:
    """RouterPage fixture"""
    return RouterPage(driver)

@pytest.fixture(scope="function")
def access_device_page(driver) -> AccessDevicePage:
    """AccessDevicePage fixture"""
    return AccessDevicePage(driver)