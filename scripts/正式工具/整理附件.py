#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tiff"}
MARKDOWN_PATTERN = re.compile(r'(!?\[[^\]]*\]\()(<)?([^)<>]+)(>)?(\))')
WIKILINK_PATTERN = re.compile(r'(!?\[\[)([^\]]+)(\]\])')
SKIP_DIRS = {".git", ".obsidian", ".trash"}


def iter_markdown_files(vault_root: Path):
    for path in vault_root.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def normalize_target(target: str) -> str:
    target = target.strip()
    if "|" in target:
        target = target.split("|", 1)[0]
    return target.strip()


def find_referencing_notes(vault_root: Path, image_name: str) -> list[Path]:
    refs: list[Path] = []
    for note in iter_markdown_files(vault_root):
        text = note.read_text(encoding="utf-8")
        if image_name not in text:
            continue
        found = False
        for match in MARKDOWN_PATTERN.finditer(text):
            target = normalize_target(match.group(3))
            if Path(target).name == image_name:
                found = True
                break
        if not found:
            for match in WIKILINK_PATTERN.finditer(text):
                target = normalize_target(match.group(2))
                if Path(target).name == image_name:
                    found = True
                    break
        if found:
            refs.append(note)
    return refs


def determine_target_dir(note: Path) -> Path:
    parts = note.parts

    if parts[0] == "附件":
        return note.parent / "media"

    if parts[0].startswith("v") and len(parts) >= 4:
        return Path("附件/03-需求参考").joinpath(*parts[1:-1])

    if parts[0] == "product-context" and "需求复盘" in parts:
        stem = note.stem
        if stem.endswith("-复盘"):
            stem = stem[:-3]
        return Path("附件/04-复盘配图") / stem

    return Path("附件/99-待整理/按文档归档") / note.stem


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def replace_links(text: str, image_name: str, markdown_path: str, wikilink_path: str) -> str:
    def replace_markdown(match: re.Match[str]) -> str:
        prefix, left_angle, target, right_angle, suffix = match.groups()
        clean_target = normalize_target(target)
        if Path(clean_target).name != image_name:
            return match.group(0)
        wrapped = f"<{markdown_path}>" if left_angle or right_angle else markdown_path
        return f"{prefix}{wrapped}{suffix}"

    def replace_wikilink(match: re.Match[str]) -> str:
        prefix, target, suffix = match.groups()
        clean_target = normalize_target(target)
        if Path(clean_target).name != image_name:
            return match.group(0)
        alias = ""
        if "|" in target:
            alias = "|" + target.split("|", 1)[1]
        return f"{prefix}{wikilink_path}{alias}{suffix}"

    text = MARKDOWN_PATTERN.sub(replace_markdown, text)
    text = WIKILINK_PATTERN.sub(replace_wikilink, text)
    return text


def move_image(vault_root: Path, image_path: Path, target_dir: Path, dry_run: bool) -> Path:
    absolute_target_dir = vault_root / target_dir
    absolute_target_dir.mkdir(parents=True, exist_ok=True)
    if image_path.parent == absolute_target_dir:
        return image_path
    destination = unique_destination(absolute_target_dir / image_path.name)
    if not dry_run:
        shutil.move(str(image_path), str(destination))
    return destination


def process_image(vault_root: Path, image_path: Path, dry_run: bool) -> tuple[str, str]:
    refs = find_referencing_notes(vault_root, image_path.name)

    if len(refs) == 1:
        note_rel = refs[0].relative_to(vault_root)
        target_dir = determine_target_dir(note_rel)
        reason = f"按引用文档归档: {note_rel.as_posix()}"
    elif len(refs) == 0:
        target_dir = Path("附件/99-待整理/收件箱")
        reason = "未找到引用，保留在收件箱"
    else:
        target_dir = Path("附件/99-待整理/多处引用")
        reason = f"存在 {len(refs)} 处引用，转入人工处理区"

    destination = move_image(vault_root, image_path, target_dir, dry_run)

    for note in refs:
        text = note.read_text(encoding="utf-8")
        markdown_rel = destination.relative_to(vault_root)
        markdown_path = os.path.relpath(destination, start=note.parent).replace(os.sep, "/")
        wikilink_path = markdown_rel.as_posix()
        updated = replace_links(text, image_path.name, markdown_path, wikilink_path)
        if updated != text and not dry_run:
            note.write_text(updated, encoding="utf-8")

    return destination.relative_to(vault_root).as_posix(), reason


def main():
    parser = argparse.ArgumentParser(description="整理 Obsidian 截图附件")
    parser.add_argument(
        "--source",
        default="附件/99-待整理/收件箱",
        help="待整理图片所在目录，默认使用 Obsidian 截图收件箱",
    )
    parser.add_argument("--dry-run", action="store_true", help="只输出结果，不实际修改文件")
    args = parser.parse_args()

    vault_root = Path.cwd()
    source_dir = (vault_root / args.source).resolve()

    if not source_dir.exists():
        print(f"source directory not found: {source_dir}")
        raise SystemExit(1)

    images = [
        path
        for path in sorted(source_dir.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not images:
        print("no images to organize")
        return

    for image in images:
        destination, reason = process_image(vault_root, image, args.dry_run)
        action = "would move" if args.dry_run else "moved"
        print(f"{action}: {image.relative_to(vault_root).as_posix()} -> {destination} | {reason}")


if __name__ == "__main__":
    main()
