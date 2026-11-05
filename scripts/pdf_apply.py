#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 回填：抹掉原文、按原位置重排译文（版式、图形、图片位置不变）。

  python pdf_apply.py --src 文档.pdf --work ./_work --lang zh --out 译文.pdf
"""
import argparse
import json
import os
import sys

import pymupdf as fitz

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CJK_FONT = r"C:\Windows\Fonts\simhei.ttf"      # 黑体（正文）
CJK_FONT2 = r"C:\Windows\Fonts\msyh.ttc"       # 备用

COLOR = (0.12, 0.12, 0.12)


def fit_insert(page, rect, text, size, fontname, fontfile=None, min_size=4.0):
    """从原字号往下试，直到塞得进原区块"""
    s = size
    while s >= min_size:
        rc = page.insert_textbox(rect, text, fontsize=s, fontname=fontname,
                                 fontfile=fontfile, color=COLOR, align=0,
                                 lineheight=1.25)
        if rc >= 0:
            return s
        s -= 0.5
    # 兜底：最小字号硬塞
    page.insert_textbox(rect, text, fontsize=min_size, fontname=fontname,
                        fontfile=fontfile, color=COLOR, align=0, lineheight=1.15)
    return min_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--work", default="./_work")
    ap.add_argument("--lang", choices=["zh", "es"], default="zh")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    model = json.load(open(os.path.join(a.work, "pdf_model.json"), encoding="utf-8"))
    tr = json.load(open(os.path.join(a.work, "translations.json"), encoding="utf-8"))

    doc = fitz.open(a.src)
    by_page = {}
    for b in model["blocks"]:
        by_page.setdefault(b["page"], []).append(b)

    done = miss = 0
    for pno, blocks in by_page.items():
        page = doc[pno]
        for b in blocks:
            page.add_redact_annot(fitz.Rect(b["bbox"]))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        for b in blocks:
            txt = tr.get(b["id"])
            if not isinstance(txt, str) or not txt.strip():
                miss += 1
                continue
            r = fitz.Rect(b["bbox"])
            r.y1 = max(r.y1, r.y0 + b["size"] * 1.6)   # 给标题留一行高
            if a.lang == "zh":
                fit_insert(page, r, txt, b["size"], "F0",
                           CJK_FONT if os.path.exists(CJK_FONT) else CJK_FONT2)
            else:
                fit_insert(page, r, txt, b["size"], "helv")
            done += 1

    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.src)),
                                os.path.splitext(os.path.basename(a.src))[0] + "_translated.pdf")
    doc.save(out, garbage=3, deflate=True)
    print(f"blocks translated={done} missing={miss} -> {out}")


if __name__ == "__main__":
    main()
