"""
工具类模块
提供常用的辅助功能
"""

import os

import xmltodict
import yaml
import subprocess
import platform
from typing import Dict, Any, Optional
from datetime import datetime
from core.logger import get_logger

logger = get_logger(__name__)


class Utils:
    """工具类"""

    @staticmethod
    def load_yaml(file_path: str) -> Dict[str, Any]:
        """
        加载YAML配置文件

        Args:
            file_path: 文件路径

        Returns:
            Dict: 配置数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            logger.debug(f"成功加载配置文件: {file_path}")
            return data if data else {}
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {file_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"配置文件格式错误: {e}")
            return {}

    @staticmethod
    def get_project_root() -> str:
        """
        获取项目根目录

        Returns:
            str: 项目根目录路径
        """
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def ensure_dir(dir_path: str):
        """
        确保目录存在，不存在则创建

        Args:
            dir_path: 目录路径
        """
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.debug(f"创建目录: {dir_path}")

    @staticmethod
    def get_timestamp(format_str: str = '%Y%m%d_%H%M%S') -> str:
        """
        获取当前时间戳字符串

        Args:
            format_str: 时间格式

        Returns:
            str: 时间戳字符串
        """
        return datetime.now().strftime(format_str)

    @staticmethod
    def get_platform() -> str:
        """
        获取当前平台信息

        Returns:
            str: windows / linux / macos / unknown
        """
        system = platform.system()
        if system == 'Windows':
            return 'windows'
        elif system == 'Linux':
            return 'linux'
        elif system == 'Darwin':
            return 'macos'
        else:
            return 'unknown'

    @staticmethod
    def check_appium_installed() -> bool:
        """
        检查Appium是否已安装

        Returns:
            bool: 是否已安装
        """
        try:
            result = subprocess.run(
                ['appium', '--version'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info(f"Appium版本: {result.stdout.strip()}")
                return True
            return False
        except FileNotFoundError:
            logger.warning("Appium未安装")
            return False

    @staticmethod
    def generate_allure_report(
            results_dir: str = './reports/allure-results',
            report_dir: str = './reports/allure-report',
            clean: bool = True
    ):
        """生成Allure报告"""
        try:
            cmd = ['allure', 'generate', results_dir, '-o', report_dir]
            if clean:
                cmd.append('--clean')

            logger.info(f"正在生成Allure报告: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

            if result.returncode == 0:
                logger.info(f"Allure报告已生成: {report_dir}")
            else:
                logger.error(f"生成Allure报告失败: {result.stderr}")
        except Exception as e:
            logger.error(f"生成Allure报告异常: {e}")

    @staticmethod
    def get_file_size(file_path: str) -> Optional[int]:
        """
        获取文件大小（字节）

        Args:
            file_path: 文件路径

        Returns:
            int: 文件大小，失败返回None
        """
        try:
            return os.path.getsize(file_path)
        except OSError as e:
            logger.error(f"获取文件大小失败: {e}")
            return None

    @staticmethod
    def read_file(file_path: str) -> Optional[str]:
        """
        读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            str: 文件内容，失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except (FileNotFoundError, OSError) as e:
            logger.error(f"读取文件失败: {e}")
            return None

    @staticmethod
    def write_file(file_path: str, content: str) -> bool:
        """
        写入文件

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            bool: 是否成功
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except OSError as e:
            logger.error(f"写入文件失败: {e}")
            return False

    @staticmethod
    def load_xml(file_path: str) -> dict:
        """
        加载 XML 配置文件，转换为字典

        Args:
            file_path: XML 文件路径

        Returns:
            dict: 配置数据字典
        """
        import xmltodict
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return xmltodict.parse(f.read())
        except FileNotFoundError:
            logger.error(f"XML配置文件不存在: {file_path}")
            return {}
        except Exception as e:
            logger.error(f"XML配置文件解析失败: {e}")
            return {}

    @staticmethod
    def _xml_to_dict(element) -> dict:
        """递归将 XML 元素转换为字典"""
        result = {}

        if element.attrib:
            result.update(element.attrib)

        for child in element:
            child_data = Utils._xml_to_dict(child)
            if child.tag in result:
                if isinstance(result[child.tag], list):
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = [result[child.tag], child_data]
            else:
                result[child.tag] = child_data if child_data else child.text or ''

        if not result and element.text:
            return element.text.strip()

        return result