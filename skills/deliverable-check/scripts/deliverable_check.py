#!/usr/bin/env python3
"""deliverable-check: scan and clean docx, pptx, xlsx and pdf files before delivery.

    deliverable_check.py scan  FILE... [--json] [--max-per-paragraph N] [--find WORD]...
    deliverable_check.py clean FILE... [-o OUT] [--author NAME] [--thin-citations]
                               [--strip-citations] [--keep-fields] [--find WORD]...

`scan` never modifies a file. `clean` always writes a new file (default
<name>.clean.<ext> next to the original) and re-scans it.

Dependencies: lxml, pypdf.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
}


def q(prefix: str, tag: str) -> str:
    return "{%s}%s" % (NS[prefix], tag)


def local(el) -> str:
    return etree.QName(el).localname


PARSER = etree.XMLParser(resolve_entities=False, huge_tree=True)

# ---------------------------------------------------------------- text rules

TOOL_TRACE = re.compile(
    r"python-docx|python-pptx|openpyxl|claude|anthropic|openai|chatgpt|gpt-?\d|gemini|"
    r"copilot|pandoc|libreoffice|docx4j|aspose|reportlab|fpdf|weasyprint|wkhtmltopdf|pypdf",
    re.I,
)

TEXT_RULES = [
    ("placeholder", "todo or tbd marker", re.compile(
        r"\b(?:TODO|TBD|FIXME)\b|\bXXX+\b|(?i:\[(?:insert|placeholder|todo|tbd)[^\]]*\])")),
    ("placeholder", "lorem ipsum", re.compile(r"lorem ipsum", re.I)),
    ("placeholder", "template field", re.compile(
        r"\{\{[^}]{1,60}\}\}|<(?:insert|your|name|date)[^>]{0,40}>"
        r"|<<[^>]{1,40}>>")),
    ("placeholder", "missing source marker", re.compile(
        r"\[(?:citation needed|source|ref|reference)\]|\[بحاجة لمصدر\]", re.I)),
    ("residue", "chatbot phrase", re.compile(
        r"(?i)\bas an ai\b|\bi hope this helps\b|\blet me know if you\b|\bknowledge cutoff\b"
        r"|\bI (?:can't|cannot) (?:browse|access)\b"
        r"|(?:^|(?<=[.!?]\s))\s*(?:certainly|of course|sure|absolutely|great question)!"
        r"|(?:^|(?<=[.!?]\s))\s*here(?:'s| is| are)\b[^.]{0,60}:"
        r"|آمل أن (?:يفيدك|يكون هذا مفيد)|يسعدني (?:مساعدتك|أن أساعدك)|كنموذج لغوي"
        r"|^\s*(?:بالتأكيد|بكل سرور|إليك)\b|هل (?:تريد|ترغب) (?:مني|أن (?:أ|ن))")),
    ("note", "note to the writer or student", re.compile(
        r"(?i)\bnotes? (?:to|for) (?:the )?(?:student|writer|self|client|user|freelancer)\b"
        r"|\b(?:replace|update|adjust|edit|customi[sz]e|personali[sz]e) (?:this|these|the (?:above|following|text|section)|with your)\b"
        r"|\b(?:you|the student) (?:should|can|may|need to|might want to) (?:add|replace|insert|edit|update|adjust|include|change)\b"
        r"|\bbefore (?:submitting|you submit)\b|\bremember to\b|\bfeel free to\b|\badd your (?:own|name|details|information)\b"
        r"|ملاحظة\s*(?:لل?طالب|لك|للعميل|للكاتب|هامة)|(?:يرجى|يُرجى|يمكنك|يمكن للطالب|تأكد من|لا تنس[ىي])\s+(?:استبدال|تعديل|إضافة|تغيير|كتابة|وضع)"
        r"|قبل التسليم|استبدل (?:هذا|هذه|النص)|ضع اسمك|أضف اسمك")),
    ("residue", "tool or watermark mark", re.compile(
        r"(?i)\b(?:generated|created|written|made|produced|designed) (?:by|with|using) (?:chat ?gpt|claude|gemini|copilot|gamma|ai|an ai|artificial intelligence|canva|beautiful\.ai|tome)\b"
        r"|chat(?:gpt)?\.(?:com|openai\.com)|claude\.ai|gemini\.google\.com|gamma\.app|perplexity\.ai"
        r"|تم (?:إنشاؤه|توليده|إنشاء هذا|توليد هذا)\s+(?:بواسطة|باستخدام)")),
    ("residue", "markdown leftover", re.compile(
        r"\*\*[^*\n]{1,80}\*\*|^\s{0,3}#{1,6}\s+\S|```|^\s*\|.+\|\s*$|^\s*---+\s*$")),
    ("residue", "citation artifact", re.compile(
        r"\u3010[^\u3011]{1,60}\u3011|contentReference\[oaicite|oaicite:\d+"
        r"|\bturn\d+(?:search|view|file|news)\d+\b|utm_source=(?:chatgpt|openai|claude)", re.I)),
]

# AI-writing tells, adapted from the humanizer skill (blader/humanizer, MIT; based on
# Wikipedia "Signs of AI writing"). One sighting in a paragraph is enough for these.
STYLE_RULES = [
    ("not-X-but-Y contrast", re.compile(
        r"(?i)\bnot (?:just|only|merely|simply)\b[^.;]{0,80}\bbut\b"
        r"|\bit(?:'s| is) not\b[^.;]{1,60}[,;]\s*it(?:'s| is)\b"
        r"|(?:ليس|ليست)\s+(?:فقط|مجرد|مجرّد)[^.؛]{0,60}\s(?:بل|وإنما)\b|لا يقتصر[^.؛]{0,60}\sبل\b")),
    ("stock closer", re.compile(
        r"(?i)(?:^|(?<=[.!?]\s))(?:that(?:'s| is) the real (?:win|point|story)|read that again"
        r"|let that sink in|that distinction matters|the message was clear|this shows the importance)\b")),
    ("deep-sounding saying", re.compile(
        r"(?i)\bthe real question is\b|\bat its core\b|\bwhat really matters\b|\bthe heart of the matter\b"
        r"|\bthe deeper issue\b|\bfundamentally,|في جوهره|لب الموضوع|بيت القصيد|حجر الزاوية")),
    ("staged run-up", re.compile(
        r"(?i)\blet'?s (?:dive|explore|break (?:this|it) down|unpack)\b|\bhere'?s what you need to know\b"
        r"|\bwithout further ado\b|\bhere'?s the thing\b|^\s*honestly\?|\breal talk\b"
        r"|دعونا نغوص|هيا بنا نتعرف|دعنا نستكشف")),
    ("argument with no one", re.compile(
        r"(?i)\bI'?m not saying\b|\bdon'?t get me wrong\b|\bto be clear,|\bthis isn'?t (?:mainly |really )?about\b"
        r"|\ba tempting approach\b|\bone might be tempted\b")),
    ("dash used as connector", re.compile(r"\u2014|\u2015|\s--\s|\s\u2013\s")),
    ("inflated significance or sales language", re.compile(
        r"(?i)\bnestled\b|\bbreathtaking\b|\bmust-visit\b|\bgroundbreaking\b|\brich (?:cultural )?heritage\b"
        r"|\bin the heart of\b|\bdiverse array\b|\bstands as a\b|\bcontinues to thrive\b"
        r"|\bthe future looks bright\b|\bexciting times\b|\ba step in the right direction\b"
        r"|\bevolving landscape\b|\bsetting the stage for\b|\bindelible\b|\benduring legacy\b"
        r"|في عالم اليوم|نسيج غني|لا يخفى على أحد")),
    ("stock AI word", re.compile(
        r"(?i)\bdelv(?:e|es|ed|ing)\b|\btapestry\b|\btestament\b|\bpivotal\b|\bunderscor(?:e|es|ed|ing)\b"
        r"|\bshowcas(?:e|es|ed|ing)\b|\bintricate\b|\bintricacies\b|\bmeticulous(?:ly)?\b|\bvibrant\b|\bdeep dive\b")),
    ("-ing rider on a plain fact", re.compile(
        r"(?i),\s+(?:highlighting|underscoring|emphasizing|reflecting|symbolizing|fostering|cultivating"
        r"|showcasing|contributing to)\b")),
    ("unnamed authority", re.compile(
        r"(?i)\bexperts? (?:argue|believe|say|agree)\b|\bindustry reports\b|\bsome critics\b"
        r"|\bobservers (?:have )?(?:noted|cited|say)\b")),
    ("knowledge-limit hedge", re.compile(
        r"(?i)\bas of my (?:last|knowledge)\b|\bup to my last (?:training|update)\b"
        r"|\bwhile specific details (?:are|remain) (?:limited|scarce)\b|\bmaintains? a low profile\b"
        r"|\bbased on (?:the )?(?:available|provided) (?:information|sources)\b")),
    ("emoji or arrow decoration", re.compile(r"[\U0001F300-\U0001FAFF\u2190-\u21FF\u2600-\u27BF]")),
]
# Common in honest prose too, so a paragraph needs two different ones to count.
WEAK_STYLE = [re.compile(p, re.I) for p in (
    r"\badditionally\b", r"\bcrucial\b", r"\benhanc(?:e|es|ed|ing)\b", r"\brobust\b", r"\blandscape\b",
    r"\bgarner(?:s|ed|ing)?\b", r"\binterplay\b", r"\bvaluable\b", r"\bplays? a (?:key|crucial|vital|pivotal) role\b",
    r"\b(?:serves|stands|functions|operates) as\b", r"\bboasts\b", r"\bever-(?:evolving|changing)\b",
    r"ومن الجدير بالذكر", r"لا شك أن", r"تلعب دور[اً]{1,2} محوري[اً]{0,2}", r"في ظل التطورات المتسارعة",
    r"يعد من أبرز")]

# Fill-in fields such as "[Full name]" or "[Student ID]". Brackets holding a digit (citations, Quran
# references, intervals) and to-do or missing-source markers are left to the placeholder rules.
FIELD = re.compile(
    r"\[(?![^\]]*\d)(?!sic\])(?!(?:citation needed|source|ref|reference|بحاجة لمصدر)\])"
    r"(?!(?i:insert|placeholder|todo|tbd|أدخل|ادخل))(?=[^\]]*[A-Za-z\u0600-\u06FF]{2})[^\[\]\n]{2,40}\]")
SEP = r"\-\u2013\u2014|/\u060c,"
# A field plus the separator and bare label in front of it: "Student: [Full name] — ID [Student ID]"
# becomes "Student:". A label that ends in a colon is kept.
FIELD_STRIP = re.compile(rf"(?:\s*[{SEP}]\s*[^\s:\[\]{SEP}]{{1,12}})?\s*{FIELD.pattern}")
SEP_TAIL = re.compile(rf"[\s{SEP}]+$")
REF_HEAD = re.compile(
    r"^\s*(?:references?|bibliography|works cited|reference list|sources|المراجع|قائمة المراجع"
    r"|المصادر والمراجع|المصادر|مراجع البحث)\s*[:：]?\s*$", re.I)
TRAPS: list = []

CITE_PAREN = re.compile(
    r"\((?=[^()\n]*[^\W\d_])[^()\n]{1,120}?[,،]\s*(?:\d{4}[a-z]?|n\.d\.|د\.ت)[^()\n]{0,80}\)")
CITE_NUM = re.compile(r"\[\d+(?:\s*[-–,،]\s*\d+)*\]")
CITE_NARR = re.compile(
    r"(?:\b[A-Z][A-Za-z'-]+(?: (?:and|&) [A-Z][A-Za-z'-]+| et al\.)?"
    r"|[\u0600-\u06FF]+(?: وآخرون)?)\s*\(\d{4}[a-zم]?(?:[,،][^()\n]{0,30})?\)")
ARABIC = re.compile(r"[\u0600-\u06FF]")
LETTER = re.compile(r"[^\W\d_]")


def snippet(text: str, m: re.Match) -> str:
    s = re.sub(r"\s+", " ", text[max(0, m.start() - 20): m.end() + 20]).strip()
    return s[:80]


def norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def find_cites(text: str):
    out = []
    for rx, kind in ((CITE_PAREN, "parenthetical"), (CITE_NUM, "numeric"), (CITE_NARR, "narrative")):
        for m in rx.finditer(text):
            out.append((m.start(), kind, m.group(0)))
    return out


def needs_rtl(text: str) -> bool:
    letters = LETTER.findall(text)
    return len(letters) >= 10 and len(ARABIC.findall(text)) >= 0.5 * len(letters)


def add(F, category, rule, fix, count, examples=(), note=""):
    if count:
        F.append({"category": category, "rule": rule, "fix": fix, "count": count,
                  "examples": list(examples)[:5], "note": note})


def ref_start(texts) -> int | None:
    """Index of the last reference-list heading, or None."""
    idx = [i for i, t in enumerate(texts) if REF_HEAD.match(t)]
    return idx[-1] if idx else None


def ref_stats(texts) -> dict:
    i = ref_start(texts)
    if i is None:
        return {}
    entries = [t for t in texts[i + 1:] if len(t.strip()) > 15]
    ar = sum(1 for t in entries if needs_rtl(t))
    return {"entries": len(entries), "arabic": ar, "other": len(entries) - ar}


def scan_text(F, paras, max_cites, thin_fix, field_fix="manual"):
    """paras: list of (where, text). Adds placeholder, note, residue, trap and citation findings."""
    fields = [f"{w}: {snippet(t, m)}" for w, t in paras for m in [FIELD.search(t)] if m]
    add(F, "placeholder", "fill-in field such as [Full name]", field_fix, len(fields), fields,
        "clean blanks the field and keeps its label (Student: [Full name] becomes Student:)."
        if field_fix == "auto" else "")
    traps = []
    for word in TRAPS:
        rx = re.compile(re.escape(word), re.I)
        traps += [f"{w}: {snippet(t, m)}" for w, t in paras for m in [rx.search(t)] if m]
    add(F, "trap", "word from a hidden instruction in the brief", "manual", len(traps), traps,
        "The brief planted this word to catch AI use. Remove or reword it.")
    buckets: dict = {}
    for where, text in paras:
        for cat, rule, rx in TEXT_RULES:
            m = rx.search(text)
            if m:
                buckets.setdefault((cat, rule), []).append(f"{where}: {snippet(text, m)}")
    for (cat, rule), items in buckets.items():
        add(F, cat, rule, "manual", len(items), items)

    style: dict = {}
    for where, text in paras:
        for rule, rx in STYLE_RULES:
            m = rx.search(text)
            if m:
                style.setdefault(rule, []).append(f"{where}: {snippet(text, m)}")
        hits = {m.group(0).lower() for rx in WEAK_STYLE for m in [rx.search(text)] if m}
        if len(hits) >= 2:
            style.setdefault("several stock words in one paragraph", []).append(
                f"{where}: {', '.join(sorted(hits))[:80]}")
    for rule, items in style.items():
        add(F, "ai_style", rule, "manual", len(items), items)

    words = sum(len(t.split()) for _, t in paras)
    total = dense_max = 0
    dense, repeated = [], []
    for where, text in paras:
        cites = find_cites(text)
        n = len(cites)
        total += n
        dense_max = max(dense_max, n)
        if n > max_cites:
            dense.append(f"{where}: {n} citations")
        keys = [norm_key(c[2]) for c in cites if c[1] != "narrative"]
        dup = len(keys) - len(set(keys))
        if dup:
            repeated.append(f"{where}: {dup} repeated")
    add(F, "citations", f"paragraphs with more than {max_cites} citations", "manual", len(dense), dense,
        "Suggest merging or dropping only with the user's approval.")
    add(F, "citations", "same citation repeated inside one paragraph", thin_fix, len(repeated), repeated,
        "clean --thin-citations keeps the first occurrence." if thin_fix == "optional" else "")
    return {"words": words, "citations": total,
            "per_1000_words": round(total * 1000 / words, 1) if words else 0.0,
            "max_in_paragraph": dense_max}


# ---------------------------------------------------------------- OOXML package


class Package:
    def __init__(self, path: Path):
        with zipfile.ZipFile(path) as z:
            self.order = [i.filename for i in z.infolist() if not i.filename.endswith("/")]
            self.parts = {n: z.read(n) for n in self.order}
        self.trees: dict = {}
        self.dirty: set = set()
        self.removed: set = set()

    def tree(self, name):
        if name not in self.trees:
            self.trees[name] = etree.fromstring(self.parts[name], PARSER)
        return self.trees[name]

    def touch(self, name):
        self.dirty.add(name)

    def match(self, pattern):
        rx = re.compile(pattern)
        return sorted(n for n in self.parts if rx.match(n) and n not in self.removed)

    def save(self, out: Path):
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for n in self.order:
                if n in self.removed:
                    continue
                if n in self.dirty:
                    data = etree.tostring(self.trees[n], xml_declaration=True,
                                          encoding="UTF-8", standalone=True)
                else:
                    data = self.parts[n]
                z.writestr(n, data)


def resolve(src_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(src_part), target))


def rels_source(rels_name: str) -> str:
    d, f = posixpath.split(rels_name)
    src = f[:-5]
    return posixpath.join(posixpath.dirname(d), src) if src else ""


def kind_of(pkg: Package) -> str:
    if "word/document.xml" in pkg.parts:
        return "docx"
    if "ppt/presentation.xml" in pkg.parts:
        return "pptx"
    if "xl/workbook.xml" in pkg.parts:
        return "xlsx"
    raise ValueError("not a docx, pptx or xlsx package")


def para_text(p, ptag, ttag) -> str:
    return "".join((t.text or "") for t in p.iter(ttag) if next(t.iterancestors(ptag)) is p)


def scan_metadata(pkg: Package, F):
    auto, manual = [], []
    if "docProps/core.xml" in pkg.parts:
        root = pkg.tree("docProps/core.xml")
        for key, tag in (("creator", q("dc", "creator")), ("lastModifiedBy", q("cp", "lastModifiedBy")),
                         ("description", q("dc", "description"))):
            for el in root.iter(tag):
                if (el.text or "").strip():
                    auto.append(f"{key}={el.text.strip()}")
        for key, tag in (("title", q("dc", "title")), ("subject", q("dc", "subject")),
                         ("keywords", q("cp", "keywords"))):
            for el in root.iter(tag):
                if TOOL_TRACE.search(el.text or ""):
                    manual.append(f"{key}={el.text.strip()}")
    if "docProps/app.xml" in pkg.parts:
        root = pkg.tree("docProps/app.xml")
        for key in ("Company", "Manager"):
            for el in root.iter(q("ep", key)):
                if (el.text or "").strip():
                    auto.append(f"{key}={el.text.strip()}")
        for el in root.iter(q("ep", "Application")):
            if TOOL_TRACE.search(el.text or ""):
                auto.append(f"Application={el.text.strip()}")
    if "docProps/custom.xml" in pkg.parts:
        auto.append("custom properties part")
    if any(n.startswith("docProps/thumbnail") for n in pkg.parts):
        auto.append("embedded thumbnail")
    add(F, "metadata", "author and property leftovers", "auto", len(auto), auto)
    add(F, "metadata", "tool name in metadata", "manual", len(manual), manual)


def scan_package_links(pkg: Package, F):
    broken, links = [], []
    bad = re.compile(r"localhost|127\.0\.0\.1|^file:|example\.(?:com|org|net)|\{\{|\[", re.I)
    for n in [x for x in pkg.parts if x.endswith(".rels")]:
        src = rels_source(n)
        for rel in pkg.tree(n).iter(q("rel", "Relationship")):
            target = rel.get("Target") or ""
            if rel.get("TargetMode") == "External":
                if bad.search(target):
                    links.append(f"{target[:70]}")
            elif resolve(src, target) not in pkg.parts:
                broken.append(f"{n} -> {target}")
    add(F, "format", "relationship pointing to a missing part", "manual", len(broken), broken)
    add(F, "residue", "suspicious hyperlink", "manual", len(links), links)


def scan_docx(pkg: Package, F, max_cites):
    comments = 0
    authors: set = set()
    if "word/comments.xml" in pkg.parts:
        cs = pkg.tree("word/comments.xml").findall(q("w", "comment"))
        comments = len(cs)
        authors = {c.get(q("w", "author")) or "?" for c in cs}
    add(F, "comments", "word comments", "auto", comments, [f"by {', '.join(sorted(authors))}"])

    text_parts = pkg.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$")
    ins = dele = fmt = 0
    names: set = set()
    hidden = []
    for n in text_parts:
        root = pkg.tree(n)
        for el in root.iter(q("w", "ins"), q("w", "moveTo")):
            ins += 1
            names.add(el.get(q("w", "author")) or "?")
        for el in root.iter(q("w", "del"), q("w", "moveFrom")):
            dele += 1
            names.add(el.get(q("w", "author")) or "?")
        for el in root.iter(*[q("w", t) for t in CHANGE_RECORDS]):
            fmt += 1
        for van in root.iter(q("w", "vanish")):
            if van.get(q("w", "val")) in ("0", "false", "off"):
                continue
            run = van.getparent().getparent()
            txt = "".join(t.text or "" for t in run.iter(q("w", "t")))
            if txt.strip():
                hidden.append(txt.strip()[:60])
    add(F, "tracked_changes", "insertions, deletions and formatting revisions", "auto", ins + dele + fmt,
        [f"{ins} inserted, {dele} deleted, {fmt} formatting; by {', '.join(sorted(names)) or '?'}"],
        "clean accepts every revision.")
    if "word/settings.xml" in pkg.parts and pkg.tree("word/settings.xml").find(q("w", "trackRevisions")) is not None:
        add(F, "tracked_changes", "track changes is switched on", "auto", 1)
    add(F, "hidden", "hidden text", "manual", len(hidden), hidden)

    doc = pkg.tree("word/document.xml")
    paras = []
    for i, p in enumerate(doc.iter(q("w", "p")), 1):
        paras.append((f"p{i}", para_text(p, q("w", "p"), q("w", "t"))))
    for n in text_parts:
        m = re.match(r"word/((?:header|footer)\d*|footnotes|endnotes)\.xml$", n)
        if m:
            for i, p in enumerate(pkg.tree(n).iter(q("w", "p")), 1):
                t = para_text(p, q("w", "p"), q("w", "t"))
                if t.strip():
                    paras.append((f"{m.group(1)} p{i}", t))
    stats = scan_text(F, paras, max_cites, "optional", "auto")
    stats["references"] = ref_stats([t for w, t in paras if re.match(r"p\d+$", w)])

    bidi_styles, default_bidi = set(), False
    if "word/styles.xml" in pkg.parts:
        st = pkg.tree("word/styles.xml")
        for s in st.iter(q("w", "style")):
            if s.find(f"{q('w', 'pPr')}/{q('w', 'bidi')}") is not None:
                bidi_styles.add(s.get(q("w", "styleId")))
        default_bidi = st.find(f"{q('w', 'docDefaults')}/{q('w', 'pPrDefault')}/{q('w', 'pPr')}/{q('w', 'bidi')}") is not None
    ltr_arabic = []
    for i, p in enumerate(doc.iter(q("w", "p")), 1):
        ppr = p.find(q("w", "pPr"))
        has = default_bidi
        if ppr is not None:
            b = ppr.find(q("w", "bidi"))
            if b is not None and b.get(q("w", "val")) not in ("0", "false", "off"):
                has = True
            ps = ppr.find(q("w", "pStyle"))
            if ps is not None and ps.get(q("w", "val")) in bidi_styles:
                has = True
        text = para_text(p, q("w", "p"), q("w", "t"))
        if not has and needs_rtl(text):
            ltr_arabic.append(f"p{i}: {text[:40]}")
    add(F, "format", "arabic paragraph without right-to-left direction", "manual", len(ltr_arabic), ltr_arabic)

    labels = []
    for i, p in enumerate(doc.iter(q("w", "p")), 1):
        first = next((r for r in p.findall(q("w", "r"))
                      if "".join(t.text or "" for t in r.iter(q("w", "t"))).strip()), None)
        if first is None:
            continue
        b = first.find(f"{q('w', 'rPr')}/{q('w', 'b')}")
        label = "".join(t.text or "" for t in first.iter(q("w", "t")))
        full = para_text(p, q("w", "p"), q("w", "t"))
        if (b is not None and b.get(q("w", "val")) not in ("0", "false", "off")
                and label.rstrip().endswith(":") and len(label) <= 45 and len(full) > len(label) + 5):
            labels.append(f"p{i}: {label.strip()}")
    if len(labels) >= 3:
        add(F, "ai_style", "bold label before a colon repeated down a list", "manual", len(labels), labels)

    body = doc.find(q("w", "body"))
    streaks, run = [], 0
    if body is not None:
        for i, child in enumerate(body, 1):
            empty = (child.tag == q("w", "p") and not para_text(child, q("w", "p"), q("w", "t")).strip()
                     and not any(True for _ in child.iter(q("w", "drawing"), q("w", "pict"), q("w", "br"),
                                                            q("w", "sectPr"), q("w", "object"), q("w", "fldChar"))))
            run = run + 1 if empty else 0
            if run == 3:
                streaks.append(f"body element {i}")
    add(F, "format", "three or more empty paragraphs in a row", "manual", len(streaks), streaks)

    fonts = set()
    for rf in doc.iter(q("w", "rFonts")):
        for att in ("ascii", "hAnsi", "cs"):
            if rf.get(q("w", att)):
                fonts.add(rf.get(q("w", att)))
    if len(fonts) > 3:
        add(F, "format", "more than three fonts in direct formatting", "manual", len(fonts), sorted(fonts))
    return stats


CHANGE_RECORDS = ("rPrChange", "pPrChange", "sectPrChange", "tblPrChange", "trPrChange",
                  "tcPrChange", "tblGridChange", "tblPrExChange", "numberingChange")


def scan_pptx(pkg: Package, F, max_cites):
    legacy = sum(len(pkg.tree(n).findall(q("p", "cm"))) for n in pkg.match(r"ppt/comments/comment\d+\.xml$"))
    modern = sum(1 for n in pkg.match(r"ppt/comments/modernComment_.*\.xml$")
                 for el in pkg.tree(n).iter() if isinstance(el.tag, str) and local(el) == "cm")
    add(F, "comments", "slide comments", "auto", legacy + modern)

    notes = []
    for n in pkg.match(r"ppt/notesSlides/notesSlide\d+\.xml$"):
        root = pkg.tree(n)
        txt = " ".join(para_text(p, q("a", "p"), q("a", "t")) for p in root.iter(q("a", "p"))).strip()
        # drop slide-number field text such as "3"
        if txt and not txt.isdigit():
            notes.append(f"{n.split('/')[-1]}: {txt[:50]}")
    add(F, "speaker_notes", "speaker notes with text", "auto", len(notes), notes)

    def slide_no(n):
        return int(re.search(r"(\d+)\.xml$", n).group(1))

    slides = sorted(pkg.match(r"ppt/slides/slide\d+\.xml$"), key=slide_no)
    paras, hidden, empty_slides, empty_ph, ltr, footers, slide_texts = [], [], [], [], [], [], []
    for n in slides:
        no = slide_no(n)
        root = pkg.tree(n)
        if root.get("show") == "0":
            hidden.append(f"slide {no}")
        has_content = False
        for sp in root.iter(q("p", "sp"), q("p", "pic"), q("p", "graphicFrame"), q("p", "grpSp")):
            if sp.tag != q("p", "sp"):
                has_content = True
                continue
            txt = "".join(t.text or "" for t in sp.iter(q("a", "t"))).strip()
            ph = sp.find(f"{q('p', 'nvSpPr')}/{q('p', 'nvPr')}/{q('p', 'ph')}")
            if txt and ph is not None and ph.get("type") in FOOTER_PH:
                footers.append(f"slide {no}: {txt[:50]}")
                continue
            if txt:
                has_content = True
            elif ph is not None and ph.get("type") in (None, "title", "ctrTitle", "subTitle", "body", "obj"):
                empty_ph.append(f"slide {no}")
            elif ph is None:
                has_content = True
        if not has_content:
            empty_slides.append(f"slide {no}")
        for i, p in enumerate(root.iter(q("a", "p")), 1):
            text = para_text(p, q("a", "p"), q("a", "t"))
            paras.append((f"slide {no} p{i}", text))
            slide_texts.append(text)
            ppr = p.find(q("a", "pPr"))
            if needs_rtl(text) and (ppr is None or ppr.get("rtl") not in ("1", "true")):
                ltr.append(f"slide {no}: {text[:40]}")
    add(F, "slide_footer", "text in slide footer or date placeholder", "auto", len(footers), footers)
    add(F, "hidden", "hidden slides", "manual", len(hidden), hidden)
    add(F, "format", "slide with no content", "manual", len(empty_slides), empty_slides)
    add(F, "format", "empty title or body placeholder", "manual", len(empty_ph), empty_ph)
    add(F, "format", "arabic paragraph without right-to-left direction", "manual", len(ltr), ltr)
    stats = scan_text(F, paras, max_cites, "manual", "auto")
    stats["references"] = ref_stats(slide_texts)
    return stats


FOOTER_PH = ("ftr", "dt")


def scan_xlsx(pkg: Package, F, max_cites):
    legacy = sum(len(list(pkg.tree(n).iter(q("x", "comment"))))
                 for n in pkg.match(r"xl/comments(?:/[^/]+|\d*)\.xml$"))
    threaded = sum(1 for n in pkg.match(r"xl/threadedComments/.*\.xml$")
                   for el in pkg.tree(n).iter() if isinstance(el.tag, str) and local(el) == "threadedComment")
    add(F, "comments", "cell notes and comments", "auto", legacy + threaded)

    wb = pkg.tree("xl/workbook.xml")
    rels = {r.get("Id"): r.get("Target") for r in pkg.tree("xl/_rels/workbook.xml.rels").iter(q("rel", "Relationship"))}
    sheet_names, hidden = {}, []
    for s in wb.iter(q("x", "sheet")):
        target = resolve("xl/workbook.xml", rels.get(s.get(q("r", "id")), ""))
        sheet_names[target] = s.get("name")
        if s.get("state") in ("hidden", "veryHidden"):
            hidden.append(f"{s.get('name')} ({s.get('state')})")
    add(F, "hidden", "hidden sheets", "manual", len(hidden), hidden)

    errors, uncomputed = [], []
    for n in pkg.match(r"xl/worksheets/sheet\d+\.xml$"):
        name = sheet_names.get(n, n)
        for c in pkg.tree(n).iter(q("x", "c")):
            v = c.find(q("x", "v"))
            if c.get("t") == "e":
                errors.append(f"{name}!{c.get('r')}: {v.text if v is not None else ''}")
            elif c.find(q("x", "f")) is not None and (v is None or not (v.text or "").strip()):
                uncomputed.append(f"{name}!{c.get('r')}")
    add(F, "format", "cell showing an error value", "manual", len(errors), errors)
    add(F, "format", "formula without a calculated value", "manual", len(uncomputed), uncomputed,
        "Open and re-save in Excel or LibreOffice so values are stored.")
    add(F, "format", "external workbook link", "manual", len(pkg.match(r"xl/externalLinks/.*\.xml$")),
        pkg.match(r"xl/externalLinks/.*\.xml$"))

    paras = []
    if "xl/sharedStrings.xml" in pkg.parts:
        for i, si in enumerate(pkg.tree("xl/sharedStrings.xml").iter(q("x", "si")), 1):
            paras.append((f"string {i}", "".join(t.text or "" for t in si.iter(q("x", "t")))))
    stats = scan_text(F, paras, max_cites, "manual")
    return stats


# ---------------------------------------------------------------- PDF

PDF_KEEP = ("/Link", "/Widget")


def scan_pdf(path: Path, F, max_cites):
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass
        add(F, "format", "pdf is encrypted", "manual", 1)
    annots, blank, paras = [], [], []
    for i, page in enumerate(reader.pages, 1):
        for a in page.get("/Annots") or []:
            sub = str(a.get_object().get("/Subtype"))
            if sub not in PDF_KEEP:
                annots.append(f"page {i}: {sub[1:]}")
        text = page.extract_text() or ""
        if not text.strip():
            blank.append(f"page {i}")
        for j, para in enumerate([t for t in re.split(r"\n\s*\n", text) if t.strip()], 1):
            paras.append((f"page {i} p{j}", para))
    add(F, "comments", "pdf annotations (notes, highlights, stamps)", "auto", len(annots), annots)
    meta = reader.metadata or {}
    found = [f"{k[1:]}={v}" for k, v in meta.items() if k in ("/Author", "/Creator", "/Producer", "/Subject", "/Keywords") and str(v).strip()]
    xmp = "/Metadata" in reader.trailer["/Root"]
    if xmp:
        found.append("XMP metadata stream")
    add(F, "metadata", "author and producer fields", "auto", len(found), found)
    if TOOL_TRACE.search(str(meta.get("/Title", ""))):
        add(F, "metadata", "tool name in metadata", "manual", 1, [f"Title={meta.get('/Title')}"])
    add(F, "format", "page without extractable text (blank or scanned)", "manual", len(blank), blank)
    stats = scan_text(F, paras, max_cites, "manual")
    stats["pages"] = len(reader.pages)
    return stats


# ---------------------------------------------------------------- scan driver


def scan_file(path: Path, max_cites: int = 3, traps=()) -> dict:
    TRAPS[:] = [t for t in traps if t.strip()]
    F: list = []
    ext = path.suffix.lower()
    if ext == ".pdf":
        kind, stats = "pdf", scan_pdf(path, F, max_cites)
    elif ext in (".docx", ".pptx", ".xlsx"):
        pkg = Package(path)
        kind = kind_of(pkg)
        scan_metadata(pkg, F)
        scan_package_links(pkg, F)
        fn = {"docx": scan_docx, "pptx": scan_pptx, "xlsx": scan_xlsx}[kind]
        stats = fn(pkg, F, max_cites)
    else:
        raise ValueError(f"unsupported file type: {ext}")
    if "_" in path.stem.replace(".clean", ""):
        add(F, "filename", "file name uses underscores", "manual", 1, [path.name],
            "Name the delivered file with spaces or hyphens unless the brief sets a naming rule.")
    order = ["trap", "filename", "comments", "tracked_changes", "speaker_notes", "slide_footer", "metadata", "hidden",
             "placeholder", "note", "residue", "ai_style", "citations", "format"]
    F.sort(key=lambda f: order.index(f["category"]) if f["category"] in order else len(order))
    return {"file": str(path), "kind": kind, "stats": stats, "findings": F}


def print_report(rep: dict):
    s = rep["stats"]
    print(f"{Path(rep['file']).name}  ({rep['kind']}, {s.get('words', 0):,} words, "
          f"{s.get('citations', 0)} citations = {s.get('per_1000_words', 0)} per 1000 words, "
          f"max {s.get('max_in_paragraph', 0)} in one paragraph)")
    r = s.get("references")
    if r:
        print(f"  reference list: {r['entries']} entries, {r['arabic']} Arabic, {r['other']} other")
    if not rep["findings"]:
        print("  no findings")
    for f in rep["findings"]:
        print(f"  [{f['fix']:<8}] {f['category']:<15} {f['rule']}: {f['count']}")
        for e in f["examples"]:
            print(f"             - {e}")
        if f["note"]:
            print(f"             ({f['note']})")
    auto = sum(1 for f in rep["findings"] if f["fix"] == "auto")
    optional = sum(1 for f in rep["findings"] if f["fix"] == "optional")
    manual = sum(1 for f in rep["findings"] if f["fix"] == "manual")
    print(f"  summary: {auto} auto-fixable, {optional} optional, {manual} need review")


# ---------------------------------------------------------------- clean (OOXML)


def drop_part(pkg: Package, name: str):
    pkg.removed.add(name)


def strip_rels_and_types(pkg: Package):
    for n in [x for x in pkg.parts if x.endswith(".rels") and x not in pkg.removed]:
        src = rels_source(n)
        root = pkg.tree(n)
        for rel in list(root.iter(q("rel", "Relationship"))):
            if rel.get("TargetMode") != "External" and resolve(src, rel.get("Target") or "") in pkg.removed:
                root.remove(rel)
                pkg.touch(n)
    ct = pkg.tree("[Content_Types].xml")
    for ov in list(ct.iter(q("ct", "Override"))):
        if (ov.get("PartName") or "").lstrip("/") in pkg.removed:
            ct.remove(ov)
            pkg.touch("[Content_Types].xml")
    for n in list(pkg.removed):
        if n.endswith(".rels"):
            continue
        r = posixpath.join(posixpath.dirname(n), "_rels", posixpath.basename(n) + ".rels")
        if r in pkg.parts:
            pkg.removed.add(r)


def scrub_core(pkg: Package, author: str):
    if "docProps/core.xml" in pkg.parts:
        root = pkg.tree("docProps/core.xml")
        for tag in (q("dc", "creator"), q("cp", "lastModifiedBy")):
            for el in root.iter(tag):
                el.text = author
        for el in list(root.iter(q("dc", "description"))):
            root.remove(el)
        pkg.touch("docProps/core.xml")
    if "docProps/app.xml" in pkg.parts:
        root = pkg.tree("docProps/app.xml")
        for key in ("Company", "Manager"):
            for el in root.iter(q("ep", key)):
                el.text = ""
        for el in root.iter(q("ep", "Application")):
            if TOOL_TRACE.search(el.text or ""):
                el.text = ""
        pkg.touch("docProps/app.xml")
    for n in list(pkg.parts):
        if n == "docProps/custom.xml" or n.startswith("docProps/thumbnail"):
            drop_part(pkg, n)


def remove_el(el):
    el.getparent().remove(el)


def unwrap(el):
    parent = el.getparent()
    idx = parent.index(el)
    for child in list(el):
        parent.insert(idx, child)
        idx += 1
    parent.remove(el)


def clean_docx_xml(root, stats):
    for tag in ("commentRangeStart", "commentRangeEnd"):
        for el in list(root.iter(q("w", tag))):
            remove_el(el)
    for ref in list(root.iter(q("w", "commentReference"))):
        run = ref.getparent()
        if run.tag == q("w", "r"):
            remove_el(run)
        else:
            remove_el(ref)
    for tag in ("moveFromRangeStart", "moveFromRangeEnd", "moveToRangeStart", "moveToRangeEnd"):
        for el in list(root.iter(q("w", tag))):
            remove_el(el)
    for el in list(root.iter(q("w", "del"), q("w", "moveFrom"))):
        if el.getparent() is None:
            continue
        stats["revisions"] += 1
        parent = el.getparent()
        if len(el) == 0:
            if parent.tag == q("w", "trPr"):
                row = parent.getparent()
                if row is not None and row.getparent() is not None:
                    remove_el(row)
                    continue
            remove_el(el)
        else:
            remove_el(el)
    for el in list(root.iter(q("w", "ins"), q("w", "moveTo"))):
        if el.getparent() is None:
            continue
        stats["revisions"] += 1
        if len(el) == 0:
            remove_el(el)
        else:
            unwrap(el)
    for tag in CHANGE_RECORDS:
        for el in list(root.iter(q("w", tag))):
            stats["revisions"] += 1
            remove_el(el)


def thin_paragraphs(root, stats):
    for p in root.iter(q("w", "p")):
        seen: set = set()
        for t in p.iter(q("w", "t")):
            if not t.text:
                continue
            text, pieces, last = t.text, [], 0
            for rx in (CITE_PAREN, CITE_NUM):
                for m in rx.finditer(t.text):
                    key = norm_key(m.group(0))
                    if key in seen:
                        pieces.append((m.start(), m.end()))
                    else:
                        seen.add(key)
            if not pieces:
                continue
            out = []
            for s, e in sorted(pieces):
                if s < last:
                    continue
                if s > last and text[s - 1] == " ":
                    s -= 1
                out.append(text[last:s])
                last = e
                stats["thinned"] += 1
            out.append(text[last:])
            t.text = "".join(out)
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def blank_fields(root, ptag, ttag, stats):
    """Remove fill-in fields inside single text nodes, then trailing separators of the paragraph."""
    for p in root.iter(ptag):
        ts = [t for t in p.iter(ttag) if next(t.iterancestors(ptag)) is p and t.text]
        hit = False
        for t in ts:
            new, n = FIELD_STRIP.subn("", t.text)
            if n:
                t.text, hit = new, True
                stats["fields"] += n
                if ttag == q("w", "t"):
                    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        if hit:
            for t in reversed(ts):
                if t.text.strip():
                    t.text = SEP_TAIL.sub("", t.text)
                    break
                t.text = ""


def strip_citations(root, stats):
    """docx: drop parenthetical and numeric citations from body text. The reference list and
    paragraphs that open with a numeric label ([1] ...) are left alone."""
    ps = list(root.iter(q("w", "p")))
    texts = [para_text(p, q("w", "p"), q("w", "t")) for p in ps]
    stop = ref_start(texts)
    for i, p in enumerate(ps):
        if stop is not None and i >= stop:
            break
        first = True
        for t in p.iter(q("w", "t")):
            if not t.text or next(t.iterancestors(q("w", "p"))) is not p:
                continue
            text = t.text
            spans = sorted((m.start(), m.end()) for rx in (CITE_PAREN, CITE_NUM) for m in rx.finditer(text))
            if first and text.strip():
                lead = len(text) - len(text.lstrip())
                spans = [sp for sp in spans if not (sp[0] == lead and text[lead] == "[")]
                first = False
            out, last = [], 0
            for a, b in spans:
                if a < last:
                    continue
                while a > last and text[a - 1] == " ":
                    a -= 1
                out.append(text[last:a])
                last = b
                stats["citations_removed"] += 1
            if out:
                out.append(text[last:])
                t.text = "".join(out)
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def clean_package(pkg: Package, author: str, thin: bool, fields: bool = True, strip: bool = False) -> dict:
    kind = kind_of(pkg)
    stats = {"revisions": 0, "thinned": 0, "fields": 0, "citations_removed": 0, "parts_removed": 0}
    if kind == "docx":
        for n in pkg.match(r"word/(comments\w*|people)\.xml$"):
            drop_part(pkg, n)
        for n in pkg.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$"):
            clean_docx_xml(pkg.tree(n), stats)
            if thin and n == "word/document.xml":
                thin_paragraphs(pkg.tree(n), stats)
            if strip and n == "word/document.xml":
                strip_citations(pkg.tree(n), stats)
            if fields:
                blank_fields(pkg.tree(n), q("w", "p"), q("w", "t"), stats)
            pkg.touch(n)
        if "word/settings.xml" in pkg.parts:
            root = pkg.tree("word/settings.xml")
            for el in list(root.iter(q("w", "trackRevisions"))):
                remove_el(el)
            pkg.touch("word/settings.xml")
    elif kind == "pptx":
        for pat in (r"ppt/notesSlides/.*", r"ppt/comments/.*", r"ppt/commentAuthors\.xml$", r"ppt/authors\.xml$"):
            for n in pkg.match(pat):
                drop_part(pkg, n)
        for n in pkg.match(r"ppt/slides/slide\d+\.xml$"):
            root = pkg.tree(n)
            for sp in list(root.iter(q("p", "sp"))):
                ph = sp.find(f"{q('p', 'nvSpPr')}/{q('p', 'nvPr')}/{q('p', 'ph')}")
                if ph is not None and ph.get("type") in FOOTER_PH:
                    remove_el(sp)
                    stats["footers"] = stats.get("footers", 0) + 1
            if fields:
                blank_fields(root, q("a", "p"), q("a", "t"), stats)
            pkg.touch(n)
    else:
        for pat in (r"xl/comments(?:/[^/]+|\d*)\.xml$", r"xl/threadedComments/.*", r"xl/persons/.*"):
            for n in pkg.match(pat):
                drop_part(pkg, n)
        for rn in pkg.match(r"xl/worksheets/_rels/sheet\d+\.xml\.rels$"):
            root = pkg.tree(rn)
            rels = list(root.iter(q("rel", "Relationship")))
            if any((r.get("Type") or "").endswith("/comments") for r in rels):
                src = rels_source(rn)
                for r in rels:
                    if (r.get("Type") or "").endswith("/vmlDrawing"):
                        drop_part(pkg, resolve(src, r.get("Target")))
                sheet = pkg.tree(src)
                for el in list(sheet.iter(q("x", "legacyDrawing"))):
                    remove_el(el)
                pkg.touch(src)
    scrub_core(pkg, author)
    stats["parts_removed"] = len(pkg.removed)
    strip_rels_and_types(pkg)
    return stats


# ---------------------------------------------------------------- clean (PDF)


def clean_pdf(path: Path, out: Path, author: str) -> dict:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, NameObject

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt("")
    writer = PdfWriter(clone_from=reader)
    removed = 0
    for page in writer.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        keep = [a for a in annots if str(a.get_object().get("/Subtype")) in PDF_KEEP]
        removed += len(annots) - len(keep)
        if keep:
            page[NameObject("/Annots")] = ArrayObject(keep)
        else:
            del page["/Annots"]
    root = writer._root_object
    if "/Metadata" in root:
        del root["/Metadata"]
    writer.add_metadata({"/Author": author, "/Creator": "", "/Producer": "", "/Subject": "", "/Keywords": ""})
    with open(out, "wb") as fh:
        writer.write(fh)
    return {"annotations_removed": removed}


# ---------------------------------------------------------------- CLI


def clean_file(path: Path, out: Path | None, author: str, thin: bool, max_cites: int,
               fields: bool = True, strip: bool = False, traps=()) -> int:
    out = out or path.with_name(f"{path.stem}.clean{path.suffix}")
    if out.resolve() == path.resolve():
        sys.exit("refusing to overwrite the original file")
    if path.suffix.lower() == ".pdf":
        stats = clean_pdf(path, out, author)
    else:
        pkg = Package(path)
        stats = clean_package(pkg, author, thin, fields, strip)
        pkg.save(out)
    print(f"wrote {out}  {stats}")
    rep = scan_file(out, max_cites, traps)
    print("after cleaning:")
    print_report(rep)
    return 1 if any(f["fix"] == "auto" for f in rep["findings"]) else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="report problems, change nothing")
    sc.add_argument("files", nargs="+", type=Path)
    sc.add_argument("--json", action="store_true")
    sc.add_argument("--max-per-paragraph", type=int, default=3)
    sc.add_argument("--find", action="append", default=[], metavar="WORD",
                    help="report this word or phrase (a trap from the brief); repeatable")
    cl = sub.add_parser("clean", help="write a cleaned copy and re-scan it")
    cl.add_argument("files", nargs="+", type=Path)
    cl.add_argument("-o", "--output", type=Path)
    cl.add_argument("--author", default="", help="value for author and last-modified-by (default: empty)")
    cl.add_argument("--thin-citations", action="store_true", help="docx only: drop repeated identical citations inside a paragraph")
    cl.add_argument("--strip-citations", action="store_true",
                    help="docx only: remove parenthetical and numeric in-text citations; the reference list stays")
    cl.add_argument("--keep-fields", action="store_true",
                    help="keep fill-in fields such as [Full name] (default: blank them, keep the label)")
    cl.add_argument("--find", action="append", default=[], metavar="WORD")
    cl.add_argument("--max-per-paragraph", type=int, default=3)
    a = ap.parse_args(argv)

    if a.cmd == "scan":
        reps = [scan_file(f, a.max_per_paragraph, a.find) for f in a.files]
        if a.json:
            print(json.dumps(reps, ensure_ascii=False, indent=2))
        else:
            for r in reps:
                print_report(r)
        return 1 if any(r["findings"] for r in reps) else 0

    if a.output and len(a.files) > 1:
        sys.exit("-o works with a single file")
    code = 0
    for f in a.files:
        code |= clean_file(f, a.output, a.author, a.thin_citations, a.max_per_paragraph,
                           not a.keep_fields, a.strip_citations, a.find)
    return code


if __name__ == "__main__":
    sys.exit(main())
