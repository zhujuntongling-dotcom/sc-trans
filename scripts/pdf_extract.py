#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 拆解：按文本块提取（位置/字号/文字），并抽出内嵌图片。

  python pdf_extract.py --src 文档.pdf --work ./_work
输出：pdf_model.json / preview.txt / title.txt / images/
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--work", default="./_work")
    a = ap.parse_args()

    os.makedirs(a.work, exist_ok=True)
    img_dir = os.path.join(a.work, "images")
    os.makedirs(img_dir, exist_ok=True)

    doc = fitz.open(a.src)
    blocks, preview, images = [], [], []

    for pno, page in enumerate(doc):
        d = page.get_text("dict")
        bi = 0
        for blk in d.get("blocks", []):
            if blk.get("type") != 0:
                continue
            lines = [ln for ln in blk.get("lines", []) if ln.get("spans")]
            if not lines:
                continue
            text_lines, sizes = [], []
            for ln in lines:
                seg = "".join(sp.get("text", "") for sp in ln["spans"]).strip()
                if seg:
                    text_lines.append(seg)
                sizes += [sp.get("size", 10) for sp in ln["spans"]]
            text = "\n".join(text_lines).strip()
            if not text:
                continue
            bid = f"p{pno}b{bi}"
            blocks.append({
                "id": bid,
                "page": pno,
                "bbox": [round(v, 1) for v in blk["bbox"]],
                "text": text,
                "size": round(sorted(sizes)[len(sizes) // 2], 1) if sizes else 10.0,
            })
            preview.append(f"[{bid}] ({blocks[-1]['size']}pt) {text.replace(chr(10), ' ⏎ ')}")
            bi += 1

        for img in page.get_images(full=True):
            xref = img[0]
            try:
                info = doc.extract_image(xref)
            except Exception:
                continue
            ext = info.get("ext", "png")
            fn = f"p{pno}_x{xref}.{ext}"
            with open(os.path.join(img_dir, fn), "wb") as f:
                f.write(info["image"])
            rects = page.get_image_rects(xref)
            images.append({
                "page": pno, "xref": xref, "file": os.path.join(img_dir, fn),
                "w": info.get("width"), "h": info.get("height"),
                "bbox": [round(v, 1) for v in rects[0]] if rects else None,
            })

    # 标题：取首页字号最大的块
    title = ""
    if blocks:
        first_page = [b for b in blocks if b["page"] == 0] or blocks
        title = max(first_page, key=lambda b: b["size"])["text"].split("\n")[0]

    model = {"src": os.path.abspath(a.src), "pages": len(doc), "blocks": blocks,
             "images": images, "kind": "pdf"}
    json.dump(model, open(os.path.join(a.work, "pdf_model.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(os.path.join(a.work, "preview.txt"), "w", encoding="utf-8").write("\n".join(preview))
    open(os.path.join(a.work, "title.txt"), "w", encoding="utf-8").write(title)

    print(f"pages={len(doc)} blocks={len(blocks)} images={len(images)}")
    print(f"title: {title[:80]}")
    print(f"-> {a.work}")


if __name__ == "__main__":
    main()
