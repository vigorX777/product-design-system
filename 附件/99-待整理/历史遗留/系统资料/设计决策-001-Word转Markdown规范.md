# ADR-001: DOCX 转 Markdown 规范

**状态**: 已采纳
**日期**: 2026-02-26
**决策者**: 产品设计系统

## 上下文

将 DOCX 文档（如用户手册）转换为 Markdown 格式以便在 Obsidian 中查阅时，使用 pandoc 默认参数会导致以下问题：

1. **表格格式不兼容**：pandoc 默认输出 `grid_tables`（`+---+` 边框格式），Obsidian 不支持，只认 `pipe_tables`（`| col | col |` 格式）；
2. **复杂表格回退为 HTML**：含 rowspan/colspan 的表格无法用 pipe table 表达，pandoc 会回退输出 `<table>` HTML，Obsidian 虽能渲染但体验差；
3. **图片路径为绝对路径**：pandoc `--extract-media` 输出的图片引用使用绝对路径，Obsidian 无法解析；
4. **pandoc 属性语法**：图片后附带 `{width="..." height="..."}` 属性，Obsidian 不支持该语法；
5. **media 目录嵌套**：`--extract-media` 会在指定目录下再创建 `media/` 子目录，导致路径多一层。

## 决策

### 转换命令

使用以下 pandoc 命令进行转换：

```bash
pandoc "源文件.docx" \
  -t markdown-grid_tables-multiline_tables-simple_tables+pipe_tables \
  --wrap=none \
  --extract-media="附件/{源文件名称}" \
  -o "输出文件.md"
```

参数说明：
- `-t markdown-grid_tables-multiline_tables-simple_tables+pipe_tables`：禁用 grid/multiline/simple 表格，强制使用 pipe tables；
- `--wrap=none`：禁止自动换行，避免长行被截断；
- `--extract-media`：图片提取到 `附件/{源文件名称}/` 目录。

### 后处理脚本

pandoc 转换后，需运行 Python 后处理脚本修复以下问题：

1. **图片路径**：绝对路径 → 相对路径（相对于 md 文件所在目录）；
2. **pandoc 属性**：去除 `{width="..." height="..."}` 语法；
3. **HTML 表格**：将 `<table>` HTML 转换为 pipe table（展平 rowspan/colspan）；
4. **零尺寸图片**：移除 `width="0.0in"` 的占位图片引用（通常是 .tiff 格式）；
5. **多余空行**：合并连续 3 行以上的空行。

### 附件存放规则

图片统一存放在根目录的 `附件/` 文件夹下，以源文件名称作为子文件夹名：

```text
附件/
├── 嘉为蓝鲸观测中心（V4.5）用户手册-V1.0/
│   ├── media/
│   │   ├── image1.png
│   │   ├── image2.png
│   │   └── ...
├── 其他文档名称/
│   └── media/
│       └── ...
```

md 文件中的引用路径格式：`![](附件/{源文件名称}/media/imageN.png)`

**注意**：由于 Obsidian 的附件路径解析是基于 vault 根目录的相对路径，因此统一使用从根目录开始的相对路径。

## 备选方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| 方案 A：pandoc + 后处理脚本（已采纳） | 自动化程度高，可复用 | 需维护后处理脚本 |
| 方案 B：pandoc 默认参数 | 简单，无需额外步骤 | 表格和图片在 Obsidian 中无法正常显示 |
| 方案 C：手动转换 | 格式完全可控 | 耗时巨大，不现实 |

## 后果

**正面影响**:
- DOCX 转换后的 Markdown 在 Obsidian 中可正常渲染表格和图片；
- 附件统一管理，避免散落在各版本目录中。

**负面影响/风险**:
- 含复杂合并单元格的表格展平后，可读性可能略有下降（重复显示合并前的内容）；
- 后处理脚本需要针对新的边界情况持续维护。

## 相关需求

- `v4.5.x/观测中心/嘉为蓝鲸观测中心（V4.5）用户手册-V1.0` — 首次转换实践
