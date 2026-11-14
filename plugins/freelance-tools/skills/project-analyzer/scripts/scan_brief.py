#!/usr/bin/env python3
"""scan_brief: find hidden text and planted AI instructions in an assignment brief.

    scan_brief.py FILE... [--json]

Supports docx, pptx, pdf, html, md and txt. Reports:
  hidden     text a reader cannot see (white or near-white, tiny font, Word hidden,
             off-slide shapes, alt text, comments)
  injection  wording aimed at an AI ("if you are an AI", "ignore previous
             instructions", "include the word ...", Arabic forms too)
  trap_words words or phrases an injection asks to be planted in the answer

Exit code 1 when anything is found. Needs lxml; pdf needs pdfplumber (falls back to pypdf).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

INJECTION = re.compile(
    r"(?i)\bif you (?:are|'re) (?:an? )?(?:ai|a\.i\.|language model|llm|chat ?gpt|claude|gemini|chatbot|assistant|bot)\b"
    r"|\b(?:ai|a\.i\.|language models?|llms?|chat ?gpt|claude|gemini|chatbots?|ai (?:tools?|models?|assistants?))\b[^.\n]{0,40}\b(?:must|should|need to|are required to|have to)\b"
    r"|\bignore (?:all |any )?(?:the )?(?:previous|prior|above|earlier|preceding) (?:instructions?|prompts?|text)\b"
    r"|\b(?:include|insert|use|mention|add|write) (?:the )?(?:word|phrase|term|sentence)s?\b"
    r"|\bdo not (?:tell|inform|reveal|mention (?:this|it) to) (?:the )?(?:user|student|human|reader)\b"
    r"|\b(?:secretly|without (?:telling|mentioning))\b|\bhidden instruction\b|\bsystem prompt\b"
    r"|إذا كنت\s+(?:نموذج(?:اً|ا)?\s+لغوي|ذكاء(?:ً|ا)?\s+اصطناعي(?:اً|ا)?|برنامج|روبوت|شات|chat ?gpt|claude)"
    r"|(?:الذكاء الاصطناعي|النموذج|نماذج اللغة|شات جي بي تي)[^.\n]{0,40}(?:يجب|عليه|عليك|ينبغي)"
    r"|تجاهل\s+(?:كل|جميع)?\s*(?:التعليمات|الأوامر)\s*(?:السابقة)?"
    r"|(?:اذكر|أذكر|أضف|ضع|استخدم|اكتب)\s+(?:كلمة|عبارة|جملة)"
    r"|لا\s+تخبر\s+(?:الطالب|المستخدم)")
# Quoted word after an injection verb: include the word "banana" / اذكر كلمة "موز"
TRAP = re.compile(
    r"(?i)(?:word|phrase|term|sentence|كلمة|عبارة|جملة)s?\s*[:：]?\s*[\"'“”«»‘’]([^\"'“”«»‘’\n]{1,40})[\"'“”«»‘’]")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"


def near_white(hexval: str | None) -> bool:
    if not hexval or not re.fullmatch(r"[0-9A-Fa-f]{6}", hexval):
        return False
    return all(int(hexval[i:i + 2], 16) >= 0xF0 for i in (0, 2, 4))


def add(out, kind, where, reason, text):
    text = re.sub(r"\s+", " ", text).strip()
    if text:
        out.append({"kind": kind, "where": where, "reason": reason, "text": text[:200]})


def scan_docx(z, out):
    from lxml import etree
    full = []
    for name in sorted(n for n in z.namelist() if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$", n)):
        root = etree.fromstring(z.read(name))
        part = name.split("/")[-1][:-4]
        if part == "comments":
            for c in root.iter(f"{W}comment"):
                add(out, "hidden", part, "comment", "".join(t.text or "" for t in c.iter(f"{W}t")))
        for i, p in enumerate(root.iter(f"{W}p"), 1):
            ptext = []
            for r in p.iter(f"{W}r"):
                t = "".join(x.text or "" for x in r.iter(f"{W}t"))
                ptext.append(t)
                rpr = r.find(f"{W}rPr")
                if rpr is None or not t.strip():
                    continue
                reasons = []
                v = rpr.find(f"{W}vanish")
                if v is not None and v.get(f"{W}val") not in ("0", "false", "off"):
                    reasons.append("Word hidden text")
                c = rpr.find(f"{W}color")
                if c is not None and near_white(c.get(f"{W}val")):
                    reasons.append("white text")
                sz = rpr.find(f"{W}sz")
                if sz is not None and (sz.get(f"{W}val") or "99").isdigit() and int(sz.get(f"{W}val")) <= 4:
                    reasons.append("font 2pt or smaller")
                if reasons:
                    add(out, "hidden", f"{part} p{i}", ", ".join(reasons), t)
            full.append((f"{part} p{i}", "".join(ptext)))
        for d in root.iter(f"{WP}docPr"):
            add(out, "hidden", part, "image alt text", (d.get("descr") or "") + " " + (d.get("title") or ""))
    return full


def scan_pptx(z, out):
    from lxml import etree
    pres = etree.fromstring(z.read("ppt/presentation.xml"))
    sz = pres.find(f"{P}sldSz")
    cx, cy = (int(sz.get("cx")), int(sz.get("cy"))) if sz is not None else (12192000, 6858000)
    full = []
    names = sorted((n for n in z.namelist() if re.match(r"ppt/(slides/slide|notesSlides/notesSlide)\d+\.xml$", n)),
                   key=lambda n: (n.startswith("ppt/notes"), int(re.search(r"(\d+)\.xml$", n).group(1))))
    for name in names:
        root = etree.fromstring(z.read(name))
        where = ("notes " if "notes" in name else "slide ") + re.search(r"(\d+)\.xml$", name).group(1)
        for sp in root.iter(f"{P}sp", f"{P}pic"):
            text = " ".join("".join(t.text or "" for t in p.iter(f"{A}t")) for p in sp.iter(f"{A}p"))
            nv = sp.find(f".//{P}cNvPr")
            if nv is not None and nv.get("descr"):
                add(out, "hidden", where, "alt text", nv.get("descr"))
            off = sp.find(f".//{A}off")
            if off is not None and text.strip():
                x, y = int(off.get("x", 0)), int(off.get("y", 0))
                if x < 0 or y < 0 or x >= cx or y >= cy:
                    add(out, "hidden", where, "shape outside the slide", text)
            for r in sp.iter(f"{A}r"):
                t = "".join(x.text or "" for x in r.iter(f"{A}t"))
                rpr = r.find(f"{A}rPr")
                if rpr is None or not t.strip():
                    continue
                reasons = []
                if (rpr.get("sz") or "9999").isdigit() and int(rpr.get("sz")) <= 400:
                    reasons.append("font 4pt or smaller")
                clr = rpr.find(f"{A}solidFill/{A}srgbClr")
                if clr is not None and near_white(clr.get("val")):
                    reasons.append("white text (check the background)")
                if reasons:
                    add(out, "hidden", where, ", ".join(reasons), t)
            if text.strip():
                full.append((where, text))
    return full


def scan_pdf(path, out):
    full = []
    try:
        import pdfplumber
    except ImportError:
        from pypdf import PdfReader
        for i, page in enumerate(PdfReader(str(path)).pages, 1):
            full.append((f"page {i}", page.extract_text() or ""))
        add(out, "hidden", "all", "pdfplumber missing, colour and size not checked", "pip install pdfplumber")
        return full
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            full.append((f"page {i}", page.extract_text() or ""))
            buf, why = [], ""
            for ch in page.chars + [None]:
                reason = ""
                if ch is not None:
                    col = ch.get("non_stroking_color")
                    vals = list(col) if isinstance(col, (list, tuple)) else ([col] if isinstance(col, (int, float)) else [])
                    white = (len(vals) in (1, 3) and vals and all(v >= 0.94 for v in vals)) or (len(vals) == 4 and all(v <= 0.06 for v in vals))
                    off = ch["x1"] < 0 or ch["top"] < 0 or ch["x0"] > page.width or ch["bottom"] > page.height
                    reason = "white text" if white else "font under 3pt" if ch["size"] < 3 else "outside the page" if off else ""
                if reason and reason == why:
                    buf.append(ch["text"])
                    continue
                if why and "".join(buf).strip():
                    add(out, "hidden", f"page {i}", why, "".join(buf))
                buf, why = ([ch["text"]] if reason else []), reason
    return full


def scan_markup(path, out):
    raw = path.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r"(?is)<[^>]+style=\"[^\"]*(?:display:\s*none|visibility:\s*hidden|font-size:\s*0|color:\s*#?f{3,6}\b|color:\s*white)[^\"]*\"[^>]*>(.*?)</", raw):
        add(out, "hidden", "html", "styled invisible", re.sub(r"<[^>]+>", " ", m.group(1)))
    for m in re.finditer(r"(?s)<!--(.*?)-->", raw):
        add(out, "hidden", "html", "comment", m.group(1))
    return [("text", re.sub(r"<[^>]+>", " ", raw))]


def scan_file(path: Path) -> dict:
    out: list = []
    ext = path.suffix.lower()
    if ext in (".docx", ".pptx"):
        with zipfile.ZipFile(path) as z:
            full = scan_docx(z, out) if ext == ".docx" else scan_pptx(z, out)
    elif ext == ".pdf":
        full = scan_pdf(path, out)
    elif ext in (".html", ".htm", ".md", ".txt"):
        full = scan_markup(path, out)
    else:
        raise SystemExit(f"unsupported file type: {ext}")
    texts = [(w, t) for w, t in full] + [(f["where"], f["text"]) for f in out if f["kind"] == "hidden"]
    traps: set = set()
    seen: set = set()
    for where, text in texts:
        for line in re.split(r"(?<=[.!?؟])\s+|\n", text):
            m = INJECTION.search(line)
            if not m:
                continue
            key = (where, re.sub(r"\W+", "", line.lower())[:60])
            if key not in seen:
                seen.add(key)
                add(out, "injection", where, "wording aimed at an AI", line)
            for t in TRAP.finditer(line):
                traps.add(t.group(1).strip())
    return {"file": str(path), "findings": out, "trap_words": sorted(traps)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    reps = [scan_file(f) for f in a.files]
    if a.json:
        print(json.dumps(reps, ensure_ascii=False, indent=2))
    else:
        for r in reps:
            print(f"{Path(r['file']).name}: {len(r['findings'])} finding(s)")
            for f in r["findings"]:
                print(f"  [{f['kind']}] {f['where']} ({f['reason']}): {f['text']}")
            if r["trap_words"]:
                print(f"  trap words: {', '.join(r['trap_words'])}")
            if not r["findings"]:
                print("  nothing hidden, no AI-directed wording")
    return 1 if any(r["findings"] for r in reps) else 0


if __name__ == "__main__":
    sys.exit(main())
