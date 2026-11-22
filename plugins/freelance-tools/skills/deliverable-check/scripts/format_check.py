#!/usr/bin/env python3
"""format-check: scan the delivery formatting rules that deliverable_check.py does not cover.

    format_check.py FILE... [--json] [--find WORD]... [--skip CHECK]...

Checks (for --skip): calibri, code-box, header-title, slide-repeat, slide-sources, code-comments. Skip a check when the task requirements
contradict it (for example the brief asks for comments in the code).

docx   Calibri in an English document (use Arial or Times New Roman).
       Code, command or output text inside a box: paragraph shading, borders, a shaded
       cell, highlighted text, or a single-cell table.
       Header or footer text other than page numbers (a title or name on every page).
pptx   The same text repeated on most slides (a deck title or name used as a footer).
       Source lines and image credits on slides.
code   Comments in source files (policy: none unless the brief asks for them).
       Supported: py sh rb pl r yml yaml toml js jsx ts tsx java c cpp cc h hpp cs go rs php
       swift kt dart scss less css sql html htm xml.

`scan` only. Nothing is modified. Other file types are skipped.
The requirements of the task come first: a finding here is dropped when the brief asks for it.

Dependencies: lxml (and deliverable_check.py next to this file).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deliverable_check as dc  # noqa: E402

q = dc.q

# ---------------------------------------------------------------- docx

BAD_FONTS = {"calibri", "calibri light"}
MONO = re.compile(
    r"courier|consolas|menlo|monaco|lucida console|cascadia|source code|liberation mono|"
    r"dejavu sans mono|fira (?:code|mono)|jetbrains|ubuntu mono|roboto mono|sf mono|andale mono|"
    r"inconsolata|monospace", re.I)
CODE_STYLE = re.compile(r"code|verbatim|preformatted|terminal|console|command|listing", re.I)
CMD_HINT = re.compile(
    r"^(?:\$ |> |>>> |PS [A-Za-z]:\\|[A-Za-z]:\\[^>]*>|sudo |pip3? install|npm (?:install|run)|"
    r"git (?:clone|commit|push|pull|checkout)|python3? \S+\.py|cd \S|curl )")


def font_name(rf, theme) -> str:
    for att, th in (("ascii", "asciiTheme"), ("hAnsi", "hAnsiTheme")):
        t = rf.get(q("w", th))
        if t:
            return theme.get("major" if t.startswith("major") else "minor", "")
        if rf.get(q("w", att)):
            return rf.get(q("w", att))
    return ""


class Styles:
    def __init__(self, pkg: dc.Package):
        self.styles, self.names = {}, {}
        self.default_p = None
        self.theme = {}
        for n in pkg.match(r"word/theme/theme\d+\.xml$")[:1]:
            root = pkg.tree(n)
            for key, tag in (("major", "majorFont"), ("minor", "minorFont")):
                el = next(root.iter(q("a", tag)), None)
                lat = el.find(q("a", "latin")) if el is not None else None
                if lat is not None:
                    self.theme[key] = lat.get("typeface") or ""
        self.defaults = ""
        if "word/styles.xml" in pkg.parts:
            root = pkg.tree("word/styles.xml")
            for s in root.iter(q("w", "style")):
                sid = s.get(q("w", "styleId"))
                self.styles[sid] = s
                nm = s.find(q("w", "name"))
                self.names[sid] = nm.get(q("w", "val")) if nm is not None else sid
                if s.get(q("w", "type")) == "paragraph" and s.get(q("w", "default")) in ("1", "true"):
                    self.default_p = sid
            rf = root.find(f"{q('w', 'docDefaults')}/{q('w', 'rPrDefault')}/{q('w', 'rPr')}/{q('w', 'rFonts')}")
            if rf is not None:
                self.defaults = font_name(rf, self.theme)

    def chain(self, sid):
        seen = set()
        while sid and sid in self.styles and sid not in seen:
            seen.add(sid)
            st = self.styles[sid]
            yield sid, st
            b = st.find(q("w", "basedOn"))
            sid = b.get(q("w", "val")) if b is not None else None

    def explicit_font(self, sid) -> str:
        for _, st in self.chain(sid):
            rf = st.find(f"{q('w', 'rPr')}/{q('w', 'rFonts')}")
            if rf is not None:
                f = font_name(rf, self.theme)
                if f:
                    return f
        return ""

    def is_code_style(self, sid) -> bool:
        return any(CODE_STYLE.search(s or "") or CODE_STYLE.search(self.names.get(s, ""))
                   for s, _ in self.chain(sid))

    def style_box(self, sid) -> list:
        out = []
        for _, st in self.chain(sid):
            ppr = st.find(q("w", "pPr"))
            if ppr is None:
                continue
            shd = ppr.find(q("w", "shd"))
            if shd is not None and shaded(shd):
                out.append("style shading")
            if has_border(ppr.find(q("w", "pBdr"))):
                out.append("style border")
        return out


def shaded(shd) -> bool:
    if (shd.get(q("w", "val")) or "") == "nil":
        return False
    return (shd.get(q("w", "fill")) or "auto").lower() not in ("auto", "ffffff", "")


def has_border(bd) -> bool:
    return bd is not None and any((b.get(q("w", "val")) or "") not in ("", "nil", "none") for b in bd)


def para_style(p, S: Styles):
    ps = p.find(f"{q('w', 'pPr')}/{q('w', 'pStyle')}")
    return ps.get(q("w", "val")) if ps is not None else S.default_p


def para_runs(p, S: Styles):
    """(font, text, run) for each text run that belongs to paragraph p."""
    base = S.explicit_font(para_style(p, S)) or S.defaults
    for r in p.iter(q("w", "r")):
        if next(r.iterancestors(q("w", "p"))) is not p:
            continue
        txt = "".join(t.text or "" for t in r.findall(q("w", "t")))
        if not txt.strip():
            continue
        font = ""
        rpr = r.find(q("w", "rPr"))
        if rpr is not None:
            rf = rpr.find(q("w", "rFonts"))
            if rf is not None:
                font = font_name(rf, S.theme)
            if not font:
                rs = rpr.find(q("w", "rStyle"))
                if rs is not None:
                    font = S.explicit_font(rs.get(q("w", "val")))
        yield font or base, txt, r


def box_reasons(p, runs, S: Styles) -> list:
    out = []
    ppr = p.find(q("w", "pPr"))
    if ppr is not None:
        shd = ppr.find(q("w", "shd"))
        if shd is not None and shaded(shd):
            out.append("paragraph shading")
        if has_border(ppr.find(q("w", "pBdr"))):
            out.append("paragraph border")
    out += S.style_box(para_style(p, S))
    for _, _, r in runs:
        rpr = r.find(q("w", "rPr"))
        if rpr is None:
            continue
        shd = rpr.find(q("w", "shd"))
        hl = rpr.find(q("w", "highlight"))
        if shd is not None and shaded(shd):
            out.append("text shading")
            break
        if hl is not None and (hl.get(q("w", "val")) or "none") != "none":
            out.append("highlight")
            break
    tc = next(p.iterancestors(q("w", "tc")), None)
    if tc is not None:
        tcpr = tc.find(q("w", "tcPr"))
        shd = tcpr.find(q("w", "shd")) if tcpr is not None else None
        if shd is not None and shaded(shd):
            out.append("table cell shading")
        tr = tc.getparent()
        tbl = tr.getparent()
        if len(tbl.findall(q("w", "tr"))) == 1 and len(tr.findall(q("w", "tc"))) == 1:
            out.append("single-cell table")
    return list(dict.fromkeys(out))


CHECKS = ("calibri", "code-box", "header-title", "slide-repeat", "slide-sources", "code-comments")
PAGE_WORDS = re.compile(r"\b(?:page|pages|of|صفحة|من)\b|[\d\s\-\u2013\u2014/|:.,]", re.I)
SOURCE_LINE = re.compile(
    r"^\s*(?:sources?|image sources?|photo sources?|image credits?|photo credits?|credits?|references?|"
    r"photo by|image by|images? (?:from|courtesy)|photos? (?:from|courtesy)|"
    r"المصدر|المصادر|مصدر الصورة|مصادر الصور|المراجع)\s*[:\uFF1A\-]", re.I)
SOURCE_TITLE = re.compile(r"^\s*(?:sources?|references?|bibliography|image credits?|المصادر|المراجع|قائمة المراجع)\s*$", re.I)


def scan_docx(pkg: dc.Package, F: list, skip=()) -> dict:
    S = Styles(pkg)
    doc = pkg.tree("word/document.xml")
    latin: Counter = Counter()
    calibri_paras, boxed = [], []
    all_text = []

    def count_fonts(p, label):
        hit = False
        for font, txt, _ in para_runs(p, S):
            n = len(re.findall(r"[A-Za-z]", txt))
            if n and font:
                latin[font] += n
                if font.lower() in BAD_FONTS:
                    hit = True
        if hit:
            calibri_paras.append(f"{label}: {''.join(t for _, t, _ in para_runs(p, S)).strip()[:50]}")

    for i, p in enumerate(doc.iter(q("w", "p")), 1):
        runs = list(para_runs(p, S))
        text = "".join(t for _, t, _ in runs)
        all_text.append(text)
        count_fonts(p, f"p{i}")
        if not text.strip():
            continue
        mono = sum(len(t) for f, t, _ in runs if MONO.search(f))
        codeish = (mono >= 0.6 * len(text) or S.is_code_style(para_style(p, S))
                   or bool(CMD_HINT.match(text.strip())))
        if codeish and "code-box" not in skip:
            why = box_reasons(p, runs, S)
            if why:
                boxed.append(f"p{i}: {text.strip()[:40]} ({', '.join(why)})")
    for n in pkg.match(r"word/(header|footer)\d*\.xml$"):
        for i, p in enumerate(pkg.tree(n).iter(q("w", "p")), 1):
            count_fonts(p, f"{n.split('/')[-1]} p{i}")

    joined = "".join(all_text)
    english = len(dc.LETTER.findall(joined)) >= 10 and not dc.needs_rtl(joined)
    total = sum(latin.values()) or 1
    if english and calibri_paras and "calibri" not in skip:
        share = ", ".join(f"{f} {round(100 * n / total)}%" for f, n in latin.most_common(3))
        add = dc.add
        add(F, "format", "Calibri in an English docx", "manual", len(calibri_paras), calibri_paras,
            f"Latin text by font: {share}. Use Arial or Times New Roman (one family) unless the brief names another font.")
    dc.add(F, "format", "code, command or output text inside a background box", "manual", len(boxed), boxed,
           "Use ordinary paragraphs: no shading, borders or single-cell table, unless the brief asks for a code box.")
    if "header-title" not in skip:
        heads = []
        for n in pkg.match(r"word/(header|footer)\d*\.xml$"):
            for p in pkg.tree(n).iter(q("w", "p")):
                text = dc.para_text(p, q("w", "p"), q("w", "t")).strip()
                if text and PAGE_WORDS.sub("", text):
                    heads.append(f"{n.split('/')[-1]}: {text[:50]}")
        dc.add(F, "format", "header or footer text besides page numbers", "manual", len(heads), heads,
               "Keep only the page number in headers and footers, not the report title or the author name.")
    return {"paragraphs": len(all_text), "latin_fonts": dict(latin)}


# ---------------------------------------------------------------- pptx


def scan_pptx(pkg: dc.Package, F: list, skip=()) -> dict:
    def slide_no(n):
        return int(re.search(r"(\d+)\.xml$", n).group(1))

    slides = sorted(pkg.match(r"ppt/slides/slide\d+\.xml$"), key=slide_no)
    seen: dict = {}
    sources = []
    for n in slides:
        no = slide_no(n)
        texts = set()
        for sp in pkg.tree(n).iter(q("p", "sp")):
            ph = sp.find(f"{q('p', 'nvSpPr')}/{q('p', 'nvPr')}/{q('p', 'ph')}")
            paras = [dc.para_text(p, q("a", "p"), q("a", "t")).strip() for p in sp.iter(q("a", "p"))]
            paras = [x for x in paras if x]
            whole = " ".join(paras)
            if whole and not whole.isdigit() and (ph is None or ph.get("type") not in ("title", "ctrTitle", "sldNum")):
                texts.add(re.sub(r"\s+", " ", whole).lower())
            for i, x in enumerate(paras):
                if SOURCE_LINE.match(x) or (ph is not None and ph.get("type") in ("title", "ctrTitle") and SOURCE_TITLE.match(x)):
                    sources.append(f"slide {no}: {x[:60]}")
        for tx in texts:
            seen.setdefault(tx, []).append(no)
    need = max(3, round(0.6 * len(slides)))
    repeated = [f"{tx[:50]} (on {len(v)} of {len(slides)} slides)" for tx, v in seen.items() if len(v) >= need]
    if "slide-repeat" not in skip:
        dc.add(F, "format", "same text repeated on most slides", "manual", len(repeated), repeated,
               "A deck title or name used as a footer. Keep only slide numbers.")
    if "slide-sources" not in skip:
        dc.add(F, "format", "source line or image credit on a slide", "manual", len(sources), sources,
               "Do not put sources or image credits on slides, unless the brief asks for them.")
    return {"slides": len(slides)}


# ---------------------------------------------------------------- code files

HASH = {"line": ("#",), "block": (), "quotes": "\"'", "triple": True}
SLASH = {"line": ("//",), "block": (("/*", "*/"),), "quotes": "\"'`", "triple": False}
CSSF = {"line": (), "block": (("/*", "*/"),), "quotes": "\"'", "triple": False}
SQLF = {"line": ("--",), "block": (("/*", "*/"),), "quotes": "'\"", "triple": False}
HTMLF = {"line": (), "block": (("<!--", "-->"),), "quotes": "", "triple": False}
SHELL = {"line": ("#",), "block": (), "quotes": "\"'", "triple": False}
FAMILIES = {
    ".py": HASH, ".sh": SHELL, ".bash": SHELL, ".rb": SHELL, ".pl": SHELL, ".r": SHELL,
    ".yml": SHELL, ".yaml": SHELL, ".toml": SHELL,
    ".js": SLASH, ".jsx": SLASH, ".ts": SLASH, ".tsx": SLASH, ".java": SLASH, ".c": SLASH,
    ".cpp": SLASH, ".cc": SLASH, ".h": SLASH, ".hpp": SLASH, ".cs": SLASH, ".go": SLASH,
    ".rs": SLASH, ".php": SLASH, ".swift": SLASH, ".kt": SLASH, ".dart": SLASH,
    ".scss": SLASH, ".less": SLASH, ".css": CSSF, ".sql": SQLF,
    ".html": HTMLF, ".htm": HTMLF, ".xml": HTMLF,
}
DIRECTIVE = re.compile(
    r"^(?:#|//|/\*|--)\s*(?:noqa|type:|pragma|pylint|eslint|prettier|@ts-|istanbul|fmt:|nolint|go:|"
    r"\+build|-\*-|vim:|shellcheck|region|endregion|!)", re.I)
BANNER = re.compile(r"[-=*#~_]{4,}")


def find_comments(text: str, fam: dict) -> list:
    """Return (line, kind, snippet, line_count) for each comment. kind: line, inline, block, docstring."""
    out, n, i, line = [], len(text), 0, 1
    code_on_line, last_code, cur_last = False, "", ""

    def newline():
        nonlocal line, code_on_line, last_code, cur_last
        line += 1
        if code_on_line:
            last_code = cur_last
        code_on_line, cur_last = False, ""

    while i < n:
        c = text[i]
        if c == "\n":
            newline()
            i += 1
            continue
        if c in " \t\r":
            i += 1
            continue
        hit = False
        for a, b in fam["block"]:
            if text.startswith(a, i):
                j = text.find(b, i + len(a))
                j = n if j < 0 else j + len(b)
                seg = text[i:j]
                out.append((line, "inline" if code_on_line else "block",
                            seg.strip().splitlines()[0][:60], seg.count("\n") + 1))
                for ch in seg:
                    if ch == "\n":
                        newline()
                i, hit = j, True
                break
        if hit:
            continue
        for m in fam["line"]:
            if text.startswith(m, i) and (m != "#" or i == 0 or text[i - 1] in " \t\n;"):
                j = text.find("\n", i)
                j = n if j < 0 else j
                seg = text[i:j]
                shebang = m == "#" and seg.startswith("#!") and line == 1
                coding = m == "#" and line <= 2 and re.match(r"#.*coding[:=]", seg)
                if not (shebang or coding):
                    out.append((line, "inline" if code_on_line else "line", seg.strip()[:60], 1))
                i, hit = j, True
                break
        if hit:
            continue
        if c in fam["quotes"]:
            if fam["triple"] and text.startswith(c * 3, i):
                end = text.find(c * 3, i + 3)
                end = n if end < 0 else end + 3
                seg = text[i:end]
                if not code_on_line and last_code in ("", ":"):
                    out.append((line, "docstring", seg.strip().splitlines()[0][:60], seg.count("\n") + 1))
                for ch in seg:
                    if ch == "\n":
                        newline()
                code_on_line, cur_last, i = True, c, end
                continue
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == c:
                    j += 1
                    break
                if text[j] == "\n" and c != "`":
                    break
                j += 1
            seg = text[i:j]
            for ch in seg:
                if ch == "\n":
                    newline()
            code_on_line, cur_last, i = True, c, j
            continue
        code_on_line, cur_last = True, c
        i += 1
    return out


def scan_code(path: Path, F: list, skip=()) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    found = [c for c in find_comments(text, FAMILIES[path.suffix.lower()]) if not DIRECTIVE.match(c[2])]
    lines = sum(1 for ln in text.splitlines() if ln.strip())
    comment_lines = sum(c[3] for c in found)
    kinds = Counter(c[1] for c in found)
    banners = sum(1 for c in found if c[1] in ("line", "block") and BANNER.search(c[2]))
    breakdown = ", ".join(f"{v} {k}" for k, v in sorted(kinds.items()))
    pct = round(100 * comment_lines / lines) if lines else 0
    note = (f"{comment_lines} comment lines out of {lines} non-blank lines ({pct}%); {breakdown}"
            f"{'; ' + str(banners) + ' banner(s)' if banners else ''}. "
            "Policy: none unless the brief asks for comments.")
    if "code-comments" not in skip:
        dc.add(F, "format", "comments in code", "manual", len(found),
               [f"line {c[0]}: {c[2]}" for c in found], note)
    traps = []
    for word in dc.TRAPS:
        rx = re.compile(re.escape(word), re.I)
        for ln, row in enumerate(text.splitlines(), 1):
            m = rx.search(row)
            if m:
                traps.append(f"line {ln}: {dc.snippet(row, m)}")
    dc.add(F, "trap", "word from a hidden instruction in the brief", "manual", len(traps), traps,
           "The brief planted this word to catch AI use. Remove or reword it.")
    return {"lines": lines, "comment_lines": comment_lines}


# ---------------------------------------------------------------- driver


def scan_file(path: Path, traps=(), skip=()) -> dict | None:
    dc.TRAPS[:] = [t for t in traps if t.strip()]
    F: list = []
    ext = path.suffix.lower()
    if ext == ".docx":
        kind, stats = "docx", scan_docx(dc.Package(path), F, skip)
    elif ext == ".pptx":
        kind, stats = "pptx", scan_pptx(dc.Package(path), F, skip)
    elif ext in FAMILIES:
        kind, stats = "code", scan_code(path, F, skip)
    else:
        return None
    return {"file": str(path), "kind": kind, "stats": stats, "findings": F}


def print_report(rep: dict):
    print(f"{Path(rep['file']).name}  ({rep['kind']})")
    if not rep["findings"]:
        print("  no findings")
    for f in rep["findings"]:
        print(f"  [{f['fix']:<8}] {f['category']:<8} {f['rule']}: {f['count']}")
        for e in f["examples"]:
            print(f"             - {e}")
        if f["note"]:
            print(f"             ({f['note']})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--find", action="append", default=[], metavar="WORD",
                    help="report this word or phrase in code files (a trap from the brief); repeatable")
    ap.add_argument("--skip", action="append", default=[], choices=CHECKS, metavar="CHECK",
                    help="leave this check out (the task requirements contradict it); repeatable")
    a = ap.parse_args(argv)
    if a.skip:
        print(f"skipped checks: {', '.join(sorted(set(a.skip)))}", file=sys.stderr)
    reps = []
    for f in a.files:
        rep = scan_file(f, a.find, a.skip)
        if rep is None:
            print(f"{f.name}: no formatting checks for this file type")
        else:
            reps.append(rep)
    if a.json:
        print(json.dumps(reps, ensure_ascii=False, indent=2))
    else:
        for r in reps:
            print_report(r)
    return 1 if any(r["findings"] for r in reps) else 0


if __name__ == "__main__":
    sys.exit(main())
