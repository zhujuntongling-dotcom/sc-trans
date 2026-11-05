#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 图片：列出内嵌图，用重绘后的同名文件替换（保持位置与尺寸）。

  python pdf_images.py list    --work ./_work
  python pdf_images.py replace --pdf 译文.pdf --work ./_work
"""
import argparse
import json
import os
import sys

import pymupdf as fitz
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "replace"])
    ap.add_argument("--pdf", default="")
    ap.add_argument("--work", default="./_work")
    a = ap.parse_args()

    model = json.load(open(os.path.join(a.work, "pdf_model.json"), encoding="utf-8"))

    if a.cmd == "list":
        for im in model["images"]:
            try:
                w, h = Image.open(im["file"]).size
            except Exception:
                w, h = "?", "?"
            print(f"p{im['page']} xref={im['xref']} {w}x{h} -> {os.path.basename(im['file'])}")
        return

    if not a.pdf:
        sys.exit("--pdf required")
    doc = fitz.open(a.pdf)
    n = 0
    # 按页分组，用"当前 PDF 里的图片顺序"与模型顺序一一对应
    # （apply 保存时 garbage 收集会重排 xref，不能沿用旧编号）
    by_page = {}
    for im in model["images"]:
        by_page.setdefault(im["page"], []).append(im)

    for pno, items in by_page.items():
        page = doc[pno]
        cur = page.get_images(full=True)
        for idx, im in enumerate(items):
            if idx >= len(cur):
                break
            xref = cur[idx][0]
            f = im["file"]
            if not os.path.isfile(f):
                continue
            ok = False
            try:
                page.replace_image(xref, filename=f)
                ok = True
            except Exception:
                pass
            if not ok or im.get("bbox"):
                # 兜底：删掉原图，按原位置原尺寸重贴（更可靠，但会盖在同位置上层）
                rect = fitz.Rect(im["bbox"]) if im.get("bbox") else None
                if rect:
                    try:
                        page.delete_image(xref)
                    except Exception:
                        pass
                    page.insert_image(rect, filename=f, keep_proportion=False)
                    ok = True
            if ok:
                n += 1
                print(f"replaced p{pno} #{idx} xref={xref} <- {os.path.basename(f)}")
            else:
                print(f"skip p{pno} #{idx}: no method worked")
    tmp = a.pdf + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, a.pdf)
    print(f"images replaced: {n}")


if __name__ == "__main__":
    main()
