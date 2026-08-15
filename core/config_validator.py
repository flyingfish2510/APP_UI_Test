"""
配置校验模块
提供配置完整性和有效性校验
"""

from core.logger import get_logger

logger = get_logger(__name__)


class ConfigValidator:
    """
    配置校验器

    校验 YAML 配置文件的必要字段是否完整。
    缺失字段时记录警告，不影响框架启动（使用默认值）。
    """

    # 必要字段定义：{配置段: [必要键]}
    YAML_REQUIRED_KEYS = {
        'appium': ['local_host', 'docker_host'],
        'timeout': ['implicit_wait', 'explicit_wait', 'page_load_timeout'],
        'logging': ['level', 'file_path', 'file_name'],
        'screenshot': ['save_path', 'on_failure'],
        'allure': ['results_path', 'report_path'],
        'environment': ['run_env', 'platform_name'],
        'device_management': ['device_config_file'],
    }

    # XML 必要字段
    XML_REQUIRED_KEYS = {
        'app': ['package'],
        'page_load': ['home_tab_name', 'timeout'],
    }

    @classmethod
    def validate_yaml(cls, config: dict) -> bool:
        """
        校验 YAML 配置

        Args:
            config: YAML 配置字典

        Returns:
            bool: 是否存在缺失字段（True=完整，False=有缺失）
        """
        if not config:
            logger.warning("YAML 配置为空")
            return False

        missing_count = 0

        for section, keys in cls.YAML_REQUIRED_KEYS.items():
            if section not in config:
                logger.warning(f"配置缺少段: {section}")
                missing_count += 1
                continue

            section_config = config[section]
            for key in keys:
                if key not in section_config or section_config[key] is None:
                    logger.warning(f"配置 {section}.{key} 缺失，将使用默认值")
                    missing_count += 1

        if missing_count == 0:
            logger.info("YAML 配置校验通过")
            return True
        else:
            logger.warning(f"YAML 配置存在 {missing_count} 个缺失项")
            return False

    @classmethod
    def validate_xml(cls, config: dict) -> bool:
        """
        校验 XML 配置

        Args:
            config: XML 配置字典（xmltodict 解析结果）

        Returns:
            bool: 是否存在缺失字段
        """
        if not config:
            logger.warning("XML 配置为空")
            return False

        root = config.get('app_config', config)
        missing_count = 0

        for section, keys in cls.XML_REQUIRED_KEYS.items():
            if section not in root:
                logger.warning(f"XML 配置缺少段: {section}")
                missing_count += 1
                continue

            section_config = root[section]
            for key in keys:
                if key not in section_config or section_config[key] is None:
                    logger.warning(f"XML 配置 {section}.{key} 缺失")
                    missing_count += 1

        # 可选字段
        if 'default_device' not in root:
            logger.debug("XML 配置未设置 default_device（可选）")

        if 'test_data' not in root:
            logger.debug("XML 配置未设置 test_data（可选）")

        if 'navigation' not in root:
            logger.debug("XML 配置未设置 navigation（可选）")

        if missing_count == 0:
            logger.info("XML 配置校验通过")
            return True
        else:
            logger.warning(f"XML 配置存在 {missing_count} 个缺失项")
            return False