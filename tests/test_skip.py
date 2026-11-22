#!/usr/bin/env python3
"""Tests for --skip in deliverable_check.py and format_check.py.

Needs: python-docx>=1.2, lxml, pypdf.
Run: python3 tests/test_skip.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins" / "freelance-tools" / "skills" / "deliverable-check" / "scripts"
failures = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


def run(script, *args):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def main():
    import docx

    tmp = Path(tempfile.mkdtemp())
    d = docx.Document()
    d.styles["Normal"].font.name = "Calibri"
    p = d.add_paragraph("Sleep helps memory (Smith, 2020). TODO write the conclusion.")
    d.add_comment(p.runs, text="check this", author="Reviewer", initials="R")
    f = tmp / "sample.docx"
    d.save(f)

    # ---- deliverable_check scan
    code, out, err = run("deliverable_check.py", "scan", f)
    check("comments" in out and "placeholder" in out, "scan: comment and placeholder reported without --skip")
    code, out, err = run("deliverable_check.py", "scan", f, "--skip", "comments", "--skip", "placeholder")
    check("word comments" not in out and "todo or tbd" not in out, "scan: skipped categories are not reported")
    check("skipped categories: comments, placeholder" in err, "scan: skipped categories are announced")
    code, out, err = run("deliverable_check.py", "scan", f, "--skip", "nonsense")
    check(code != 0 and "invalid choice" in err, "scan: unknown category rejected")

    # ---- deliverable_check clean
    out_p = tmp / "kept.docx"
    run("deliverable_check.py", "clean", f, "-o", out_p, "--skip", "comments")
    doc = docx.Document(str(out_p))
    check(len(list(doc.comments)) == 1, "clean: --skip comments keeps the comment")
    out_q = tmp / "cleaned.docx"
    run("deliverable_check.py", "clean", f, "-o", out_q)
    check(len(list(docx.Document(str(out_q)).comments)) == 0, "clean: comment removed by default")

    # ---- format_check
    code, out, err = run("format_check.py", f)
    check("Calibri" in out, "format: Calibri reported without --skip")
    code, out, err = run("format_check.py", f, "--skip", "calibri")
    check("Calibri" not in out and "skipped checks: calibri" in err, "format: --skip calibri drops the finding and says so")
    py = tmp / "a.py"
    py.write_text("# set x\nx = 1\n", encoding="utf-8")
    code, out, err = run("format_check.py", py, "--skip", "code-comments")
    check("comments in code" not in out, "format: --skip code-comments drops the finding")
    code, out, err = run("format_check.py", py, "--skip", "nonsense")
    check(code != 0 and "invalid choice" in err, "format: unknown check rejected")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
