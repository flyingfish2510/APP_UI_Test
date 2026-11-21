#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""从 Jenkins 更新中心解析插件依赖闭包，生成 docker/plugins.lock。

用法:
    python scripts/gen_plugins_lock.py [更新中心URL]

修改 docker/plugins.txt 后重新执行，再 docker compose build。
"""
import json
import sys
from collections import deque
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UC = "https://mirrors.huaweicloud.com/jenkins/update-center.json"


def main() -> int:
    uc = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_UC
    text = requests.get(uc, timeout=120).text

    # 更新中心内容是 updateCenter.post({...}) 包装的 JS，截取第一个完整 JSON 对象
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(text[text.index("{"):])
    plugins = obj["plugins"]

    requested = [
        line.strip()
        for line in (ROOT / "docker" / "plugins.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    resolved = {}
    queue = deque(requested)
    missing = set()
    while queue:
        name = queue.popleft()
        if name in resolved:
            continue
        plugin = plugins.get(name)
        if plugin is None:
            missing.add(name)
            continue
        resolved[name] = plugin
        for dep in plugin.get("dependencies", []):
            if not dep.get("optional") and dep["name"] not in resolved:
                queue.append(dep["name"])

    out = ROOT / "docker" / "plugins.lock"
    lines = ["# name|version|url (resolved from update-center.json)"]
    for name in sorted(resolved):
        url = resolved[name]["url"].replace("http://", "https://")
        lines.append(f'{name}|{resolved[name]["version"]}|{url}')
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"resolved {len(resolved)} plugins -> {out}")
    if missing:
        print("missing:", sorted(missing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
