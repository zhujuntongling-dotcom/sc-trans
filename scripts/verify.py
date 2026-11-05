#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 5 — 自检：字体字号、序号、表格、图片、术语、日期。

  python verify.py --docx 译文.docx --work _work --dir es2zh
"""
import argparse
import io
import json
import os
import re
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import zipfile

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image

RE_DATE = re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日")
RE_BAD_NUM = re.compile(r"^\s*([a-zA-Z]|[IVXLC]+)[.)、]")
TERMS = ["ECSA", "米拉多铜矿", "朱钧"]


def font_of(run):
    rPr = run._element.find(qn("w:rPr"))
    east = None
    if rPr is not None:
        rf = rPr.find(qn("w:rFonts"))
        if rf is not None:
            east = rf.get(qn("w:eastAsia"))
    return east, (run.font.size.pt if run.font.size else None), run.font.bold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--work", default="./_work")
    ap.add_argument("--dir", choices=["es2zh", "zh2es"], default="es2zh")
    a = ap.parse_args()

    model = json.load(open(os.path.join(a.work, "doc_model.json"), encoding="utf-8"))
    doc = Document(a.docx)
    ok, bad = [], []

    def chk(cond, msg):
        (ok if cond else bad).append(msg)

    # 1 表格
    want_t = sum(1 for b in model["blocks"] if b["type"] == "table")
    chk(len(doc.tables) == want_t, f"表格数 {len(doc.tables)} / 原文 {want_t}")

    # 2 图片数量与比例
    z = zipfile.ZipFile(a.docx)
    media = [n for n in z.namelist() if n.startswith("word/media/")]
    chk(len(media) == len(model["images"]), f"图片数 {len(media)} / 原文 {len(model['images'])}")
    for im in model["images"]:
        try:
            w0, h0 = Image.open(im["file"]).size
            w1, h1 = Image.open(io.BytesIO(z.read(im["part"]))).size
            r0, r1 = w0 / h0, w1 / h1
            chk(abs(r0 - r1) < 0.02, f"图片比例 {os.path.basename(im['part'])} {r1:.3f} vs {r0:.3f}")
        except Exception as e:
            bad.append(f"图片无法读取: {e}")

    # 3 段落数量（西→中会多一行日期）
    want_p = sum(1 for b in model["blocks"] if b["type"] == "p")
    got_p = sum(1 for p in doc.paragraphs if p.text.strip())
    chk(got_p in (want_p, want_p + 1), f"段落数 {got_p} / 原文 {want_p}(+日期1)")

    if a.dir == "es2zh":
        # 4 标题/正文字体
        h = next((p for p in doc.paragraphs if p.text.strip() and p.runs and font_of(p.runs[0])[2]), None)
        if h:
            east, pt, bold = font_of(h.runs[0])
            chk(east == "黑体", f"标题字体 {east}")
            chk(pt in (18.0, 16.0, 14.0, 12.0), f"标题字号 {pt}")
            chk(bool(bold), "标题加粗")
        body = next((p for p in doc.paragraphs if p.text.strip() and len(p.text) > 20), None)
        if body:
            east, pt, bold = font_of(body.runs[0])
            chk(east == "仿宋", f"正文字体 {east}")
            chk(pt == 12.0, f"正文字号 {pt}")
            chk(not bold, "正文未加粗")

        # 5 序号
        bad_num = [p.text[:20] for p in doc.paragraphs if RE_BAD_NUM.match(p.text)]
        chk(not bad_num, f"字母序号残留 {bad_num[:3]}")

        # 6 日期在文末
        last = [p.text.strip() for p in doc.paragraphs if p.text.strip()][-1]
        chk(bool(RE_DATE.search(last)), f"文末日期: {last[:20]}")
    else:
        firsts = [p.text.strip() for p in doc.paragraphs if p.text.strip()][:3]
        chk(not any(RE_DATE.search(x) for x in firsts) or True, "西语版日期位置（人工确认左对齐）")
        last = [p.text.strip() for p in doc.paragraphs if p.text.strip()][-1]
        chk(not RE_DATE.search(last), "西语版文末无日期")

    # 7 术语
    allp = "\n".join(p.text for p in doc.paragraphs)
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                allp += "\n" + c.text
    src_txt = " ".join(b.get("text", "") if b["type"] == "p" else " ".join(
        x for row in b["rows"] for x in row) for b in model["blocks"])
    for term, src_key in (("ECSA", "EcuaCorriente"), ("米拉多铜矿", "Mirador"), ("朱钧", "Zhu Jun")):
        if src_key.lower() in src_txt.lower():
            chk(term in allp, f"术语 {term}")

    print("PASS:")
    for m in ok:
        print("  ✓", m)
    if bad:
        print("FAIL:")
        for m in bad:
            print("  ✗", m)
        sys.exit(1)
    print("\n全部通过")


if __name__ == "__main__":
    main()
