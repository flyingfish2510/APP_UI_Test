"""
全局异常处理模块
提供统一的异常处理策略和错误恢复机制
"""

import traceback
import functools
import time
from typing import Callable, Any, Dict
from core.logger import get_logger
from core.exceptions import (
    MobileAutoTestException,
    ElementNotFoundError,
    ElementNotClickableError,
    ElementStaleError,
    DriverSessionExpiredError,
    PageLoadTimeoutError,
    exception_to_dict
)

logger = get_logger(__name__)


class ExceptionHandler:
    """
    全局异常处理器
    提供统一的异常处理、记录和统计
    """

    def __init__(self):
        self.exception_history: list = []
        self.max_history_size = 100

    def handle_exception(self, exception: Exception,
                         context: Dict = None) -> Dict:
        """
        处理异常并返回标准化的错误信息

        Args:
            exception: 异常对象
            context: 上下文信息

        Returns:
            Dict: 标准化的错误信息
        """
        self._record_exception(exception, context)
        error_info = exception_to_dict(exception)
        if context:
            error_info['details']['context'] = context
        self._log_exception(exception, error_info)
        return error_info

    def _record_exception(self, exception: Exception, context: Dict = None):
        """记录异常历史"""
        from datetime import datetime
        exception_record = {
            'exception': exception,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        self.exception_history.append(exception_record)
        if len(self.exception_history) > self.max_history_size:
            self.exception_history = self.exception_history[-self.max_history_size:]

    @staticmethod
    def _log_exception(exception: Exception, error_info: Dict):
        """记录异常日志"""
        error_code = error_info.get('error_code', 'UNKNOWN')
        message = error_info.get('message', str(exception))

        if isinstance(exception, ElementNotFoundError):
            logger.warning(f"[{error_code}] {message}")
        elif isinstance(exception, ElementStaleError):
            logger.warning(f"[{error_code}] {message} - 可尝试重试")
        elif isinstance(exception, DriverSessionExpiredError):
            logger.error(f"[{error_code}] {message} - 需要重新创建会话")
        elif isinstance(exception, PageLoadTimeoutError):
            logger.error(f"[{error_code}] {message}")
        else:
            logger.error(f"[{error_code}] {message}")
            logger.debug(f"异常详情: {traceback.format_exc()}")

    def get_exception_summary(self) -> Dict:
        """
        获取异常汇总信息

        Returns:
            Dict: 异常汇总
        """
        summary = {
            'total_exceptions': len(self.exception_history),
            'exception_types': {},
            'error_codes': {},
            'recent_exceptions': []
        }

        for record in self.exception_history[-10:]:
            exc = record['exception']
            exc_type = type(exc).__name__
            summary['exception_types'][exc_type] = \
                summary['exception_types'].get(exc_type, 0) + 1

            if isinstance(exc, MobileAutoTestException):
                error_code = exc.error_code
                summary['error_codes'][error_code] = \
                    summary['error_codes'].get(error_code, 0) + 1

            summary['recent_exceptions'].append({
                'type': exc_type,
                'message': str(exc),
                'timestamp': record['timestamp']
            })

        return summary

    def clear_history(self):
        """清除异常历史"""
        self.exception_history.clear()
        logger.debug("异常历史已清除")


class RetryHandler:
    """
    重试处理器
    提供智能重试机制
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0,
                 backoff_factor: float = 2.0):
        """
        初始化重试处理器

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            backoff_factor: 退避因子
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.exception_handler = ExceptionHandler()

    @staticmethod
    def should_retry(exception: Exception) -> bool:
        """
        判断是否应该重试

        Args:
            exception: 异常对象

        Returns:
            bool: 是否应该重试
        """
        retryable_exceptions = (
            ElementStaleError,
            ElementNotClickableError,
            TimeoutError,
            ConnectionError,
        )

        if isinstance(exception, retryable_exceptions):
            return True

        if isinstance(exception, DriverSessionExpiredError):
            return False

        if isinstance(exception, MobileAutoTestException):
            retryable_codes = [
                'ELEMENT_STALE',
                'ELEMENT_NOT_CLICKABLE',
                'DEVICE_CONNECTION_ERROR'
            ]
            return exception.error_code in retryable_codes

        return False

    def retry_on_exception(self, func: Callable = None, *,
                           max_retries: int = None,
                           retry_delay: float = None,
                           backoff_factor: float = None,
                           retryable_exceptions: tuple = None):
        """
        装饰器：在指定异常时重试

        Args:
            func: 被装饰的函数
            max_retries: 最大重试次数
            retry_delay: 重试延迟
            backoff_factor: 退避因子
            retryable_exceptions: 可重试的异常类型元组

        Returns:
            装饰后的函数
        """
        if func is None:
            return functools.partial(
                self.retry_on_exception,
                max_retries=max_retries or self.max_retries,
                retry_delay=retry_delay or self.retry_delay,
                backoff_factor=backoff_factor or self.backoff_factor,
                retryable_exceptions=retryable_exceptions
            )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _max_retries = max_retries or self.max_retries
            _retry_delay = retry_delay or self.retry_delay
            _backoff_factor = backoff_factor or self.backoff_factor
            _retryable = retryable_exceptions or (
                ElementStaleError,
                ElementNotClickableError,
                TimeoutError,
                ConnectionError,
            )

            last_exception = None

            for attempt in range(_max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except _retryable as e:
                    last_exception = e
                    if attempt < _max_retries:
                        delay = _retry_delay * (_backoff_factor ** attempt)
                        logger.warning(
                            f"重试 {attempt + 1}/{_max_retries}: "
                            f"{func.__name__} - {str(e)} - 等待 {delay:.1f}s"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"重试耗尽: {func.__name__} - {str(e)}")
                        raise

            raise last_exception

        return wrapper

    def execute_with_retry(self, func: Callable, *args,
                           max_retries: int = None,
                           retry_delay: float = None,
                           backoff_factor: float = None,
                           **kwargs) -> Any:
        """
        执行函数并在失败时重试

        Args:
            func: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数
            retry_delay: 重试延迟
            backoff_factor: 退避因子
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数返回值
        """
        _max_retries = max_retries or self.max_retries
        _retry_delay = retry_delay or self.retry_delay
        _backoff_factor = backoff_factor or self.backoff_factor

        last_exception = None

        for attempt in range(_max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if not self.should_retry(e) or attempt >= _max_retries:
                    raise
                delay = _retry_delay * (_backoff_factor ** attempt)
                logger.warning(
                    f"重试 {attempt + 1}/{_max_retries}: "
                    f"{func.__name__} - {str(e)} - 等待 {delay:.1f}s"
                )
                time.sleep(delay)

        raise last_exception


class RecoveryManager:
    """
    恢复管理器
    提供异常恢复策略
    """

    def __init__(self, driver_getter: Callable = None):
        """
        初始化恢复管理器

        Args:
            driver_getter: 获取driver的回调函数
        """
        self.driver_getter = driver_getter
        self.exception_handler = ExceptionHandler()

    def recover_from_element_stale(self, locator: tuple = None) -> bool:
        """
        从元素过时异常中恢复

        Args:
            locator: 元素定位器

        Returns:
            bool: 是否恢复成功
        """
        logger.info(f"尝试从元素过时中恢复: {locator}")
        try:
            driver = self.driver_getter() if self.driver_getter else None
            if driver:
                driver.execute_script("mobile: refresh")
                logger.info("页面状态已刷新")
                return True
        except Exception as e:
            logger.error(f"恢复失败: {e}")
        return False

    def recover_from_page_load_timeout(self, page_name: str = None) -> bool:
        """
        从页面加载超时中恢复

        Args:
            page_name: 页面名称

        Returns:
            bool: 是否恢复成功
        """
        logger.info(f"尝试从页面加载超时中恢复: {page_name}")
        try:
            driver = self.driver_getter() if self.driver_getter else None
            if driver:
                driver.back()
                time.sleep(1)
                logger.info("已返回上一页")
                return True
        except Exception as e:
            logger.error(f"恢复失败: {e}")
        return False

    def attempt_recovery(self, exception: Exception) -> bool:
        """
        尝试从异常中恢复

        Args:
            exception: 异常对象

        Returns:
            bool: 是否恢复成功
        """
        if isinstance(exception, ElementStaleError):
            return self.recover_from_element_stale(
                exception.details.get('locator')
            )
        elif isinstance(exception, PageLoadTimeoutError):
            return self.recover_from_page_load_timeout(
                exception.details.get('page_name')
            )
        elif isinstance(exception, DriverSessionExpiredError):
            logger.warning("检测到会话过期，需要重新创建会话")
            return False
        return False


# 全局实例
global_exception_handler = ExceptionHandler()
global_retry_handler = RetryHandler()
global_recovery_manager = RecoveryManager()