"""
Pytest配置文件（根目录版本）
提供测试夹具（fixtures）和钩子函数
"""

import os
import sys
import json
import shutil
import pytest
import time
import psutil
import allure
from datetime import datetime
from typing import Dict, Generator
from _pytest.runner import TestReport
from _pytest.nodes import Item
from _pytest.config import Config
from appium.webdriver.webdriver import WebDriver

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.driver_manager import driver_manager
from core.logger import get_logger
from core.utils import Utils
from core.exceptions import (
    DriverCreationError,
    DeviceNotFoundError,
    DeviceOfflineError,
    AppiumConnectionError,
    AppiumServiceStartError
)
from core.exception_handler import (
    global_exception_handler,
    global_recovery_manager
)
from core.device_operations import DeviceOperations
from pages.smarthome_page import SmartHomePage
from pages.router_page import RouterPage
from pages.access_device_page import AccessDevicePage

logger = get_logger(__name__)

HISTORY_DIR = os.path.join(project_root, 'reports', 'history')

MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY = 2


def pytest_configure(config: Config):
    """Pytest配置钩子"""
    dirs_to_create = ['screenshots', 'reports/allure-results', 'reports/history', 'logs']
    for dir_path in dirs_to_create:
        Utils.ensure_dir(os.path.join(project_root, dir_path))

    config.addinivalue_line("markers", "smoke: 冒烟测试")
    config.addinivalue_line("markers", "regression: 回归测试")
    config.addinivalue_line("markers", "p0: 优先级P0")
    config.addinivalue_line("markers", "p1: 优先级P1")
    config.addinivalue_line("markers", "p2: 优先级P2")
    config.addinivalue_line("markers", "p3: 优先级P3")


def _restore_history(allure_dir: str):
    """恢复历史趋势数据"""
    trend_files = [
        'history.json',
        'history-trend.json',
        'duration-trend.json',
        'retry-trend.json',
        'categories-trend.json'
    ]

    for filename in trend_files:
        source = os.path.join(HISTORY_DIR, filename)
        if os.path.exists(source):
            target = os.path.join(allure_dir, filename)
            shutil.copy2(source, target)
            logger.debug(f"已恢复趋势数据: {filename}")


def _load_json(file_path: str) -> list:
    """安全加载 JSON 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, FileNotFoundError):
        return []


def _save_json(file_path: str, data: list):
    """安全保存 JSON 文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"保存趋势数据失败: {e}")


