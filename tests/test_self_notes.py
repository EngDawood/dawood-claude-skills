#!/usr/bin/env python3
"""Tests for the self-notes check in format_check.py.

Needs: python-docx>=1.2, python-pptx, lxml.
Run: python3 tests/test_self_notes.py
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


def has(rep):
    return any("own understanding" in f["rule"] for f in rep["findings"])


def main():
    import docx
    from pptx import Presentation

    tmp = Path(tempfile.mkdtemp())

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_paragraph("Sleep improves memory consolidation in students according to the study.")
    d.add_paragraph("Assumption: the sample is representative, to be checked later.")
    d.add_paragraph("Note to self: verify the second table before delivery.")
    d.add_paragraph("ملاحظة لنفسي: أراجع الجدول الثاني قبل التسليم")
    a = tmp / "notes.docx"
    d.save(a)
    rep = fc.scan_file(a)
    f = next((f for f in rep["findings"] if "own understanding" in f["rule"]), None)
    check(f is not None and f["count"] == 3, f"docx: three self-notes found ({f['count'] if f else 0})")
    check(not has(fc.scan_file(a, skip=("self-notes",))), "docx: self-notes can be skipped")

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_paragraph("Sleep improves memory consolidation in students according to the study.")
    d.add_paragraph("Note: the study used a sample of 120 students from two universities.")
    d.add_paragraph("The results are shown in Table 1 and discussed in the next section.")
    b = tmp / "plain.docx"
    d.save(b)
    check(not has(fc.scan_file(b)), "docx: ordinary note and prose not flagged")

    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Findings"
    s.placeholders[1].text = "I assumed the data is complete"
    c = tmp / "deck.pptx"
    prs.save(c)
    check(has(fc.scan_file(c)), "pptx: self-note on a slide found")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
