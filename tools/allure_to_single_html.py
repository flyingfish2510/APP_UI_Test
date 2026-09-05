#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 Allure 报告合并为单个 HTML 文件
适用于邮件发送到手机查看

用法:
    python tools/allure_to_single_html.py <allure-report目录> <输出文件路径>

示例:
    python tools/allure_to_single_html.py reports/allure-report reports/standalone_report.html
"""

import os
import sys
import base64
import re


def inline_css(html: str, base_dir: str) -> str:
    """将 <link href="*.css"> 内联为 <style>"""

    def replace(match):
        css_path = match.group(1)
        full_path = os.path.join(base_dir, css_path.lstrip('./').lstrip('/'))
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f'<style>{f.read()}</style>'
        return match.group(0)

    pattern = r'<link[^>]*href="([^"]*\.css)"[^>]*/?>'
    return re.sub(pattern, replace, html)


def inline_js(html: str, base_dir: str) -> str:
    """将 <script src="*.js"> 内联为 <script>"""

    def replace(match):
        js_path = match.group(1)
        full_path = os.path.join(base_dir, js_path.lstrip('./').lstrip('/'))
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f'<script>{f.read()}</script>'
        return match.group(0)

    pattern = r'<script[^>]*src="([^"]*\.js)"[^>]*></script>'
    return re.sub(pattern, replace, html)


def inline_images(html: str, base_dir: str) -> str:
    """将 src="*.png/jpg/..." 内联为 base64 data URI"""
    mime_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'ico': 'image/x-icon',
        'webp': 'image/webp',
    }

    def replace(match):
        img_path = match.group(1)
        ext = os.path.splitext(img_path)[1].lstrip('.').lower()
        full_path = os.path.join(base_dir, img_path.lstrip('./').lstrip('/'))

        if os.path.exists(full_path) and ext in mime_map:
            with open(full_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            return f'src="data:{mime_map[ext]};base64,{img_data}"'
        return match.group(0)

    pattern = r'src="([^"]*\.(png|jpg|jpeg|gif|svg|ico|webp))"'
    return re.sub(pattern, replace, html)


def inline_all(html: str, base_dir: str) -> str:
    """依次内联 CSS、JS、图片"""
    html = inline_css(html, base_dir)
    html = inline_js(html, base_dir)
    html = inline_images(html, base_dir)
    return html


def main():
    if len(sys.argv) < 2:
        print("用法: python tools/allure_to_single_html.py <allure-report目录> [输出文件]")
        sys.exit(1)

    report_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'reports/standalone_report.html'

    index_path = os.path.join(report_dir, 'index.html')

    if not os.path.exists(index_path):
        print(f"错误: 未找到 {index_path}")
        print("请先运行: allure generate <results> -o <report>")
        sys.exit(1)

    print(f"读取: {index_path}")
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()

    print("内联 CSS/JS/图片...")
    html = inline_all(html, report_dir)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"单文件报告已生成: {output_file} ({file_size:.2f} MB)")


if __name__ == '__main__':
    main()