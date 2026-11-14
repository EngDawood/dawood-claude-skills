#!/usr/bin/env python3
"""Make an Arabic .pptx right-to-left at the XML level.

usage: rtl_fix.py deck.pptx [-o out.pptx] [--check] [--slides-only] [--keep-table-order]

Fix mode rewrites the file (in place unless -o), then re-checks the result.
Exit code 0 = clean, 1 = issues or warnings remain.
"""
import argparse
import re
import shutil
import sys
import tempfile
import zipfile

try:
    from lxml import etree
except ImportError:
    sys.exit("rtl_fix.py needs lxml: pip install lxml")

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
ARABIC = re.compile("[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN = re.compile("[A-Za-z]")
LEAD_PUNCT = re.compile("^\\s*[.\u060C\u061B:!\u061F\u2026]+\\s*[\u0600-\u06FF]")
BIDI_CTRL = re.compile("[\u200E\u200F\u202A-\u202E\u2066-\u2069]")
PRES_FORMS = re.compile("[\uFB50-\uFDFF\uFE70-\uFEFF]")
SLIDE = re.compile(r"ppt/slides/[^/]+\.xml$")
STYLE_PART = re.compile(r"ppt/(slideLayouts|slideMasters)/[^/]+\.xml$|ppt/presentation\.xml$")
TOP_STYLE_PART = re.compile(r"ppt/slideMasters/[^/]+\.xml$|ppt/presentation\.xml$")
LVL = re.compile(r"lvl\dpPr$")


def q(tag):
    return "{%s}%s" % (A, tag)


def text_of(el):
    return "".join(t.text or "" for t in el.iter(q("t")))


def in_placeholder(el):
    """True when the paragraph sits in a layout placeholder, whose alignment is inherited."""
    node = el.getparent()
    while node is not None:
        if isinstance(node.tag, str) and node.tag.endswith("}sp"):
            return any(isinstance(c.tag, str) and c.tag.endswith("}ph") for c in node.iter())
        node = node.getparent()
    return False


class Report:
    def __init__(self):
        self.issues = []
        self.warnings = []

    def issue(self, part, kind, text):
        self.issues.append((part, kind, text.strip()[:50]))

    def warn(self, part, kind, text):
        self.warnings.append((part, kind, text.strip()[:50]))


def fix_paragraph(p, part, rep, fix, deck_arabic):
    text = text_of(p)
    has_ar = bool(ARABIC.search(text))
    if not has_ar and (LATIN.search(text) or not deck_arabic):
        return
    if has_ar:
        if LEAD_PUNCT.search(text):
            rep.warn(part, "punctuation typed before the sentence; retype in reading order", text)
        if BIDI_CTRL.search(text):
            rep.warn(part, "bidi control characters in text; remove them and rely on rtl", text)
        if PRES_FORMS.search(text):
            rep.warn(part, "pre-shaped presentation-form letters; use plain Arabic letters", text)

    ppr = p.find(q("pPr"))
    if ppr is None or ppr.get("rtl") != "1":
        if has_ar:
            rep.issue(part, "paragraph is not rtl", text)
        if fix:
            if ppr is None:
                ppr = etree.Element(q("pPr"))
                p.insert(0, ppr)
            ppr.set("rtl", "1")
    if fix and has_ar and ppr.get("algn") is None and not in_placeholder(p):
        ppr.set("algn", "r")
    if ppr is not None and ppr.get("algn") == "l":
        if has_ar:
            rep.issue(part, "Arabic paragraph is left-aligned", text)
        if fix:
            ppr.set("algn", "r")

    for r in list(p.findall(q("r"))) + list(p.findall(q("fld"))):
        rtext = text_of(r)
        if not ARABIC.search(rtext):
            continue
        rpr = r.find(q("rPr"))
        if rpr is None or not (rpr.get("lang") or "").startswith("ar"):
            rep.issue(part, "Arabic run is not tagged lang=ar", rtext)
            if fix:
                if rpr is None:
                    rpr = etree.Element(q("rPr"))
                    r.insert(0, rpr)
                rpr.set("lang", "ar-SA")
        if rpr is None:
            continue
        latin = rpr.find(q("latin"))
        if latin is None or (latin.get("typeface") or "").startswith("+"):
            continue
        face = latin.get("typeface")
        cs = rpr.find(q("cs"))
        if cs is None or cs.get("typeface") != face:
            rep.issue(part, "complex-script font differs from the run font", rtext)
            if fix:
                if cs is None:
                    cs = etree.Element(q("cs"))
                    ea = rpr.find(q("ea"))
                    (ea if ea is not None else latin).addnext(cs)
                cs.set("typeface", face)


def fix_part(name, root, rep, fix, deck_arabic, opts):
    for p in root.iter(q("p")):
        fix_paragraph(p, name, rep, fix, deck_arabic)

    for body in root.iter(q("bodyPr")):
        parent = body.getparent()
        if fix and parent is not None and ARABIC.search(text_of(parent)):
            body.set("rtlCol", "1")

    for tbl in root.iter(q("tbl")):
        if not ARABIC.search(text_of(tbl)) or opts.keep_table_order:
            continue
        tblpr = tbl.find(q("tblPr"))
        if tblpr is None or tblpr.get("rtl") != "1":
            rep.issue(name, "table is not rtl", text_of(tbl))
            if fix:
                if tblpr is None:
                    tblpr = etree.Element(q("tblPr"))
                    tbl.insert(0, tblpr)
                tblpr.set("rtl", "1")

    if fix and deck_arabic and not opts.slides_only:
        top = bool(TOP_STYLE_PART.search(name))
        for el in root.iter():
            if not isinstance(el.tag, str) or not el.tag.startswith("{%s}" % A):
                continue
            local = el.tag.split("}")[1]
            if not LVL.match(local):
                continue
            el.set("rtl", "1")
            algn = el.get("algn")
            if algn == "l" or (algn is None and top and not SLIDE.search(name)):
                el.set("algn", "r")


def run(path, out, fix, opts):
    rep = Report()
    zin = zipfile.ZipFile(path)
    names = zin.namelist()
    trees = {}
    ar = lat = 0
    for n in names:
        if SLIDE.search(n) or (STYLE_PART.search(n) and not opts.slides_only):
            trees[n] = etree.fromstring(zin.read(n))
        if SLIDE.search(n):
            for p in trees[n].iter(q("p")):
                t = text_of(p)
                if ARABIC.search(t):
                    ar += 1
                elif LATIN.search(t):
                    lat += 1
    deck_arabic = ar > 0 and ar >= lat
    for n, root in trees.items():
        fix_part(n, root, rep, fix, deck_arabic, opts)
    if fix:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename in trees:
                    data = etree.tostring(trees[info.filename], xml_declaration=True,
                                          encoding="UTF-8", standalone=True)
                zout.writestr(info, data)
        zin.close()
        shutil.move(tmp.name, out)
    else:
        zin.close()
    return rep, ar


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx")
    ap.add_argument("-o", "--out")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    ap.add_argument("--slides-only", action="store_true", help="leave masters, layouts and defaults untouched")
    ap.add_argument("--keep-table-order", action="store_true", help="do not set tables right-to-left")
    opts = ap.parse_args()
    target = opts.pptx
    if not opts.check:
        target = opts.out or opts.pptx
        before, ar = run(opts.pptx, target, True, opts)
        print("fixed %d issues across %d Arabic paragraphs -> %s" % (len(before.issues), ar, target))
    rep, ar = run(target, None, False, opts)
    if ar == 0:
        print("note: no Arabic text found")
    for part, kind, text in rep.issues[:40]:
        print("ISSUE %s: %s | %s" % (part.split("/")[-1], kind, text))
    if len(rep.issues) > 40:
        print("... %d more issues" % (len(rep.issues) - 40))
    for part, kind, text in rep.warnings:
        print("WARN  %s: %s | %s" % (part.split("/")[-1], kind, text))
    if rep.issues or rep.warnings:
        print("FAIL: %d issues, %d warnings" % (len(rep.issues), len(rep.warnings)))
        sys.exit(1)
    print("OK: 0 issues, 0 warnings")


if __name__ == "__main__":
    main()
