---
name: sc-trans
description: "SC Trans —— 西班牙语 ⇄ 中文整篇文档互译，支持 Word(.docx) 与 PDF 双输入双输出；保留表格/图片/版式，按中文规范重排（黑体加粗小二标题、仿宋小四正文、一、/1./1）三级序号），图片按原样式重绘只换语言，译文另存并翻译文件名。Triggers: 西语翻译, 西班牙语文档翻译, traducir al chino, traducir al español, 中文译西语, Word 翻译, PDF 翻译, docx 翻译, SC Trans。"
---

# SC Trans

西班牙语 ⇄ 中文的整篇文档翻译。**输入什么，输出什么**：

| 输入 | 输出 | 版式处理 |
|---|---|---|
| `.docx` | `.docx` | 表格、样式、图片位置全部保留 |
| `.pdf` | `.pdf` | 字号、坐标、图形、图片位置全部保留 |

两个方向：`es2zh`（西→中，按中文规范重排）｜`zh2es`（中→西，西语用默认格式）。
两种形态：`full`（全译文，默认）｜`bilingual`（一段原文一段译文）。

---

## 一、开始前只问两件事

1. **输出形态**：全译文 / 对照
2. **目标文件名**（不给我就取文内大标题）

其余默认：西→中日期放**文末右对齐**；中→西日期放**文首左对齐**且文末不加日期。

---

## 二、词表（强制）

| 原文 | 译文 |
|---|---|
| Ecuacorriente S.A. / ECSA | **ECSA** |
| Mirador（矿区） | **米拉多铜矿** |
| Zhu Jun | **朱钧** |

完整词表见 `references/glossary.md`。同一个词全篇只能有一种译法。

---

## 三、中文排版规范（仅 es2zh）

| 层级 | 字体 | 字号 | 加粗 |
|---|---|---|---|
| 一级标题 | 黑体 | 小二 18pt | 是 |
| 二级标题 | 黑体 | 三号 16pt | 是 |
| 三级标题 | 黑体 | 四号 14pt | 是 |
| 四级及以下 | 黑体 | 小四 12pt | 是 |
| 正文 | 仿宋 | 小四 12pt | 否 |

斜体等行内属性沿用原文；对齐、缩进、行距不动。
**zh2es 时整张表不适用**，西语一律用默认样式。

### 序号

```
一级 一、二、    二级 1. 2.    三级 1）2）    四级 ①②
```

原文的 `1.` `1.1` `a)` `A.` `I.` `•` 自动识别层级并改写；**不出现字母编号**。
标题字号跟着它在编号体系里的层级走（`1.` 开头的标题 → `一、` + 18pt）。

---

## 四、图片

- 尺寸、位置、比例**一律不动**，只换图内语言。
- 位图必须**按原图重绘**：读配色/结构/字号 → PIL 复刻 → 换成译文。方法见 `references/rebuild-image.md`。
- 重绘文件**沿用原文件名**放回 `_work/images/`，替换脚本按名字/顺序命中。
- ⚠️ **不要重跑 extract**，它会用原图覆盖你重绘的结果。

---

## 五、Word 流程

```bash
python scripts/extract.py --src 报告.docx --work ./_work        # 拆解
# 按 _work/preview.txt 填 _work/translations.json（表格见下）
python scripts/apply.py  --src 报告.docx --work ./_work \
       --dir es2zh --mode full --filename "中文名.docx"
python scripts/images.py replace --docx "中文名.docx" --work ./_work   # 有重绘图片时
python scripts/verify.py --docx "中文名.docx" --work ./_work --dir es2zh
```

表格译文按单元格给，`preview.txt` 里的键形如 `[7.r0c2p1]`（第7块・行・列・段）：

```json
"7": { "rows": [ ["单段格", ["第一段","第二段"]], ["下一行…"] ] }
```

## 六、PDF 流程

```bash
python scripts/pdf_extract.py --src 报告.pdf --work ./_work     # 按文本块拆
# 填 _work/translations.json，键是块 id（p0b0、p0b1…）
python scripts/pdf_apply.py   --src 报告.pdf --work ./_work --lang zh --out "中文名.pdf"
python scripts/pdf_images.py list --work ./_work                 # 看内嵌图
python scripts/pdf_images.py replace --pdf "中文名.pdf" --work ./_work
python scripts/pdf_verify.py --pdf "中文名.pdf" --work ./_work
```

原理：先按块 `redact` 掉原文（**保留线稿与图片**），再用中文字体在**原 bbox** 内重排，字号自动从原字号往下试到塞得进为止。

---

## 七、翻译硬性要求

1. **逐块/逐段对应**，键必须覆盖 `preview.txt` 里每一条，漏一条就缺一段。
2. **日期、数字、百分比、机构缩写原样搬**，不要重算。
3. **不要自己加序号**——脚本会重排。
4. **专有名词首现给缩写**：`公民参与与社会监督委员会（CPCCS）`，后文只用 CPCCS。
5. **语气**：公文/分析报告体，不用口语，不加评论。

---

## 八、自检

`verify.py`（docx）查：字体字号、序号、表格数、图片比例、术语、文末/文首日期。
`pdf_verify.py` 查：页数、残留源语言、图片数。

人工再过一眼：标题层级对不对、译文有没有压在图上、长句有没有溢出。

---

## 九、限制（先跟用户说清）

- **扫描版 PDF** 没有文字层，只能整页当图片处理（重绘或加图注）。
- **PDF 复杂排版**（多栏混排、竖排、旋转文字）按块处理可能错位，需人工校。
- **Word 域代码**（自动目录、交叉引用）译后需在 Word 里按 F9 更新。
- **文本框**内容 python-docx 读不到，`extract.py` 会报 `textboxes` 计数。
- 图片重绘是"同一版式语言"，不是像素级复刻。
