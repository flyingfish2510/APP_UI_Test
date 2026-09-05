#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 Allure 报告合并为单个 HTML 文件
通过内联 CSS/JS/数据 JSON/附件，解决 file:// 协议下的 Loading... 问题

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
        'txt': 'text/plain',
        'json': 'application/json',
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

    pattern = r'src="([^"]*\.(png|jpg|jpeg|gif|svg|ico|webp|txt|json))"'
    return re.sub(pattern, replace, html)


def collect_all_data_files(base_dir: str) -> dict:
    """
    递归收集 data 目录下所有 JSON 数据文件和附件

    Returns:
        dict: {相对路径: {content: str, type: str, mime: str}}
    """
    data_dir = os.path.join(base_dir, 'data')
    data_files = {}

    if not os.path.exists(data_dir):
        return data_files

    mime_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'txt': 'text/plain',
        'log': 'text/plain',
        'json': 'application/json',
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'csv': 'text/csv',
        'xml': 'application/xml',
        'html': 'text/html',
    }

    for root, dirs, files in os.walk(data_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, base_dir).replace('\\', '/')

            if filename.endswith('.json'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data_files[rel_path] = {
                            'content': f.read(),
                            'type': 'json',
                            'mime': 'application/json'
                        }
                except (IOError, UnicodeDecodeError):
                    with open(filepath, 'rb') as f:
                        data_files[rel_path] = {
                            'content': base64.b64encode(f.read()).decode('utf-8'),
                            'type': 'binary',
                            'mime': 'application/json'
                        }
            else:
                ext = os.path.splitext(filename)[1].lstrip('.').lower()
                mime = mime_map.get(ext, 'application/octet-stream')
                try:
                    with open(filepath, 'rb') as f:
                        data_files[rel_path] = {
                            'content': base64.b64encode(f.read()).decode('utf-8'),
                            'type': 'binary',
                            'mime': mime
                        }
                except IOError:
                    pass

    return data_files


def inline_fetch_data(html: str, data_files: dict) -> str:
    """
    重写 fetch/XHR 请求，从内联数据中读取
    支持 JSON 文本和二进制附件
    """
    if not data_files:
        return html

    data_js = json.dumps(data_files, ensure_ascii=False)

    interceptor = f"""
<script>
(function() {{
    var __ALLURE_DATA__ = {data_js};

    function extractPath(url) {{
        var urlStr = String(url);
        var cleanUrl = urlStr.split('?')[0].split('#')[0];

        var dataIndex = cleanUrl.indexOf('data/');
        if (dataIndex !== -1) {{
            return cleanUrl.substring(dataIndex);
        }}

        var attachIndex = cleanUrl.indexOf('attachments/');
        if (attachIndex !== -1) {{
            return 'data/' + cleanUrl.substring(attachIndex);
        }}

        var parts = cleanUrl.split('/');
        var filename = parts[parts.length - 1];

        for (var key in __ALLURE_DATA__) {{
            if (key.endsWith(filename)) {{
                return key;
            }}
        }}

        return filename;
    }}

    function findData(url) {{
        var path = extractPath(url);

        if (path in __ALLURE_DATA__) {{
            return __ALLURE_DATA__[path];
        }}

        var dataPath = 'data/' + path;
        if (dataPath in __ALLURE_DATA__) {{
            return __ALLURE_DATA__[dataPath];
        }}

        var attachPath = 'data/attachments/' + path.split('/').pop();
        if (attachPath in __ALLURE_DATA__) {{
            return __ALLURE_DATA__[attachPath];
        }}

        var filename = path.split('/').pop();
        for (var key in __ALLURE_DATA__) {{
            if (key.endsWith(filename)) {{
                return __ALLURE_DATA__[key];
            }}
        }}

        return null;
    }}

    function base64ToUint8Array(base64) {{
        var binaryString = atob(base64);
        var bytes = new Uint8Array(binaryString.length);
        for (var i = 0; i < binaryString.length; i++) {{
            bytes[i] = binaryString.charCodeAt(i);
        }}
        return bytes;
    }}

    function createResponse(dataInfo) {{
        if (dataInfo.type === 'json') {{
            return new Response(dataInfo.content, {{
                status: 200,
                headers: {{'Content-Type': 'application/json'}}
            }});
        }} else {{
            var bytes = base64ToUint8Array(dataInfo.content);
            var mime = dataInfo.mime || 'application/octet-stream';
            return new Response(bytes, {{
                status: 200,
                headers: {{'Content-Type': mime}}
            }});
        }}
    }}

    var originalFetch = window.fetch;
    window.fetch = function(url, options) {{
        var data = findData(url);
        if (data !== null) {{
            return Promise.resolve(createResponse(data));
        }}
        return originalFetch.apply(this, arguments);
    }};

    var originalOpen = XMLHttpRequest.prototype.open;
    var originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url) {{
        this.__allureData__ = findData(url);
        return originalOpen.apply(this, arguments);
    }};

    XMLHttpRequest.prototype.send = function(body) {{
        if (this.__allureData__ !== null && this.__allureData__ !== undefined) {{
            var self = this;
            var dataInfo = this.__allureData__;

            setTimeout(function() {{
                try {{
                    var content;
                    if (dataInfo.type === 'json') {{
                        content = dataInfo.content;
                    }} else {{
                        content = base64ToUint8Array(dataInfo.content);
                    }}

                    Object.defineProperty(self, 'responseText', {{
                        value: dataInfo.type === 'json' ? content : '',
                        writable: false
                    }});
                    Object.defineProperty(self, 'response', {{
                        value: content,
                        writable: false
                    }});
                    Object.defineProperty(self, 'status', {{
                        value: 200,
                        writable: false
                    }});
                    Object.defineProperty(self, 'statusText', {{
                        value: 'OK',
                        writable: false
                    }});
                    Object.defineProperty(self, 'readyState', {{
                        value: 4,
                        writable: false
                    }});

                    if (self.onreadystatechange) self.onreadystatechange();
                    if (self.onload) self.onload();
                    if (self.onloadend) self.onloadend();
                }} catch (e) {{
                    console.error('XHR 拦截失败:', e);
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

    print("  递归收集数据文件和附件...")
    data_files = collect_all_data_files(base_dir)
    json_count = sum(1 for v in data_files.values() if v['type'] == 'json')
    binary_count = sum(1 for v in data_files.values() if v['type'] == 'binary')
    print(f"  找到 {len(data_files)} 个文件（JSON: {json_count}, 附件: {binary_count}）")

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
    print("包含：用例步骤、失败详情、失败截图")


if __name__ == '__main__':
    main()