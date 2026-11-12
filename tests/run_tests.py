#!/usr/bin/env python3
"""Build dirty sample files, then check that scan finds the problems and clean removes them.

Needs: python-docx>=1.2, python-pptx, openpyxl, pypdf, lxml, and LibreOffice (soffice) for the PDF case.
Run: python3 tests/run_tests.py
"""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "deliverable-check" / "scripts"))
import deliverable_check as dc  # noqa: E402

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
failures = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


def cats(rep):
    return {(f["category"], f["rule"]): f for f in rep["findings"]}


def has(rep, category, rule_part=""):
    return any(f["category"] == category and rule_part in f["rule"] for f in rep["findings"])


def make_docx(path):
    import docx
    from lxml import etree

    d = docx.Document()
    d.core_properties.author = "Some Author"
    p1 = d.add_paragraph("Sleep helps memory (Smith, 2020). More evidence appears later (Smith, 2020) in the text.")
    d.add_paragraph("TODO write the conclusion. Certainly! Here is the draft: **bold** leftovers.")
    d.add_paragraph("Many sources agree (Lee, 2019; Kim, 2021) (Roe, 2018) (Poe, 2017) (Doe, 2016).")
    d.add_paragraph("هذه فقرة عربية طويلة بما يكفي لاختبار اتجاه الكتابة من اليمين إلى اليسار في الملف")
    d.add_paragraph("It's not just a tool, it's a statement. We delve into a pivotal tapestry — truly.")
    for label in ("Speed:", "Safety:", "Cost:"):
        lp = d.add_paragraph()
        lp.add_run(label).bold = True
        lp.add_run(" this item is described in a plain sentence.")
    d.add_comment(p1.runs, text="please check this", author="Reviewer", initials="R")
    body = d.element.body
    p = d.add_paragraph("Kept ")
    ins = etree.SubElement(p._p, f"{{{W}}}ins", {f"{{{W}}}id": "90", f"{{{W}}}author": "Ed"})
    r = etree.SubElement(ins, f"{{{W}}}r")
    etree.SubElement(r, f"{{{W}}}t").text = "inserted words "
    dl = etree.SubElement(p._p, f"{{{W}}}del", {f"{{{W}}}id": "91", f"{{{W}}}author": "Ed"})
    r2 = etree.SubElement(dl, f"{{{W}}}r")
    etree.SubElement(r2, f"{{{W}}}delText").text = "deleted words"
    d.save(path)


def make_pptx(path):
    from pptx import Presentation

    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Title"
    s.placeholders[1].text = "Body (Smith, 2020) text"
    s.notes_slide.notes_text_frame.text = "secret speaker note"
    from pptx.util import Emu
    from lxml import etree as _et
    P = "http://schemas.openxmlformats.org/presentationml/2006/main"
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    tree = s.shapes._spTree
    sp = _et.SubElement(tree, f"{{{P}}}sp")
    nv = _et.SubElement(sp, f"{{{P}}}nvSpPr")
    _et.SubElement(nv, f"{{{P}}}cNvPr", id="99", name="Footer")
    _et.SubElement(nv, f"{{{P}}}cNvSpPr")
    nvpr = _et.SubElement(nv, f"{{{P}}}nvPr")
    _et.SubElement(nvpr, f"{{{P}}}ph", type="ftr", sz="quarter", idx="11")
    _et.SubElement(sp, f"{{{P}}}spPr")
    tx = _et.SubElement(sp, f"{{{P}}}txBody")
    _et.SubElement(tx, f"{{{A}}}bodyPr")
    para = _et.SubElement(tx, f"{{{A}}}p")
    run = _et.SubElement(para, f"{{{A}}}r")
    _et.SubElement(run, f"{{{A}}}t").text = "Prepared by Dawood for client"
    prs.slides.add_slide(prs.slide_layouts[1])  # empty placeholders
    prs.save(path)
    # inject a legacy comment
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"</Types>",
                    b'<Override PartName="/ppt/comments/comment1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.comments+xml"/></Types>')
            if item.filename == "ppt/slides/_rels/slide1.xml.rels":
                data = data.replace(b"</Relationships>",
                    b'<Relationship Id="rIdC1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="../comments/comment1.xml"/></Relationships>')
            zout.writestr(item, data)
        zout.writestr("ppt/comments/comment1.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:cmLst xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cm authorId="0" dt="2024-01-01T00:00:00.000" idx="1"><p:pos x="10" y="10"/><p:text>fix this</p:text></p:cm></p:cmLst>')
    shutil.move(tmp, path)


def make_xlsx(path):
    from openpyxl import Workbook
    from openpyxl.comments import Comment

    wb = Workbook()
    ws = wb.active
    ws["A1"] = "Total"
    ws["B1"] = "#REF!"
    ws["B2"] = "=SUM(1,2)"
    ws["A2"] = "TBD"
    ws["A1"].comment = Comment("check this cell", "Reviewer")
    wb.create_sheet("Hidden").sheet_state = "hidden"
    wb.save(path)


def make_pdf(tmp, docx_path):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(docx_path)],
                   check=True, capture_output=True)
    from pypdf import PdfReader, PdfWriter
    from pypdf.annotations import Text

    src = tmp / (docx_path.stem + ".pdf")
    w = PdfWriter(clone_from=PdfReader(str(src)))
    w.add_annotation(page_number=0, annotation=Text(text="a note", rect=(50, 50, 100, 100)))
    out = tmp / "sample.pdf"
    with open(out, "wb") as fh:
        w.write(fh)
    return out


