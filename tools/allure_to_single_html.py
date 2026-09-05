#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 Allure 报告合并为单个自包含 HTML 文件
支持 CSS/JS/数据 JSON/附件（截图、日志）全部内联

用法:
    python tools/allure_to_single_html.py <allure-report目录> [输出文件]
"""

import os
import sys
import json
import base64
import re


MIME_MAP = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
    'svg': 'image/svg+xml',
    'ico': 'image/x-icon',
    'webp': 'image/webp',
    'txt': 'text/plain',
    'log': 'text/plain',
    'json': 'application/json',
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'csv': 'text/csv',
    'xml': 'application/xml',
    'html': 'text/html',
}


def inline_css(html: str, base_dir: str) -> str:
    """内联所有 CSS"""
    def replace(match):
        css_path = match.group(1)
        full_path = os.path.join(base_dir, css_path.lstrip('./').lstrip('/'))
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f'<style>{f.read()}</style>'
        return match.group(0)

    return re.sub(r'<link[^>]*href="([^"]*\.css)"[^>]*/?>', replace, html)


def inline_js(html: str, base_dir: str) -> str:
    """内联所有 JS"""
    def replace(match):
        js_path = match.group(1)
        full_path = os.path.join(base_dir, js_path.lstrip('./').lstrip('/'))
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return f'<script>{f.read()}</script>'
        return match.group(0)

    return re.sub(r'<script[^>]*src="([^"]*\.js)"[^>]*></script>', replace, html)


def inline_static_images(html: str, base_dir: str) -> str:
    """内联 HTML 中直接引用的图片"""
    def replace(match):
        img_path = match.group(1)
        ext = os.path.splitext(img_path)[1].lstrip('.').lower()
        full_path = os.path.join(base_dir, img_path.lstrip('./').lstrip('/'))
        if os.path.exists(full_path) and ext in MIME_MAP:
            with open(full_path, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
            return f'src="data:{MIME_MAP[ext]};base64,{data}"'
        return match.group(0)

    return re.sub(
        r'src="([^"]*\.(png|jpg|jpeg|gif|svg|ico|webp))"',
        replace, html
    )


def collect_data_files(base_dir: str) -> dict:
    """
    递归收集 data 目录下所有文件
    返回: {相对路径: {content, type, mime}}
    """
    data_dir = os.path.join(base_dir, 'data')
    result = {}

    if not os.path.exists(data_dir):
        return result

    for root, _, files in os.walk(data_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, base_dir).replace('\\', '/')
            ext = os.path.splitext(filename)[1].lstrip('.').lower()

            if filename.endswith('.json'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        result[rel_path] = {
                            'content': f.read(),
                            'type': 'json',
                            'mime': 'application/json'
                        }
                except (IOError, UnicodeDecodeError):
                    with open(filepath, 'rb') as f:
                        result[rel_path] = {
                            'content': base64.b64encode(f.read()).decode('utf-8'),
                            'type': 'binary',
                            'mime': 'application/json'
                        }
            else:
                mime = MIME_MAP.get(ext, 'application/octet-stream')
                try:
                    with open(filepath, 'rb') as f:
                        result[rel_path] = {
                            'content': base64.b64encode(f.read()).decode('utf-8'),
                            'type': 'binary',
                            'mime': mime
                        }
                except IOError:
                    pass

    return result


def build_interceptor(data_files: dict) -> str:
    """构建 JS 拦截器，拦截 fetch/XHR 从内联数据返回"""
    if not data_files:
        return ''

    data_js = json.dumps(data_files, ensure_ascii=False)

    return f"""
<script>
(function() {{
    var __ALLURE_DATA__ = {data_js};

    function normalizePath(url) {{
        var urlStr = String(url).split('?')[0].split('#')[0];
        var idx = urlStr.indexOf('data/');
        if (idx !== -1) return urlStr.substring(idx);
        idx = urlStr.indexOf('attachments/');
        if (idx !== -1) return 'data/' + urlStr.substring(idx);
        return urlStr;
    }}

    function findData(url) {{
        var path = normalizePath(url);
        if (path in __ALLURE_DATA__) return __ALLURE_DATA__[path];

        var withData = 'data/' + path;
        if (withData in __ALLURE_DATA__) return __ALLURE_DATA__[withData];

        var filename = path.split('/').pop();
        for (var key in __ALLURE_DATA__) {{
            if (key.endsWith(filename)) return __ALLURE_DATA__[key];
        }}
        return null;
    }}

    function b64ToBytes(b64) {{
        var bin = atob(b64);
        var arr = new Uint8Array(bin.length);
        for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        return arr;
    }}

    function makeResponse(info) {{
        if (info.type === 'json') {{
            return new Response(info.content, {{
                status: 200,
                headers: {{'Content-Type': 'application/json'}}
            }});
        }}
        return new Response(b64ToBytes(info.content), {{
            status: 200,
            headers: {{'Content-Type': info.mime || 'application/octet-stream'}}
        }});
    }}

    var origFetch = window.fetch;
    window.fetch = function(url, opts) {{
        var d = findData(url);
        if (d) return Promise.resolve(makeResponse(d));
        return origFetch.apply(this, arguments);
    }};

    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {{
        this.__data = findData(url);
        return origOpen.apply(this, arguments);
    }};
    XMLHttpRequest.prototype.send = function(body) {{
        var self = this;
        if (this.__data) {{
            var info = this.__data;
            setTimeout(function() {{
                try {{
                    var content = info.type === 'json' ? info.content : b64ToBytes(info.content);
                    Object.defineProperty(self, 'responseText', {{value: info.type === 'json' ? content : '', writable: false}});
                    Object.defineProperty(self, 'response', {{value: content, writable: false}});
                    Object.defineProperty(self, 'status', {{value: 200, writable: false}});
                    Object.defineProperty(self, 'statusText', {{value: 'OK', writable: false}});
                    Object.defineProperty(self, 'readyState', {{value: 4, writable: false}});
                    if (self.onreadystatechange) self.onreadystatechange();
                    if (self.onload) self.onload();
                    if (self.onloadend) self.onloadend();
                }} catch (e) {{ console.error(e); }}
            }}, 0);
            return;
        }}
        return origSend.apply(this, arguments);
    }};
}})();
</script>
"""


def main():
    if len(sys.argv) < 2:
        print("用法: python tools/allure_to_single_html.py <allure-report目录> [输出文件]")
        sys.exit(1)

    report_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'reports/standalone_report.html'

    index_path = os.path.join(report_dir, 'index.html')
    if not os.path.exists(index_path):
        print(f"错误: 未找到 {index_path}")
        sys.exit(1)

    print(f"读取: {index_path}")
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()

    print("内联 CSS/JS/静态图片...")
    html = inline_css(html, report_dir)
    html = inline_js(html, report_dir)
    html = inline_static_images(html, report_dir)

    print("收集 data 目录所有数据...")
    data_files = collect_data_files(report_dir)
    print(f"共 {len(data_files)} 个文件")

    print("注入拦截器...")
    interceptor = build_interceptor(data_files)
    html = html.replace('</head>', interceptor + '</head>')

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"已生成: {output_file} ({size_mb:.2f} MB)")


if __name__ == '__main__':
    main()