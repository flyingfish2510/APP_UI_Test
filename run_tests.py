#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试运行入口
支持单设备和多设备测试执行
兼容本地Windows和Docker中Jenkins环境
"""

import os
import sys
import argparse
import subprocess
from typing import List

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.logger import get_logger
from core.utils import Utils
from core.exceptions import ConfigFileNotFoundError

logger = get_logger(__name__)


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.project_root = project_root
        self.results_dir = os.path.join(self.project_root, 'reports', 'allure-results')
        self.report_dir = os.path.join(self.project_root, 'reports', 'allure-report')
        self.log_dir = os.path.join(self.project_root, 'logs')
        Utils.ensure_dir(self.results_dir)
        Utils.ensure_dir(self.log_dir)

    @staticmethod
    def parse_args() -> argparse.Namespace:
        """解析命令行参数"""
        parser = argparse.ArgumentParser(description='移动端自动化测试运行器')

        parser.add_argument('-m', '--markers', type=str, default=None, help='测试标记过滤')
        parser.add_argument('-k', '--keyword', type=str, default=None, help='测试用例名称关键字过滤')
        parser.add_argument('-d', '--device-index', type=int, default=0, help='设备索引，默认为0')
        parser.add_argument('--multi-device', action='store_true', help='是否多设备并行执行')
        parser.add_argument('-n', '--parallel', type=int, default=1, help='并行执行的进程数')
        parser.add_argument('--env', type=str, choices=['local', 'docker'], default=None, help='运行环境')
        parser.add_argument('--no-report', action='store_true', help='不生成Allure报告')
        parser.add_argument('--open-report', action='store_true', help='生成报告后自动打开')
        parser.add_argument('--clean-reports', action='store_true', help='清理旧的测试报告')
        parser.add_argument('--log-level', type=str, default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        parser.add_argument('--no-screenshot', action='store_true', help='禁用失败截图')
        parser.add_argument('--reruns', type=int, default=0, help='失败重试次数')
        parser.add_argument('--maxfail', type=int, default=5, help='最大失败数后停止')
        parser.add_argument('--timeout', type=int, default=300, help='单个测试超时时间（秒）')
        parser.add_argument('--case-file', type=str, default=None, help='用例列表文件路径')
        parser.add_argument('--no-single-file', action='store_true', help='不生成单文件HTML报告')

        return parser.parse_args()

    def build_pytest_command(self, args: argparse.Namespace) -> List[str]:
        """构建Pytest命令行"""
        cmd = ['pytest']

        case_file = args.case_file or "test_cases.txt"

        if os.path.exists(case_file):
            with open(case_file, 'r', encoding='utf-8') as f:
                case_names = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if case_names:
                cmd.extend(['-k', ' or '.join(case_names)])

        if args.markers:
            cmd.extend(['-m', args.markers])
        if args.keyword:
            cmd.extend(['-k', args.keyword])

        test_path = os.path.join(self.project_root, 'testcases')
        cmd.append(test_path)

        cmd.extend(['--alluredir', self.results_dir, '--clean-alluredir'])
        cmd.extend(['--log-level', args.log_level])
        cmd.extend(['--device-index', str(args.device_index)])

        if args.no_screenshot:
            cmd.append('--no-screenshot')
        if args.env:
            os.environ['RUN_ENV'] = args.env
            cmd.extend(['--run-env', args.env])

        return cmd

    def run_tests(self, args: argparse.Namespace) -> int:
        """执行测试"""
        cmd = self.build_pytest_command(args)

        logger.info("=" * 60)
        logger.info(f"项目路径: {self.project_root}")
        logger.info(f"运行环境: {args.env or os.getenv('RUN_ENV', 'local')}")
        logger.info(f"设备索引: {args.device_index}")
        logger.info(f"测试标记: {args.markers or '全部'}")
        logger.info(f"执行命令: {' '.join(cmd)}")
        logger.info("=" * 60)

        try:
            if args.clean_reports:
                self.clean_reports()

            result = subprocess.run(cmd, cwd=self.project_root)
            exit_code = result.returncode

            if exit_code == 0:
                logger.info("所有测试通过")
            else:
                logger.warning(f"测试执行完毕，退出码: {exit_code}")

            if not args.no_report:
                self.generate_report(args.open_report, args.no_single_file)

            return exit_code
        except KeyboardInterrupt:
            logger.warning("测试被用户中断")
            return 2
        except Exception as e:
            logger.error(f"测试执行异常: {e}")
            return 1

    def generate_single_file_report(self) -> str:
        """
        生成单文件 HTML 报告（用于邮件发送）

        使用 allure-combine 将 Allure 报告合并为单个 HTML 文件。
        本地查看仍使用完整的 Allure 报告，仅邮件发送时使用此单文件。

        Returns:
            str: 单文件报告路径，失败返回 None
        """
        import shutil

        single_file = os.path.join(self.project_root, 'reports', 'complete.html')

        try:
            cmd = f'allure-combine {self.report_dir}'
            logger.info("正在生成单文件报告...")

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                generated_file = os.path.join(self.report_dir, 'complete.html')
                if os.path.exists(generated_file):
                    shutil.move(generated_file, single_file)
                    logger.info(f"单文件报告已生成: {single_file}")
                    return single_file
                else:
                    logger.warning("单文件报告生成失败，未找到 complete.html")
                    return None
            else:
                logger.error(f"生成单文件报告失败: {result.stderr}")
                return None
        except FileNotFoundError:
            logger.error("allure-combine 未安装，请执行: npm install -g allure-combine")
            return None
        except Exception as e:
            logger.error(f"生成单文件报告异常: {e}")
            return None

    def generate_report(self, open_report: bool = False, no_single_file: bool = False):
        """
        生成报告

        Args:
            open_report: 是否自动打开报告
            no_single_file: 是否跳过单文件报告生成
        """
        if not os.path.exists(self.results_dir) or not os.listdir(self.results_dir):
            logger.warning("没有测试结果，跳过报告生成")
            return

        # 1. 生成完整 Allure 报告（本地查看）
        Utils.generate_allure_report(self.results_dir, self.report_dir)

        # 2. 生成单文件报告（邮件发送）
        if not no_single_file:
            self.generate_single_file_report()

        if open_report:
            self.open_report()

    def open_report(self):
        """打开Allure报告"""
        report_index = os.path.join(self.report_dir, 'index.html')
        if os.path.exists(report_index):
            import webbrowser
            webbrowser.open(f'file://{report_index}')
            logger.info("已打开Allure报告")

    def clean_reports(self):
        """清理测试报告"""
        import shutil
        for path in [self.results_dir, self.report_dir]:
            if os.path.exists(path):
                shutil.rmtree(path)
        single_file = os.path.join(self.project_root, 'reports', 'complete.html')
        if os.path.exists(single_file):
            os.remove(single_file)
        Utils.ensure_dir(self.results_dir)

    @staticmethod
    def cleanup():
        """清理测试环境"""
        logger.info("清理测试环境...")


def main():
    runner = TestRunner()
    try:
        args = TestRunner.parse_args()
        exit_code = runner.run_tests(args)
        TestRunner.cleanup()
        sys.exit(exit_code)
    except ConfigFileNotFoundError as e:
        logger.error(f"配置文件错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试运行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()