def main():
    tmp = Path(tempfile.mkdtemp())
    docx_p, pptx_p, xlsx_p = tmp / "sample.docx", tmp / "sample.pptx", tmp / "sample.xlsx"
    make_docx(docx_p)
    make_pptx(pptx_p)
    make_xlsx(xlsx_p)

    # ---- docx
    rep = dc.scan_file(docx_p)
    check(has(rep, "comments"), "docx: comment found")
    check(has(rep, "tracked_changes", "insertions"), "docx: tracked changes found")
    check(has(rep, "metadata", "author"), "docx: author metadata found")
    check(has(rep, "placeholder"), "docx: TODO found")
    check(has(rep, "residue", "chatbot"), "docx: chatbot phrase found")
    check(has(rep, "residue", "markdown"), "docx: markdown leftover found")
    check(has(rep, "citations", "more than 3"), "docx: dense paragraph found")
    check(has(rep, "citations", "repeated"), "docx: repeated citation found")
    check(has(rep, "format", "right-to-left"), "docx: arabic paragraph without rtl found")
    check(has(rep, "ai_style", "contrast"), "docx: not-X-but-Y contrast found")
    check(has(rep, "ai_style", "stock AI word"), "docx: stock AI word found")
    check(has(rep, "ai_style", "dash"), "docx: dash connector found")
    check(has(rep, "ai_style", "bold label"), "docx: repeated bold labels found")
    out = tmp / "out.docx"
    dc.clean_file(docx_p, out, "", True, 3)
    rep2 = dc.scan_file(out)
    check(not any(f["fix"] in ("auto", "optional") for f in rep2["findings"]), "docx: no auto or optional findings after clean")
    check(has(rep2, "placeholder"), "docx: manual placeholder still reported after clean")
    import docx
    text = "\n".join(p.text for p in docx.Document(str(out)).paragraphs)
    check("inserted words" in text and "deleted words" not in text, "docx: insertion kept, deletion dropped")
    check(text.count("(Smith, 2020)") == 1, "docx: repeated citation thinned to one")
    check("More evidence appears later in the text." in text, "docx: no stray space left by thinning")
    docx.Document(str(out))  # re-opens without error
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp / "chk"), str(out)],
                       capture_output=True)
    check(r.returncode == 0 and (tmp / "chk" / "out.pdf").exists(), "docx: cleaned file opens in LibreOffice")

    # ---- style rules: plain prose and honest hedges must stay quiet
    quiet = ("Certainly, the results hold. Smith (2020) found an effect (p < .05). The sample served as the control "
             "group. Results were stable across 1990-2000 and the model is robust to outliers.")
    F = []
    dc.scan_text(F, [("p1", quiet)], 3, "optional")
    check(not any(f["category"] == "ai_style" for f in F), "style: clean prose gives no ai_style finding")
    F = []
    dc.scan_text(F, [("p1", "This is not only a plan but also a promise."),
                     ("p2", "ليست مجرد خطة بل التزام. وهذا هو حجر الزاوية."),
                     ("p3", "Additionally, the robust design enhances trust.")], 3, "optional")
    check({f["rule"] for f in F if f["category"] == "ai_style"} >= {
        "not-X-but-Y contrast", "deep-sounding saying", "several stock words in one paragraph"},
        "style: english and arabic patterns found")

    # ---- fields, notes, tool marks, traps, citation stripping, reference language
    import docx as _docx
    f_p = tmp / "fields.docx"
    d = _docx.Document()
    d.add_paragraph("Student: [Full name] \u2014 ID [Student ID]")
    d.add_paragraph("Name: [Your name]   Date: [Date]")
    d.add_paragraph("Sleep helps memory (Smith, 2020) and focus [3]. See [البقرة: 255] and the interval [a, b].")
    d.add_paragraph("Note to student: replace this paragraph with your own reflection.")
    d.add_paragraph("This report was generated by ChatGPT for the course.")
    d.add_paragraph("The pineapple test word appears here.")
    d.add_paragraph("References")
    d.add_paragraph("[1] Smith, J. (2020). Sleep and memory. Journal of Sleep, 4(2), 1-10.")
    d.add_paragraph("Lee, K. (2019). Focus and rest in students. Learning Press.")
    d.save(f_p)
    rep = dc.scan_file(f_p, 3, ["pineapple"])
    u_p = tmp / "final_report_v2.docx"
    shutil.copy(f_p, u_p)
    check(has(dc.scan_file(u_p), "filename"), "filename: underscores flagged")
    check(not has(rep, "filename"), "filename: plain name not flagged")
    check(has(rep, "placeholder", "fill-in field"), "fields: fill-in field found")
    check(has(rep, "note"), "fields: note to student found")
    check(has(rep, "residue", "tool or watermark"), "fields: tool mark found")
    check(has(rep, "trap"), "fields: trap word found")
    check(rep["stats"]["references"] == {"entries": 2, "arabic": 0, "other": 2}, "fields: reference language counted")
    out = tmp / "fields.out.docx"
    dc.clean_file(f_p, out, "", False, 3, True, True, ["pineapple"])
    ps = [p.text for p in _docx.Document(str(out)).paragraphs]
    check(ps[0] == "Student:", f"fields: label kept, field blanked ({ps[0]!r})")
    check(ps[1].split() == ["Name:", "Date:"], f"fields: two labels kept ({ps[1]!r})")
    check(ps[2] == "Sleep helps memory and focus. See [البقرة: 255] and the interval [a, b].",
          f"fields: in-text citations stripped, verse and interval kept ({ps[2]!r})")
    check(ps[7].startswith("[1] Smith"), "fields: reference list left alone")
    rep2 = dc.scan_file(out)
    check(not has(rep2, "placeholder", "fill-in field"), "fields: no fill-in field after clean")

    # ---- pptx
    rep = dc.scan_file(pptx_p)
    check(has(rep, "speaker_notes"), "pptx: speaker note found")
    check(has(rep, "comments"), "pptx: comment found")
    check(has(rep, "format", "empty title"), "pptx: empty placeholder found")
    check(has(rep, "slide_footer"), "pptx: footer text found")
    out = tmp / "out.pptx"
    dc.clean_file(pptx_p, out, "", False, 3)
    rep2 = dc.scan_file(out)
    check(not any(f["fix"] == "auto" for f in rep2["findings"]), "pptx: no auto findings after clean")
    from pptx import Presentation
    prs = Presentation(str(out))
    check(len(prs.slides) == 2 and not prs.slides[0].has_notes_slide, "pptx: reopens, notes gone")

    # ---- xlsx
    rep = dc.scan_file(xlsx_p)
    check(has(rep, "comments"), "xlsx: comment found")
    check(has(rep, "hidden", "sheets"), "xlsx: hidden sheet found")
    check(has(rep, "format", "error value"), "xlsx: error cell found")
    check(has(rep, "format", "without a calculated"), "xlsx: uncomputed formula found")
    out = tmp / "out.xlsx"
    dc.clean_file(xlsx_p, out, "", False, 3)
    rep2 = dc.scan_file(out)
    check(not any(f["fix"] == "auto" for f in rep2["findings"]), "xlsx: no auto findings after clean")
    import openpyxl
    wb = openpyxl.load_workbook(str(out))
    check(wb.active["A1"].comment is None and wb.active["A1"].value == "Total", "xlsx: reopens, comment gone, value kept")

    # ---- pdf
    if shutil.which("soffice"):
        pdf_p = make_pdf(tmp, docx_p)
        rep = dc.scan_file(pdf_p)
        check(has(rep, "comments"), "pdf: annotation found")
        out = tmp / "out.pdf"
        dc.clean_file(pdf_p, out, "", False, 3)
        rep2 = dc.scan_file(out)
        check(not any(f["fix"] == "auto" for f in rep2["findings"]), "pdf: no auto findings after clean")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
