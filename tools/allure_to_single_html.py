#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 Allure 报告合并为单个 HTML 文件
通过内联 CSS/JS 和数据 JSON，解决 file:// 协议下的 Loading... 问题

用法:
    python tools/allure_to_single_html.py <allure-report目录> [输出文件路径]

示例:
    python tools/allure_to_single_html.py reports/allure-report reports/standalone_report.html
"""

import os
import sys
import json
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


def collect_data_files(base_dir: str) -> dict:
    """
    收集 data 目录下的所有 JSON 数据文件

    Args:
        base_dir: Allure 报告目录

    Returns:
        dict: {文件名: 文件内容}
    """
    data_dir = os.path.join(base_dir, 'data')
    data_files = {}

    if not os.path.exists(data_dir):
        return data_files

    for filename in os.listdir(data_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data_files[filename] = f.read()
            except (IOError, UnicodeDecodeError):
                # 尝试二进制读取
                try:
                    with open(filepath, 'rb') as f:
                        data_files[filename] = base64.b64encode(f.read()).decode('utf-8')
                except IOError:
                    pass

    return data_files


def inline_fetch_data(html: str, data_files: dict) -> str:
    """
    重写 fetch/XHR 请求，从内联数据中读取

    在 HTML 中注入拦截器，将 fetch 请求重定向到内联数据。
    """
    if not data_files:
        return html

    # 将数据文件注入为 JavaScript 对象
    data_js = json.dumps(data_files, ensure_ascii=False)

    interceptor = f"""
<script>
(function() {{
    // 内联的 Allure 数据
    var __ALLURE_DATA__ = {data_js};

    // 拦截 fetch 请求
    var originalFetch = window.fetch;
    window.fetch = function(url, options) {{
        var urlStr = String(url);

        // 提取文件名
        var parts = urlStr.split('/');
        var filename = parts[parts.length - 1].split('?')[0];

        // 检查是否在数据中
        if (filename in __ALLURE_DATA__) {{
            console.log('从内联数据加载: ' + filename);
            return Promise.resolve(new Response(__ALLURE_DATA__[filename], {{
                status: 200,
                headers: {{'Content-Type': 'application/json'}}
            }}));
        }}

        // 尝试完整路径匹配
        for (var key in __ALLURE_DATA__) {{
            if (urlStr.indexOf(key) !== -1) {{
                console.log('从内联数据加载(路径匹配): ' + key);
                return Promise.resolve(new Response(__ALLURE_DATA__[key], {{
                    status: 200,
                    headers: {{'Content-Type': 'application/json'}}
                }}));
            }}
        }}

        // 原始请求
        return originalFetch.apply(this, arguments);
    }};

    // 拦截 XMLHttpRequest
    var originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {{
        var urlStr = String(url);
        var parts = urlStr.split('/');
        var filename = parts[parts.length - 1].split('?')[0];

        if (filename in __ALLURE_DATA__) {{
            this.__allureData__ = __ALLURE_DATA__[filename];
        }}

        return originalOpen.apply(this, arguments);
    }};

    var originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(body) {{
        if (this.__allureData__) {{
            var self = this;
            setTimeout(function() {{
                Object.defineProperty(self, 'responseText', {{
                    value: self.__allureData__,
                    writable: false
                }});
                Object.defineProperty(self, 'response', {{
                    value: self.__allureData__,
                    writable: false
                }});
                Object.defineProperty(self, 'status', {{
                    value: 200,
                    writable: false
                }});
                Object.defineProperty(self, 'readyState', {{
                    value: 4,
                    writable: false
                }});

                if (self.onreadystatechange) {{
                    self.onreadystatechange();
                }}
                if (self.onload) {{
                    self.onload();
                }}
            }}, 0);
            return;
        }}

        return originalSend.apply(this, arguments);
    }};
}})();
</script>
"""
    html = html.replace('</head>', interceptor + '</head>')
    return html


def inline_all(html: str, base_dir: str) -> str:
    """依次内联 CSS、JS、图片、数据"""
    print("  内联 CSS...")
    html = inline_css(html, base_dir)

    print("  内联 JS...")
    html = inline_js(html, base_dir)

    print("  内联图片...")
    html = inline_images(html, base_dir)

    print("  收集数据文件...")
    data_files = collect_data_files(base_dir)
    print(f"  找到 {len(data_files)} 个数据文件")

    print("  注入数据拦截器...")
    html = inline_fetch_data(html, data_files)

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

    print("开始内联资源...")
    html = inline_all(html, report_dir)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\n单文件报告已生成: {output_file} ({file_size:.2f} MB)")
    print("可直接双击打开，无需服务器。")


if __name__ == '__main__':
    main()