"""
企业级日志记录模块
支持控制台和文件输出，可自主设置打印级别
日志文件名自动包含日期，格式：automation_2026-08-15.log
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional
import yaml


class Logger:
    """
    日志管理器（单例模式）
    支持控制台和文件输出，可配置日志级别
    日志文件名自动包含日期
    """

    _instance = None
    _loggers = {}

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: str = "config/config.yaml"):
        """初始化日志配置"""
        if not hasattr(self, 'initialized'):
            self.config = self._load_config(config_path)
            self.log_config = self.config.get('logging', {})
            self.initialized = True

    @staticmethod
    def _load_config(config_path: str) -> dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            return {}

    @staticmethod
    def _get_dated_filename(base_name: str, extension: str = "log") -> str:
        """
        根据日期生成文件名

        Args:
            base_name: 基础文件名
            extension: 文件扩展名

        Returns:
            str: 带日期的文件名
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        name_without_ext = base_name.rsplit('.', 1)[0] if '.' in base_name else base_name
        return f"{name_without_ext}_{date_str}.{extension}"

    def get_logger(self, name: str = None, log_level: Optional[str] = None) -> logging.Logger:
        """
        获取日志记录器

        Args:
            name: 日志记录器名称
            log_level: 日志级别

        Returns:
            logging.Logger: 日志记录器实例
        """
        if name is None:
            name = __name__

        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.propagate = False  # 禁止向根 logger 传播，避免重复输出
        level = log_level or self.log_config.get('level', 'INFO')
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        logger.handlers.clear()

        # 控制台格式化器
        console_formatter = logging.Formatter(
            fmt=self.log_config.get('console_format', '%(asctime)s [%(levelname)s] %(message)s'),
            datefmt=self.log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )

        # 文件格式化器
        file_formatter = logging.Formatter(
            fmt=self.log_config.get('format', '%(asctime)s [%(levelname)s] %(name)s - %(message)s'),
            datefmt=self.log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )

        # 控制台处理器
        if self.log_config.get('console_output', True):
            console_handler = logging.StreamHandler()
            console_level = self.log_config.get('console_level', level)
            console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        # 文件处理器（按日期命名）
        if self.log_config.get('file_output', True):
            log_dir = self.log_config.get('file_path', './logs')
            os.makedirs(log_dir, exist_ok=True)

            base_name = self.log_config.get('file_name', 'automation.log')
            dated_filename = self._get_dated_filename(base_name)
            log_file = os.path.join(log_dir, dated_filename)

            max_size = self.log_config.get('max_file_size', 10) * 1024 * 1024
            backup_count = self.log_config.get('backup_count', 5)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_level = self.log_config.get('file_level', 'DEBUG')
            file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        self._loggers[name] = logger
        return logger

    @staticmethod
    def set_global_level(level: str):
        """设置全局日志级别"""
        logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))


# 全局实例
logger_manager = Logger()
default_logger = logger_manager.get_logger('APP_UI_Test')


def get_logger(name: str = None) -> logging.Logger:
    """获取日志记录器的便捷方法"""
    return logger_manager.get_logger(name)