#!/usr/bin/env python3
"""Tests for the header, footer and slide rules in format_check.py.

Needs: python-docx>=1.2, python-pptx, lxml.
Run: python3 tests/test_deck_rules.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "plugins" / "freelance-tools" / "skills" / "deliverable-check" / "scripts"))
import format_check as fc  # noqa: E402

failures = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


def has(rep, part):
    return any(part in f["rule"] for f in rep["findings"])


def page_field(paragraph):
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    paragraph._p.append(parse_xml(
        f'<w:r {nsdecls("w")}><w:fldChar w:fldCharType="begin"/></w:r>'))
    paragraph._p.append(parse_xml(f'<w:r {nsdecls("w")}><w:instrText> PAGE </w:instrText></w:r>'))
    paragraph._p.append(parse_xml(f'<w:r {nsdecls("w")}><w:fldChar w:fldCharType="separate"/></w:r>'))
    paragraph._p.append(parse_xml(f'<w:r {nsdecls("w")}><w:t>1</w:t></w:r>'))
    paragraph._p.append(parse_xml(f'<w:r {nsdecls("w")}><w:fldChar w:fldCharType="end"/></w:r>'))


def main():
    import docx
    from pptx import Presentation
    from pptx.util import Inches

    tmp = Path(tempfile.mkdtemp())

    # ---- docx header and footer
    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_paragraph("Body text of the report about sleep and memory in students.")
    d.sections[0].header.paragraphs[0].text = "Sleep and Memory Report"
    p1 = tmp / "title_header.docx"
    d.save(p1)
    check(has(fc.scan_file(p1), "header or footer text"), "docx: title in the header flagged")

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_paragraph("Body text of the report about sleep and memory in students.")
    foot = d.sections[0].footer.paragraphs[0]
    page_field(foot)
    p2 = tmp / "page_only.docx"
    d.save(p2)
    check(not has(fc.scan_file(p2), "header or footer text"), "docx: page number only is fine")

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_paragraph("Body text of the report about sleep and memory in students.")
    d.sections[0].footer.paragraphs[0].text = "Page 3 of 10"
    p3 = tmp / "page_words.docx"
    d.save(p3)
    check(not has(fc.scan_file(p3), "header or footer text"), "docx: 'Page 3 of 10' is fine")
    check(not has(fc.scan_file(p1, skip=("header-title",)), "header or footer text"), "docx: header-title can be skipped")

    # ---- pptx
    prs = Presentation()
    for i in range(4):
        s = prs.slides.add_slide(prs.slide_layouts[5])
        s.shapes.title.text = f"Slide {i + 1}"
        tb = s.shapes.add_textbox(Inches(1), Inches(6.8), Inches(6), Inches(0.4))
        tb.text_frame.text = "Sleep and Memory Deck"
    s = prs.slides[1]
    src = s.shapes.add_textbox(Inches(1), Inches(6), Inches(6), Inches(0.4))
    src.text_frame.text = "Source: Smith, J. (2020)"
    img = s.shapes.add_textbox(Inches(1), Inches(5), Inches(6), Inches(0.4))
    img.text_frame.text = "Image credit: Unsplash"
    p4 = tmp / "deck.pptx"
    prs.save(p4)
    rep = fc.scan_file(p4)
    check(has(rep, "same text repeated"), "pptx: deck title repeated on every slide flagged")
    check(has(rep, "source line"), "pptx: source line and image credit flagged")
    src_f = next(f for f in rep["findings"] if "source line" in f["rule"])
    check(src_f["count"] == 2, f"pptx: both source lines counted ({src_f['count']})")
    rep2 = fc.scan_file(p4, skip=("slide-repeat", "slide-sources"))
    check(not rep2["findings"], "pptx: both checks can be skipped")

    prs = Presentation()
    for i in range(4):
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = f"Point {i + 1}"
        s.placeholders[1].text = f"Plain content {i + 1}"
    p5 = tmp / "clean_deck.pptx"
    prs.save(p5)
    check(not fc.scan_file(p5)["findings"], "pptx: clean deck gives no finding")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
