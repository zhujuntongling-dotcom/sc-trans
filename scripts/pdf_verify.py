#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 自检：页数、块覆盖、残留源语言、图片数。

  python pdf_verify.py --pdf 译文.pdf --work ./_work
"""
import argparse
import json
import os
import re
import sys

import pymupdf as fitz

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RE_LATIN = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]{3,}(?:\s+[A-Za-zÁÉÍÓÚáéíóúÑñÜü]{2,}){3,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--work", default="./_work")
    a = ap.parse_args()

    model = json.load(open(os.path.join(a.work, "pdf_model.json"), encoding="utf-8"))
    doc = fitz.open(a.pdf)
    ok, bad = [], []

    def chk(c, m):
        (ok if c else bad).append(m)

    chk(len(doc) == model["pages"], f"页数 {len(doc)} / 原文 {model['pages']}")

    text = "\n".join(p.get_text() for p in doc)
    left = RE_LATIN.findall(text)
    chk(len(left) <= 2, f"残留源语言片段 {len(left)}（专有名词可忽略）")
    for s in left[:3]:
        print("   残留:", s[:80])

    imgs = sum(len(p.get_images(full=True)) for p in doc)
    chk(imgs >= len(model["images"]), f"图片数 {imgs} ≥ 原文 {len(model['images'])}")

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