def _save_history(session, exitstatus):
    """保存测试结果历史趋势数据"""
    Utils.ensure_dir(HISTORY_DIR)

    build_name = datetime.now().strftime('%Y%m%d_%H%M%S')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    total = 0
    passed = 0
    failed = 0
    skipped = 0
    broken = 0
    duration = 0.0
    retry_count = 0

    for item in session.items:
        total += 1
        retry_count += getattr(item, 'execution_count', 0)

        if hasattr(item, 'rep_call'):
            rep = item.rep_call
            if rep.passed:
                passed += 1
            elif rep.failed:
                failed += 1
            elif rep.skipped:
                skipped += 1
            if hasattr(rep, 'duration'):
                duration += rep.duration

    history_file = os.path.join(HISTORY_DIR, 'history.json')
    history = _load_json(history_file)
    history.append({
        'timestamp': timestamp,
        'buildName': f"Build_{build_name}",
        'total': total,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'broken': broken,
        'exitStatus': exitstatus,
        'duration': round(duration, 2)
    })
    _save_json(history_file, history[-100:])

    trend_file = os.path.join(HISTORY_DIR, 'history-trend.json')
    trend = _load_json(trend_file)
    trend.append({
        'buildName': f"Build_{build_name}",
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'broken': broken,
        'total': total
    })
    _save_json(trend_file, trend[-100:])

    duration_file = os.path.join(HISTORY_DIR, 'duration-trend.json')
    duration_trend = _load_json(duration_file)
    duration_trend.append({
        'buildName': f"Build_{build_name}",
        'duration': round(duration, 2)
    })
    _save_json(duration_file, duration_trend[-100:])

    retry_file = os.path.join(HISTORY_DIR, 'retry-trend.json')
    retry_trend = _load_json(retry_file)
    retry_trend.append({
        'buildName': f"Build_{build_name}",
        'retries': retry_count
    })
    _save_json(retry_file, retry_trend[-100:])

    categories_file = os.path.join(HISTORY_DIR, 'categories-trend.json')
    categories_trend = _load_json(categories_file)
    categories_trend.append({
        'buildName': f"Build_{build_name}",
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'broken': broken
    })
    _save_json(categories_file, categories_trend[-100:])

    logger.info(f"历史趋势数据已保存: {HISTORY_DIR}")


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

    allure_dir = os.path.join(project_root, 'reports', 'allure-results')
    Utils.ensure_dir(allure_dir)

    env_props = [
        f"RunEnv={driver_manager.run_env}",
        f"DeviceCount={driver_manager.get_device_count()}",
        f"Platform=Android",
        f"Automation=UiAutomator2",
        f"AppiumURL={driver_manager._get_appium_url()}",
        f"Python={sys.version.split()[0]}",
        f"ExecTime={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ]
    for i, device in enumerate(devices):
        env_props.append(f"Device{i + 1}={device.get('device_name', 'Unknown')}_{device.get('udid', 'N/A')}")
    env_path = os.path.join(allure_dir, 'environment.properties')
    with open(env_path, 'w', encoding='ISO-8859-1') as f:
        f.write('\n'.join(env_props))

    executor_info = {
        "name": "APP_UI_Test Runner",
        "type": "pytest",
        "buildName": f"Build_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "buildUrl": os.getenv('BUILD_URL', ''),
        "reportUrl": os.getenv('BUILD_URL', '') + 'allure/'
    }
    executor_path = os.path.join(allure_dir, 'executor.json')
    with open(executor_path, 'w', encoding='utf-8') as f:
        json.dump(executor_info, f, ensure_ascii=False, indent=2)

    categories = [
        {"name": "Test Failure", "matchedStatuses": ["failed"],
         "messageRegex": ".*AssertionError.*"},
        {"name": "Element Not Found", "matchedStatuses": ["failed"],
         "messageRegex": ".*ElementNotFoundError.*"},
        {"name": "Device Connection Failed", "matchedStatuses": ["failed"],
         "messageRegex": ".*ConnectionError.*|.*AppiumConnectionError.*"},
        {"name": "Test Passed", "matchedStatuses": ["passed"]},
        {"name": "Test Skipped", "matchedStatuses": ["skipped"]},
        {"name": "Test Broken", "matchedStatuses": ["broken"]}
    ]
    categories_path = os.path.join(allure_dir, 'categories.json')
    with open(categories_path, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

    _restore_history(allure_dir)

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

    _save_history(session, exitstatus)

    logger.info("=" * 60)

    driver_manager.quit_all_drivers()
    if driver_manager.run_env == 'local':
        driver_manager.stop_appium_service()
    global_exception_handler.clear_history()


@pytest.fixture(scope="function")
def driver(request) -> Generator[WebDriver, None, None]:
    """WebDriver fixture（带断线重连机制）"""
    device_index = getattr(request, 'param', 0)
    if hasattr(request.config, 'option') and hasattr(request.config.option, 'device_index'):
        device_index = request.config.option.device_index

    driver_instance = None
    device_name = None
    udid = None
    last_exception = None

    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        try:
            driver_instance = driver_manager.create_driver(device_index)

            devices = driver_manager.devices_config.get('devices', [])
            if device_index < len(devices):
                device_name = devices[device_index].get('device_name', f'device_{device_index}')
                udid = devices[device_index].get('udid', 'N/A')

            logger.info(f"测试用例 [{request.node.name}] 开始执行 (设备: {device_name})")
            global_recovery_manager.driver_getter = lambda: driver_instance

            allure.dynamic.tag(f"Device:{device_name}")
            allure.dynamic.tag(f"UDID:{udid}")

            break

        except DeviceNotFoundError:
            logger.error("设备未找到（不可重试）")
            pytest.skip("跳过测试 - 设备未找到")
        except (AppiumConnectionError, DeviceOfflineError, DriverCreationError) as e:
            last_exception = e
            if attempt < MAX_RECONNECT_ATTEMPTS - 1:
                logger.warning(
                    f"Driver创建失败，第 {attempt + 1}/{MAX_RECONNECT_ATTEMPTS} 次重试: {e}"
                )
                driver_manager.quit_all_drivers()
                time.sleep(RECONNECT_DELAY * (attempt + 1))
            else:
                logger.error(f"Driver创建最终失败（已重试 {MAX_RECONNECT_ATTEMPTS} 次）: {e}")
                if isinstance(e, AppiumConnectionError):
                    pytest.fail(f"Appium连接失败: {e}")
                elif isinstance(e, DeviceOfflineError):
                    pytest.fail(f"设备离线: {e}")
                else:
                    pytest.fail(f"Driver创建失败: {e}")

    if driver_instance is None:
        pytest.fail(f"Driver创建失败: {last_exception}")

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


@pytest.fixture(scope="function")
def device_ops(driver) -> DeviceOperations:
    """DeviceOperations fixture"""
    return DeviceOperations(driver)


@pytest.fixture(autouse=True)
def manage_smarthome_app(driver):
    """自动管理智慧生活应用生命周期"""
    from core.utils import Utils

    device = DeviceOperations(driver)
    smarthome = SmartHomePage(driver)

    smarthome.launch_app()

    yield

    # 从 XML 读取包名，避免硬编码
    xml_config = Utils.load_xml("config/app_config.xml")
    root = xml_config.get('app_config', xml_config)
    app_config = root.get('app', {})
    app_package = app_config.get('package', '')

    try:
        device.close_app(app_package)
        logger.info(f"已自动关闭应用: {app_package}")
    except Exception as e:
        logger.debug(f"关闭应用异常: {e}")


@pytest.fixture(autouse=True)
def performance_monitor(request):
    """性能监控 fixture"""
    start_time = time.time()
    start_cpu = psutil.cpu_percent(interval=None)
    start_mem = psutil.virtual_memory().percent

    yield

    end_time = time.time()
    end_cpu = psutil.cpu_percent(interval=None)
    end_mem = psutil.virtual_memory().percent

    exec_time = end_time - start_time
    cpu_usage = max(0, end_cpu - start_cpu)
    mem_usage = max(0, end_mem - start_mem)

    perf_data = (
        f"执行时间: {exec_time:.2f}s\n"
        f"CPU使用率变化: {cpu_usage:.1f}%\n"
        f"内存使用率变化: {mem_usage:.1f}%\n"
        f"结束CPU: {end_cpu:.1f}%\n"
        f"结束内存: {end_mem:.1f}%"
    )

    allure.attach(
        perf_data,
        name="Performance Data",
        attachment_type=allure.attachment_type.TEXT
    )

    logger.info(f"性能数据: 执行时间={exec_time:.2f}s, CPU变化={cpu_usage:.1f}%, 内存变化={mem_usage:.1f}%")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """测试报告钩子"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        item.rep_call = report
        rerun_count = getattr(item, 'execution_count', 0)
        if rerun_count > 0:
            allure.dynamic.description(f"Retry: {rerun_count} time(s)")

        if report.failed:
            driver = item.funcargs.get('driver') if hasattr(item, 'funcargs') else None

            if driver:
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    screenshot_name = f"failure_{item.name}_{timestamp}"
                    screenshot_path = os.path.join(project_root, 'screenshots', f"{screenshot_name}.png")
                    driver.save_screenshot(screenshot_path)
                    logger.info(f"失败截图已保存: {screenshot_path}")

                    with open(screenshot_path, 'rb') as f:
                        allure.attach(f.read(), name=screenshot_name,
                                      attachment_type=allure.attachment_type.PNG)

                    error_text = str(report.longrepr) if hasattr(report, 'longrepr') else ""
                    allure.attach(error_text, name="Error Detail",
                                  attachment_type=allure.attachment_type.TEXT)
                    logger.error(f"测试失败 [{item.name}]: {error_text}")
                except Exception as e:
                    logger.error(f"失败截图处理异常: {e}")


def pytest_addoption(parser):
    """添加自定义命令行选项"""
    parser.addoption("--device-index", action="store", default=0, type=int, help="设备索引")
    parser.addoption("--run-env", action="store", default=None, choices=['local', 'docker'], help="运行环境")
    parser.addoption("--no-screenshot", action="store_true", default=False, help="禁用失败截图")
    parser.addoption("--test-log-level", action="store", default="INFO",
                     choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help="日志级别")


def pytest_runtest_setup(item):
    """测试用例设置钩子"""
    log_level = item.config.getoption("--test-log-level", default="INFO")
    from core.logger import logger_manager
    logger_manager.set_global_level(log_level)
    logger.debug(f"开始设置测试用例: {item.name}")