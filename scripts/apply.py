#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 3 — 用 translations.json 重建译文文档。

translations.json 支持两种条目：
  段落： {"3": "译文"}
  表格： {"7": {"rows": [["格1","格2"], ["..."]]}}   # 与原文行列一一对应

  python apply.py --src 原文.docx --work _work --dir es2zh --mode full --filename 中文名.docx
"""
import argparse
import copy
import datetime
import json
import os
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.table import Table
from docx.text.paragraph import Paragraph
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HEI, FANGSONG = "黑体", "仿宋"
LATIN_HEI, LATIN_FS = "SimHei", "FangSong"
SIZES = {1: 18.0, 2: 16.0, 3: 14.0, 4: 12.0}   # 小二 / 三号 / 四号 / 小四
BODY_PT = 12.0
CN_NUM = "一二三四五六七八九十"
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

RE_ROMAN = re.compile(r"^\s*([IVXLC]+)[.)、]\s*")
RE_LETTER = re.compile(r"^\s*([A-Za-z])[.)、]\s*")
RE_NUM = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)、]\s*")
RE_BULLET = re.compile(r"^\s*[•·▪◦‣\-–—]\s*")
RE_CIRCLED = re.compile(r"^\s*([①-⑳])\s*")
RE_MARK = (RE_ROMAN, RE_LETTER, RE_NUM, RE_CIRCLED, RE_BULLET)


def cn_number(n):
    if n <= 10:
        return CN_NUM[n - 1]
    if n < 20:
        return "十" + CN_NUM[n - 11]
    if n < 100:
        t, u = divmod(n, 10)
        return CN_NUM[t - 1] + "十" + (CN_NUM[u - 1] if u else "")
    return str(n)


def detect_tier(text):
    """编号层级：1/2/3…；0 = 无编号。
    字母、罗马数字、圈号一律当第三级（输出会变成 1））。"""
    if RE_ROMAN.match(text) or RE_LETTER.match(text) or RE_CIRCLED.match(text):
        return 3
    m = re.match(r"^\s*([\d.]+)", text)
    if m and len(text) > m.end():
        tok = m.group(1).rstrip(".")
        rest = text[m.end():]
        if re.fullmatch(r"\d+(?:\.\d+)*", tok) and rest[:1] in (" ", ")", "、"):
            return tok.count(".") + 1
    return 0


def strip_marker(text):
    for rx in (RE_ROMAN, RE_LETTER, RE_CIRCLED, RE_BULLET):
        m = rx.match(text)
        if m:
            return text[m.end():]
    m = re.match(r"^\s*([\d.]+)\s*[.)、]?\s+", text)
    if m and re.fullmatch(r"\d+(?:\.\d+)*", m.group(1).rstrip(".")):
        return text[m.end():]
    return text


def set_font(run, latin, east, pt, bold):
    run.font.name = latin
    run.font.size = Pt(pt)
    run.font.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), latin)
    rFonts.set(qn("w:hAnsi"), latin)
    rFonts.set(qn("w:eastAsia"), east)


def restyle(p, level):
    if level >= 1:
        pt, bold, latin, east = SIZES.get(min(level, 4), 12.0), True, LATIN_HEI, HEI
    else:
        pt, bold, latin, east = BODY_PT, False, LATIN_FS, FANGSONG
    for r in p.runs:
        keep_italic = r.font.italic
        set_font(r, latin, east, pt, bold)
        if keep_italic is not None:
            r.font.italic = keep_italic


def write_paragraph(p, text):
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(text)


def sanitize(name):
    for ch in '\\/:*?"<>|\n\r\t':
        name = name.replace(ch, "")
    name = name.strip().strip(".")
    return name if name.lower().endswith(".docx") else name + ".docx"


def today_zh():
    d = datetime.date.today()
    return f"{d.year}年{d.month}月{d.day}日"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--work", default="./_work")
    ap.add_argument("--dir", choices=["es2zh", "zh2es"], required=True)
    ap.add_argument("--mode", choices=["full", "bilingual"], default="full")
    ap.add_argument("--filename", default="")
    ap.add_argument("--date", default="")
    a = ap.parse_args()

    model = json.load(open(os.path.join(a.work, "doc_model.json"), encoding="utf-8"))
    raw = json.load(open(os.path.join(a.work, "translations.json"), encoding="utf-8"))
    tr = {int(k): v for k, v in raw.items()}

    doc = Document(a.src)
    targets, idx = [], 0
    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, doc)
            if p.text.strip():
                targets.append((idx, "p", p))
                idx += 1
        elif child.tag == qn("w:tbl"):
            targets.append((idx, "table", Table(child, doc)))
            idx += 1

    # 全篇最浅编号层级 → 一、
    tiers = [detect_tier(tr.get(i) if isinstance(tr.get(i), str) else r.text)
             for i, k, r in targets if k == "p"]
    tiers = [t for t in tiers if t]
    min_tier = min(tiers) if tiers else 1

    counters, replaced, missing = {}, 0, []

    for i, kind, ref in targets:
        if kind == "table":
            data = tr.get(i)
            if not isinstance(data, dict) or "rows" not in data:
                missing.append(i)
                continue
            rows = data["rows"]
            # 单元格段落的原始加粗信息（用来判断小标题）
            cell_meta = {}
            if i < len(model["blocks"]):
                for c in model["blocks"][i].get("cells", []):
                    cell_meta[(c["r"], c["c"])] = c.get("meta", [])
            for ri, row in enumerate(ref.rows):
                if ri >= len(rows):
                    break
                seen = set()
                ci = 0
                for cell in row.cells:
                    if id(cell._tc) in seen:
                        continue
                    seen.add(id(cell._tc))
                    if ci < len(rows[ri]):
                        val = rows[ri][ci]
                        # 单元格可以是单段字符串，也可以是逐段列表
                        vals = val if isinstance(val, list) else [val]
                        paras = [q for q in cell.paragraphs]
                        metas = cell_meta.get((ri, ci), [])
                        for pi, ptext in enumerate(vals):
                            if pi < len(paras) and ptext:
                                write_paragraph(paras[pi], ptext)
                                if a.dir == "es2zh":
                                    # 全大写 + 加粗 + 不长 → 当作三级小标题
                                    lvl = 0
                                    md = metas[pi] if pi < len(metas) else {}
                                    if md.get("bold") and md.get("upper", 0) >= 0.75 \
                                            and md.get("len", 999) <= 110:
                                        lvl = 2
                                    restyle(paras[pi], lvl)
                    ci += 1
            replaced += 1
            continue

        p = ref
        zh = tr.get(i)
        if not isinstance(zh, str) or not zh.strip():
            missing.append(i)
            continue
        replaced += 1

        if a.mode == "bilingual":
            original = copy.deepcopy(p._p)

        if a.dir == "es2zh":
            tier = detect_tier(p.text)
            if tier:
                lvl = min(4, max(1, tier - min_tier + 1))
                counters[lvl] = counters.get(lvl, 0) + 1
                for k in [k for k in list(counters) if k > lvl]:
                    counters.pop(k)
                n = counters[lvl]
                mark = (f"{cn_number(n)}、" if lvl == 1 else
                        f"{n}. " if lvl == 2 else
                        f"{n}）" if lvl == 3 else CIRCLED[(n - 1) % 20])
                zh = mark + strip_marker(zh)

        write_paragraph(p, zh)
        if a.dir == "es2zh":
            style_lvl = model["blocks"][i].get("level", 0) if i < len(model["blocks"]) else 0
            if i == 0 and not tier:          # 文首第一段＝文档标题
                style_lvl = 1
            if tier and style_lvl >= 1:      # 标题字号跟随它在编号体系里的层级
                style_lvl = min(4, max(1, tier - min_tier + 1))
            restyle(p, style_lvl)
        if a.mode == "bilingual":
            p._p.addnext(original)

    if a.dir == "es2zh":
        dp = doc.add_paragraph()
        dr = dp.add_run(a.date or today_zh())
        set_font(dr, LATIN_FS, FANGSONG, BODY_PT, False)
        dp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        for ch in doc.element.body.iterchildren():
            if ch.tag == qn("w:p"):
                pp = Paragraph(ch, doc)
                if pp.text.strip():
                    if re.match(r"^\s*\d{4}\s*[年/.\-]", pp.text):
                        pp.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    break

    name = a.filename.strip()
    if not name:
        t = open(os.path.join(a.work, "title.txt"), encoding="utf-8").read().strip()
        name = (t or "translated")[:60]
    out = os.path.join(os.path.dirname(os.path.abspath(a.src)), sanitize(name))
    doc.save(out)

    print(f"replaced={replaced} missing={len(missing)} {missing[:10]}")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
