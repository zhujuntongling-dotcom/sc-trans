#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1 — 拆解 docx：结构模型 + 图片 + 预览文本。

输出到 --work：
  doc_model.json   段落/表格结构、字体字号、层级
  preview.txt      按顺序的可读预览（翻译时对照用）
  title.txt        文内首个标题（用于自动命名）
  images/*         抽出的图片（按原格式）
"""
import argparse
import json
import os
import re
import zipfile

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HEADING_RE = re.compile(r"(?i)heading\s*(\d)|标题\s*(\d)")


def para_meta(p):
    sizes = [r.font.size.pt for r in p.runs if r.font.size]
    bolds = [bool(r.font.bold) for r in p.runs if r.font.bold is not None]
    name = p.style.name or ""
    m = HEADING_RE.search(name)
    level = int(m.group(1) or m.group(2)) if m else 0
    if not level:
        # 没有用标题样式时，用"加粗 + 字号明显偏大"兜底判为标题
        if bolds and all(bolds) and sizes and max(sizes) >= 14:
            level = 1 if max(sizes) >= 18 else 2
    return {
        "style": name,
        "level": level,
        "bold": all(bolds) if bolds else False,
        "size": round(max(sizes), 1) if sizes else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--work", default="./_work")
    a = ap.parse_args()

    os.makedirs(a.work, exist_ok=True)
    img_dir = os.path.join(a.work, "images")
    os.makedirs(img_dir, exist_ok=True)

    doc = Document(a.src)
    blocks, preview, idx = [], [], 0

    for child in doc.element.body.iterchildren():
        if child.tag == qn("w:p"):
            p = Paragraph(child, doc)
            txt = p.text.strip()
            if not txt:
                continue
            meta = para_meta(p)
            blocks.append({"i": idx, "type": "p", "text": txt, **meta})
            preview.append(f"[{idx}] <{'H%d' % meta['level'] if meta['level'] else 'body'}> {txt}")
            idx += 1
        elif child.tag == qn("w:tbl"):
            tb = Table(child, doc)
            rows, cells = [], []
            for ri, row in enumerate(tb.rows):
                line, seen, ci = [], set(), 0
                for cell in row.cells:
                    if id(cell._tc) in seen:
                        continue
                    seen.add(id(cell._tc))
                    paras, metas = [], []
                    for q in cell.paragraphs:
                        txt = q.text.strip()
                        paras.append(txt)
                        bolds = [r.font.bold for r in q.runs if r.font.bold is not None]
                        letters = [c for c in txt if c.isalpha()]
                        up = (sum(1 for c in letters if c.isupper()) / len(letters)) if letters else 0
                        metas.append({"bold": bool(bolds) and all(bolds),
                                      "len": len(txt), "upper": round(up, 2)})
                    cells.append({"r": ri, "c": ci, "paras": paras, "meta": metas})
                    line.append("\n".join(paras))
                    ci += 1
                rows.append(line)
            blocks.append({"i": idx, "type": "table", "rows": rows, "cells": cells})
            preview.append(f"[{idx}] <table {len(rows)}x{len(rows[0]) if rows else 0}>  "
                           f"cells={len(cells)}")
            for cell in cells:
                for pi, t in enumerate(cell["paras"]):
                    if t:
                        preview.append(f"      [{idx}.r{cell['r']}c{cell['c']}p{pi}] {t}")
            idx += 1

    # 图片
    z = zipfile.ZipFile(a.src)
    images = []
    for n in z.namelist():
        if n.startswith("word/media/"):
            data = z.read(n)
            ext = os.path.splitext(n)[1].lower()
            out = os.path.join(img_dir, os.path.basename(n))
            with open(out, "wb") as f:
                f.write(data)
            images.append({"part": n, "file": out, "bytes": len(data), "ext": ext})

    # 文本框（python-docx 读不到，只报数）
    xml = z.read("word/document.xml").decode("utf-8", "ignore")
    tb_count = xml.count("txbxContent")

    title = ""
    for b in blocks:
        if b["type"] == "p" and (b["level"] == 1 or not title):
            title = b["text"]
            if b["level"] == 1:
                break

    model = {
        "src": os.path.abspath(a.src),
        "blocks": blocks,
        "images": images,
        "textboxes": tb_count,
    }
    with open(os.path.join(a.work, "doc_model.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.work, "preview.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(preview))
    with open(os.path.join(a.work, "title.txt"), "w", encoding="utf-8") as f:
        f.write(title)

    print(f"blocks={len(blocks)} images={len(images)} textboxes={tb_count}")
    print(f"title: {title[:80]}")
    print(f"-> {a.work}")


if __name__ == "__main__":
    main()
