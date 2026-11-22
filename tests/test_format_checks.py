#!/usr/bin/env python3
"""Tests for format_check.py: Calibri in English docx, boxed code text, comments in code files.

Needs: python-docx>=1.2, lxml.
Run: python3 tests/test_format_checks.py
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


def has(rep, rule_part):
    return any(rule_part in f["rule"] for f in rep["findings"])


def shade(paragraph, fill="D9D9D9"):
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    paragraph._p.get_or_add_pPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:fill="{fill}"/>'))


def border(paragraph):
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    paragraph._p.get_or_add_pPr().append(parse_xml(
        f'<w:pBdr {nsdecls("w")}><w:top w:val="single" w:sz="4" w:color="000000"/></w:pBdr>'))


def mono(paragraph, text):
    run = paragraph.add_run(text)
    run.font.name = "Courier New"
    return run


def main():
    import docx

    tmp = Path(tempfile.mkdtemp())
    text = "The experiment measured sleep length in students and compared the results across three groups."

    # ---- fonts
    d = docx.Document()
    d.styles["Normal"].font.name = "Calibri"
    d.add_paragraph(text)
    p1 = tmp / "calibri.docx"
    d.save(p1)
    check(has(fc.scan_file(p1), "Calibri"), "font: Calibri body flagged in an English docx")

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_heading("Results of the sleep experiment", level=1)  # heading style uses the theme font (Calibri)
    d.add_paragraph(text)
    ph = tmp / "heading.docx"
    d.save(ph)
    check(has(fc.scan_file(ph), "Calibri"), "font: Calibri from the theme in a heading flagged")

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_paragraph(text)
    p2 = tmp / "arial.docx"
    d.save(p2)
    check(not has(fc.scan_file(p2), "Calibri"), "font: Arial body not flagged")

    d = docx.Document()
    d.styles["Normal"].font.name = "Times New Roman"
    para = d.add_paragraph()
    para.add_run(text).font.name = "Calibri"
    p3 = tmp / "direct.docx"
    d.save(p3)
    check(has(fc.scan_file(p3), "Calibri"), "font: direct Calibri run flagged over an Arial style")

    d = docx.Document()
    d.add_paragraph("هذا نص عربي طويل بما يكفي لاختبار أن الخط الافتراضي لا يُعتبر خطأ في المستند العربي كله")
    p4 = tmp / "arabic.docx"
    d.save(p4)
    check(not has(fc.scan_file(p4), "Calibri"), "font: Arabic document not flagged")

    # ---- boxed code text
    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    d.add_paragraph(text)
    mono(d.add_paragraph(), "pip install python-docx")
    p5 = tmp / "plain_code.docx"
    d.save(p5)
    check(not has(fc.scan_file(p5), "background box"), "box: plain monospace code paragraph not flagged")

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    a = d.add_paragraph()
    mono(a, "print('hello')")
    shade(a)
    b = d.add_paragraph()
    mono(b, "npm run build")
    border(b)
    t = d.add_table(rows=1, cols=1)
    mono(t.cell(0, 0).paragraphs[0], "$ git status")
    r = d.add_paragraph()
    run = mono(r, "output: ok")
    run.font.highlight_color = 7
    p6 = tmp / "boxed.docx"
    d.save(p6)
    rep = fc.scan_file(p6)
    boxed = [f for f in rep["findings"] if "background box" in f["rule"]]
    check(bool(boxed) and boxed[0]["count"] == 4, f"box: shading, border, single-cell table and highlight found ({boxed[0]['count'] if boxed else 0})")

    d = docx.Document()
    d.styles["Normal"].font.name = "Arial"
    n = d.add_paragraph("Note: this callout is shaded but holds ordinary prose, not code.")
    shade(n, "FFF2CC")
    p7 = tmp / "callout.docx"
    d.save(p7)
    check(not has(fc.scan_file(p7), "background box"), "box: shaded prose paragraph not flagged")

    # ---- comments in code files
    py = tmp / "a.py"
    py.write_text(
        '#!/usr/bin/env python3\n"""Module doc."""\nimport os  # noqa: F401\n\n# set the value\nx = "a # not a comment"\n\n'
        'def f():\n    """Return one."""\n    return 1  # one\n', encoding="utf-8")
    rep = fc.scan_file(py)
    f = next((f for f in rep["findings"] if "comments in code" in f["rule"]), None)
    check(f is not None and f["count"] == 4, f"code: python comments counted, shebang and noqa skipped ({f['count'] if f else 0})")

    clean = tmp / "b.py"
    clean.write_text('x = "a # b"\nurl = "https://example.org"\nprint(x, url)\n', encoding="utf-8")
    check(not fc.scan_file(clean)["findings"], "code: python file without comments gives no finding")

    js = tmp / "c.js"
    js.write_text('// header\nconst u = "http://a.b"; /* inline */\n/*\n * block\n */\nconst t = `x // y`;\n', encoding="utf-8")
    rep = fc.scan_file(js)
    f = next((f for f in rep["findings"] if "comments in code" in f["rule"]), None)
    check(f is not None and f["count"] == 3, f"code: js line and block comments counted, URL and template kept ({f['count'] if f else 0})")

    banner = tmp / "d.py"
    banner.write_text("# ==== helpers ====\nvalue = 1\n", encoding="utf-8")
    f = next((f for f in fc.scan_file(banner)["findings"] if "comments in code" in f["rule"]), None)
    check(f is not None and "banner" in f["note"], "code: banner comment noted")

    trap = tmp / "e.py"
    trap.write_text("name = 'pineapple'\n", encoding="utf-8")
    check(any(f["category"] == "trap" for f in fc.scan_file(trap, ["pineapple"])["findings"]), "code: trap word found")

    check(fc.scan_file(tmp / "x.pdf") is None, "other file types are skipped")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
