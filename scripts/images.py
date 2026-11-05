#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 4 — 把重绘后的图片写回 docx（只换 word/media/*，不动 document.xml）。

  python images.py list   --work _work
  python images.py replace --docx 译文.docx --work _work
"""
import argparse
import os
import shutil
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import zipfile

from PIL import Image

MEDIA_PREFIX = "word/media/"


def list_images(work):
    m = os.path.join(work, "doc_model.json")
    import json
    model = json.load(open(m, encoding="utf-8"))
    for im in model["images"]:
        f = im["file"]
        try:
            w, h = Image.open(f).size
            print(f"{os.path.basename(f):24s} {w}x{h}  {im['part']}")
        except Exception as e:
            print(f"{os.path.basename(f):24s} (unreadable: {e})")


def replace(docx, work):
    img_dir = os.path.join(work, "images")
    files = {n: os.path.join(img_dir, n) for n in os.listdir(img_dir)}
    tmp = docx + ".tmp"
    changed = 0
    with zipfile.ZipFile(docx, "r") as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename.startswith(MEDIA_PREFIX):
                base = os.path.basename(item.filename)
                if base in files and os.path.isfile(files[base]):
                    new = open(files[base], "rb").read()
                    if new != data:
                        data = new
                        changed += 1
                        print(f"replaced {base} ({len(new)} bytes)")
            dst.writestr(item, data)
    shutil.move(tmp, docx)
    print(f"images replaced: {changed}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "replace"])
    ap.add_argument("--docx", default="")
    ap.add_argument("--work", default="./_work")
    a = ap.parse_args()
    if a.cmd == "list":
        list_images(a.work)
    else:
        if not a.docx:
            sys.exit("--docx required")
        replace(a.docx, a.work)


if __name__ == "__main__":
    main()
