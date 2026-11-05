# SC Trans

西班牙语 ⇄ 中文整篇文档翻译技能，支持 **Word (.docx)** 与 **PDF** 双输入双输出。

An agent skill for translating whole documents between Spanish and Chinese, preserving tables, images and layout.

---

## 能力

| 输入 | 输出 | 保留什么 |
|---|---|---|
| `.docx` | `.docx` | 表格、样式、图片位置；中文按规范重排 |
| `.pdf` | `.pdf` | 字号、坐标、线条、图片位置；原地换字 |

- 方向：`es2zh`（西→中）/ `zh2es`（中→西）
- 形态：`full`（全译文）/ `bilingual`（一段原文一段译文）
- 图片：按原版式重绘，只换图内语言
- 文件名：随内容一起翻译

## 安装

```bash
npx skills add https://github.com/<你的用户名>/sc-trans --skill sc-trans
```

或者手动：把整个仓库复制到 Agent 的技能目录

| Agent | 目录 |
|---|---|
| DSH | `~/.dsh/skills/sc-trans/` |
| Claude Code | `~/.claude/skills/sc-trans/` |
| Codex | `~/.codex/skills/sc-trans/` |

依赖：

```bash
pip install -r requirements.txt
```

## 中文排版规范（es2zh）

| 层级 | 字体 | 字号 | 加粗 |
|---|---|---|---|
| 一级标题 | 黑体 | 小二 18pt | 是 |
| 二级标题 | 黑体 | 三号 16pt | 是 |
| 三级标题 | 黑体 | 四号 14pt | 是 |
| 四级及以下 | 黑体 | 小四 12pt | 是 |
| 正文 | 仿宋 | 小四 12pt | 否 |

序号：`一、` → `1.` → `1）` → `①`，不出现字母编号。文末附日期。

## 用法

**Word**

```bash
python scripts/extract.py --src 报告.docx --work ./_work
# 填 _work/translations.json
python scripts/apply.py  --src 报告.docx --work ./_work \
       --dir es2zh --mode full --filename "中文名.docx"
python scripts/images.py replace --docx "中文名.docx" --work ./_work
python scripts/verify.py --docx "中文名.docx" --work ./_work --dir es2zh
```

**PDF**

```bash
python scripts/pdf_extract.py --src 报告.pdf --work ./_work
# 填 _work/translations.json
python scripts/pdf_apply.py   --src 报告.pdf --work ./_work --lang zh --out "中文名.pdf"
python scripts/pdf_images.py  replace --pdf "中文名.pdf" --work ./_work
python scripts/pdf_verify.py  --pdf "中文名.pdf" --work ./_work
```

## 术语（强制）

| 原文 | 译文 |
|---|---|
| Ecuacorriente S.A. / ECSA | ECSA |
| Mirador（矿区） | 米拉多铜矿 |
| Zhu Jun | 朱钧 |

完整词表见 `references/glossary.md`。

## 结构

```
sc-trans/
├── SKILL.md                  技能主文件
├── requirements.txt
├── references/
│   ├── glossary.md           术语表（政治/选举/矿业）
│   └── rebuild-image.md      图片重绘方法
└── scripts/
    ├── extract.py            docx 拆解
    ├── apply.py              docx 回填 + 排版 + 序号 + 日期
    ├── images.py             docx 图片替换
    ├── verify.py             docx 自检
    ├── pdf_extract.py        PDF 拆解
    ├── pdf_apply.py          PDF 原地换字
    ├── pdf_images.py         PDF 图片替换
    └── pdf_verify.py         PDF 自检
```

## 限制

- **Windows 专用**：字体路径写死为 `C:\Windows\Fonts\`，Mac/Linux 需改 `apply.py` 的 `HEI/FANGSONG` 与 `pdf_apply.py` 的 `CJK_FONT`。
- **扫描版 PDF** 无文字层，只能整页重绘或加图注。
- **复杂 PDF 版式**（多栏、竖排、旋转）按块处理会错位，需人工校。
- **Word 域代码**（目录、交叉引用）译后需按 F9 更新。
- 图片重绘是"同一版式语言"，不是像素级复刻。

## 许可

未指定。使用前请与作者确认。
