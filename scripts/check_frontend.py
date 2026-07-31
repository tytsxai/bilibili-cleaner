#!/usr/bin/env python3
"""前端静态自检。

Web UI 是纯静态 HTML/CSS/JS，没有构建步骤，也就没有任何东西会在改错时报错：
index.html 里删掉一个 id，app.js 会在运行时抛 TypeError，而 CI 全绿。
这个脚本补上最低限度的门禁，只检查会直接导致页面崩坏的几类问题：

1. app.js 里 getElementById 的每个 id 都必须存在于 index.html
2. HTML 标签闭合正确
3. <use href="#..."> 引用的图标 symbol 都存在
4. style.css 里用到的每个 var(--x) 都有定义

用法：python scripts/check_frontend.py
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
    # SVG 里在本项目中始终自闭合的元素
    "path", "circle", "rect", "use", "polygon", "line", "ellipse",
}


class TagBalanceChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, int]] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag: str, attrs: object) -> None:
        return

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        if not self.stack:
            self.errors.append(f"第 {self.getpos()[0]} 行：多余的 </{tag}>")
            return
        open_tag, line = self.stack.pop()
        if open_tag != tag:
            self.errors.append(
                f"第 {self.getpos()[0]} 行：</{tag}> 与第 {line} 行的 <{open_tag}> 不匹配"
            )


def check() -> list[str]:
    problems: list[str] = []

    html_path = FRONTEND / "index.html"
    js_path = FRONTEND / "app.js"
    css_path = FRONTEND / "style.css"
    for path in (html_path, js_path, css_path):
        if not path.exists():
            problems.append(f"缺少前端文件：{path}")
    if problems:
        return problems

    html = html_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")

    # 1. id 契约
    html_ids = set(re.findall(r'\bid="([^"]+)"', html))
    js_ids = set(re.findall(r'getElementById\("([^"]+)"\)', js))
    for missing in sorted(js_ids - html_ids):
        problems.append(f'app.js 引用了 index.html 中不存在的 id："{missing}"')

    # 2. 标签闭合
    checker = TagBalanceChecker()
    checker.feed(html)
    problems.extend(f"index.html {error}" for error in checker.errors)
    for tag, line in checker.stack:
        problems.append(f"index.html 第 {line} 行：<{tag}> 未闭合")

    # 3. 图标 symbol
    symbols = set(re.findall(r'<symbol id="([^"]+)"', html))
    referenced = set(re.findall(r'href="#([^"]+)"', html))
    for missing in sorted(referenced - symbols):
        problems.append(f'index.html 引用了未定义的图标 symbol："#{missing}"')
    for unused in sorted(symbols - referenced):
        problems.append(f'index.html 定义了无人引用的图标 symbol："#{unused}"')

    # 4. CSS 变量
    defined = set(re.findall(r'^\s*(--[\w-]+)\s*:', css, re.MULTILINE))
    used = set(re.findall(r'var\((--[\w-]+)', css))
    for missing in sorted(used - defined):
        problems.append(f"style.css 使用了未定义的变量：{missing}")

    return problems


def main() -> int:
    problems = check()
    if problems:
        print("前端自检未通过：")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("前端自检通过：id 契约、标签闭合、图标引用、CSS 变量均一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
