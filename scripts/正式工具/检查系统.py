#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_FILES = [
    "系统变更说明.md",
    "product-context/01-原型设计规范.md",
    "product-context/02-设计原则库.md",
    "product-context/03-交互模式库.md",
    "product-context/04-文案规范.md",
    "product-context/05-业务术语表.md",
    "product-context/06-监控中心背景地图.md",
    "product-context/07-观测中心背景地图.md",
    "product-context/说明.md",
]

TEMPLATE_FILES = [
    "template/AGENTS.md",
    "template/README.md",
    "template/product-context/说明.md",
]

FORMAL_TOOLS = [
    "scripts/正式工具/整理附件.py",
    "scripts/正式工具/转换产品资料.py",
]

REQUIRED_DIRS = [
    "product-context",
    "template/product-context",
    "附件",
    "scripts/正式工具",
]

OLD_PATTERNS = [
    "component-templates",
    "design-decisions",
    "retrospectives",
    "_template.md",
    "prototype-standards",
    "design-principles",
    "interaction-patterns",
    "copywriting-standards",
    "business-glossary",
    "validation-test",
    "test_v5_",
    "convert_product_docs.py",
    "organize_obsidian_attachments.py",
    "_临时脚本归档",
]

TEXT_SUFFIXES = {".md", ".py", ".js", ".html", ".json", ".txt"}
OFFICE_SUFFIXES = {".docx", ".xlsx", ".xls"}
SKIP_DIR_NAMES = {".git", ".obsidian", ".sisyphus", "node_modules", "__pycache__"}


def clean_stem(path: Path) -> str:
    name = path.name
    while True:
        lower = name.lower()
        changed = False
        for suffix in [".docx", ".xlsx", ".xls"]:
            if lower.endswith(suffix):
                name = name[: -len(suffix)]
                changed = True
                break
        if not changed:
            break
    return name


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path == Path(__file__).resolve():
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def check_path_exists(root: Path, relative_path: str, problems: list[str], passes: list[str]) -> None:
    target = root / relative_path
    if target.exists():
        passes.append(f"存在: {relative_path}")
    else:
        problems.append(f"缺失: {relative_path}")


def check_office_conversion(root: Path, problems: list[str], passes: list[str]) -> None:
    office_root = root / "附件/01-产品资料"
    if not office_root.exists():
        problems.append("缺失: 附件/01-产品资料")
        return

    for office in office_root.rglob("*"):
        if not office.is_file() or office.suffix.lower() not in OFFICE_SUFFIXES:
            continue
        stem = clean_stem(office)
        if office.suffix.lower() == ".docx":
            md_path = office.parent / stem / f"{stem}.md"
        else:
            md_path = office.parent / f"{stem}.md"
        if md_path.exists():
            passes.append(f"已转换: {office.relative_to(root)} -> {md_path.relative_to(root)}")
        else:
            problems.append(f"未转换: {office.relative_to(root)} 缺少 {md_path.relative_to(root)}")


def check_old_patterns(root: Path, problems: list[str], passes: list[str]) -> None:
    hits: list[str] = []
    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in OLD_PATTERNS:
            if pattern in text:
                hits.append(f"{path.relative_to(root)} 包含旧标识: {pattern}")
    if hits:
        problems.extend(hits)
    else:
        passes.append("未发现旧目录名、旧脚本名或旧路径残留")


def check_ds_store(root: Path, problems: list[str], passes: list[str]) -> None:
    ds_files = sorted(root.rglob(".DS_Store"))
    if ds_files:
        problems.extend([f"存在 .DS_Store: {path.relative_to(root)}" for path in ds_files])
    else:
        passes.append("仓库内无 .DS_Store")


def main() -> int:
    parser = argparse.ArgumentParser(description="检查产品设计系统关键结构与引用一致性")
    parser.add_argument("--root", default=".", help="仓库根目录，默认当前目录")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    problems: list[str] = []
    passes: list[str] = []

    for path in REQUIRED_DIRS:
        check_path_exists(root, path, problems, passes)
    for path in ROOT_FILES:
        check_path_exists(root, path, problems, passes)
    for path in TEMPLATE_FILES:
        check_path_exists(root, path, problems, passes)
    for path in FORMAL_TOOLS:
        check_path_exists(root, path, problems, passes)

    check_office_conversion(root, problems, passes)
    check_old_patterns(root, problems, passes)
    check_ds_store(root, problems, passes)

    for item in passes:
        print(f"PASS {item}")
    for item in problems:
        print(f"FAIL {item}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
