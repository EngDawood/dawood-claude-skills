#!/usr/bin/env python3
"""
Claude Doc markdown export -> house-style RTL .docx.

Usage: python3 md_to_docx_rtl.py INPUT OUTPUT.docx [options]
INPUT: a .md file, or the JSON file Claude Docs `export` saves ({"data": {"bytes_b64": ...}}).

Front matter: everything before the first `##` heading is the cover page: each line its own
centered paragraph (lines above the `#` title are the institution block, bold at the top; the
title sits lower and large; a table there becomes centered "label: value" lines, never a Word
table; the last line, the date or year, is pushed down). It ends with a page break; a table of contents page follows (a live Word TOC field that Word fills
on open), then the body starts in a new section whose page numbers start at 1.
Equations: `$$...$$`, `\\[...\\]`, a line that is only `$...$`, and a bare formula line such as
`Z = 3.3X_1 + 1.2X_2` become native Word equations (OMML), not plain text.
"""
import argparse, base64, json, os, re, sys, unicodedata
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# Arabic Unicode blocks, built from code points so no invisible characters live in this file.
_AR_RANGES = [(0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)]
AR_RE = re.compile('[' + ''.join(re.escape(chr(a)) + '-' + re.escape(chr(b)) for a, b in _AR_RANGES) + ']')
LATIN_RE = re.compile(r'[A-Za-z]')
RLM = chr(0x200F)
BYLINE_RE = re.compile(r'^\s*([A-Z][a-z]{2} \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})?\s*(·\s*)?(@\S+\s*)*$')
INLINE_RE = re.compile(r'(\*\*[^*]+\*\*|__[^_]+__|\*[^*\s][^*]*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))')
CENTER_H_RE = re.compile(r'^(المحور|الفصل|مراجع|المراجع|قائمة|ملخص|Chapter|References|Abstract)')
CAPTION_RE = re.compile(r'^(جدول|شكل|الجدول|الشكل|Table|Figure)\s*\(?\s*\d')
# Multi-level heading number at the start of a heading: 2.1, 5.3.2 ...
HNUM_RE = re.compile(r'^(\d+(?:\.\d+)+)(?=[\s.):-])')
# Start-aligned = no jc at all. In a right-to-left paragraph Word reads jc="right" as the line's
# end, i.e. the LEFT edge; leaving jc unset aligns to the start, which is the right edge.
START = None
SOURCE_RE = re.compile(r'^(المصدر|Source)\s*:')
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def load_markdown(path):
    raw = open(path, encoding='utf-8').read()
    s = raw.lstrip()
    if s.startswith('{'):
        try:
            d = json.loads(s)
            data = d.get('data', d)
            if 'bytes_b64' in data:
                return base64.b64decode(data['bytes_b64']).decode('utf-8')
            if 'markdown' in data:
                return data['markdown']
        except Exception:
            pass
    return raw


def is_rtl_text(t, default_rtl):
    ar = len(AR_RE.findall(t))
    la = len(LATIN_RE.findall(t))
    if ar == 0 and la == 0:
        return default_rtl
    return ar >= la * 0.3 if ar else False


def set_par_dir(p, rtl):
    pPr = p._p.get_or_add_pPr()
    for el in pPr.findall(qn('w:bidi')):
        pPr.remove(el)
    if rtl:
        b = OxmlElement('w:bidi'); b.set(qn('w:val'), '1')
        pPr.insert(1 if pPr.find(qn('w:pStyle')) is not None else 0, b)


def style_run(run, cfg, rtl, size=None, bold=None, italic=None, mono=False):
    rPr = run._r.get_or_add_rPr()
    fonts = rPr.find(qn('w:rFonts'))
    if fonts is None:
        fonts = OxmlElement('w:rFonts'); rPr.insert(0, fonts)
    en = 'Consolas' if mono else cfg.en_font
    fonts.set(qn('w:ascii'), en); fonts.set(qn('w:hAnsi'), en)
    fonts.set(qn('w:cs'), cfg.ar_font); fonts.set(qn('w:eastAsia'), en)
    sz = size or cfg.size
    run.font.size = Pt(sz)
    szCs = rPr.find(qn('w:szCs'))
    if szCs is None:
        szCs = OxmlElement('w:szCs'); rPr.append(szCs)
    szCs.set(qn('w:val'), str(int(sz * 2)))
    if bold is not None:
        run.bold = bold
        if bold:
            rPr.append(OxmlElement('w:bCs'))
    if italic is not None:
        run.italic = italic
        if italic:
            rPr.append(OxmlElement('w:iCs'))
    if rtl and AR_RE.search(run.text or ''):
        r = OxmlElement('w:rtl'); r.set(qn('w:val'), '1'); rPr.append(r)
    run.font.color.rgb = RGBColor.from_string(cfg.color)


def add_inline(p, text, cfg, rtl, size=None, bold=False):
    for part in INLINE_RE.split(text):
        if not part:
            continue
        b, i, mono, t = bold, False, False, part
        if (part.startswith('**') and part.endswith('**')) or (part.startswith('__') and part.endswith('__')):
            b, t = True, part[2:-2]
        elif part.startswith('*') and part.endswith('*') and len(part) > 2:
            i, t = True, part[1:-1]
        elif part.startswith('`') and part.endswith('`'):
            mono, t = True, part[1:-1]
        elif part.startswith('[') and '](' in part:
            m = re.match(r'\[([^\]]+)\]\(([^)]+)\)', part)
            t = m.group(1) if m else part
        t = t.replace('\\*', '*').replace('\\_', '_').replace('\\[', '[').replace('\\]', ']').replace('\\#', '#').replace('\\-', '-').replace('\\.', '.')
        run = p.add_run(t)
        style_run(run, cfg, rtl, size=size, bold=b, italic=i, mono=mono)


def para_spacing(p, cfg, before=0, after=8, line=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before); pf.space_after = Pt(after)
    pf.line_spacing = line if line is not None else cfg.line


def cell_shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), hex_fill)
    tcPr.append(shd)


def table_borders(table):
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '8'); e.set(qn('w:space'), '0'); e.set(qn('w:color'), 'auto')
        borders.append(e)
    table._tbl.tblPr.append(borders)


def table_rtl(table):
    bv = OxmlElement('w:bidiVisual'); bv.set(qn('w:val'), '1')
    table._tbl.tblPr.insert(0, bv)


def no_split(row, header=False):
    trPr = row._tr.get_or_add_trPr()
    if header:
        h = OxmlElement('w:tblHeader'); h.set(qn('w:val'), 'true'); trPr.append(h)
    cs = OxmlElement('w:cantSplit'); cs.set(qn('w:val'), 'true'); trPr.append(cs)


def add_page_number(section, cfg):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, txt in (('begin', None), (None, 'PAGE'), ('end', None)):
        if kind:
            fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'), kind); run._r.append(fc)
        else:
            it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = txt; run._r.append(it)
    style_run(run, cfg, False, size=11)


def sect_bidi(sectPr):
    """w:bidi in schema order (before textDirection/rtlGutter/docGrid), so Word does not repair the file."""
    if sectPr.find(qn('w:bidi')) is not None:
        return
    b = OxmlElement('w:bidi')
    for tag in ('w:textDirection', 'w:rtlGutter', 'w:docGrid', 'w:printerSettings'):
        el = sectPr.find(qn(tag))
        if el is not None:
            el.addprevious(b); return
    sectPr.append(b)


def restart_page_numbers(sectPr, start=1):
    pg = sectPr.find(qn('w:pgNumType'))
    if pg is None:
        pg = OxmlElement('w:pgNumType')
        anchor = sectPr.find(qn('w:pgMar'))
        if anchor is not None:
            anchor.addnext(pg)
        else:
            sectPr.append(pg)
    pg.set(qn('w:start'), str(start))


def style_fonts(style, cfg):
    st_rPr = style.element.get_or_add_rPr()
    f = st_rPr.find(qn('w:rFonts'))
    if f is None:
        f = OxmlElement('w:rFonts'); st_rPr.insert(0, f)
    for a in ('ascii', 'hAnsi', 'eastAsia'):
        f.set(qn(f'w:{a}'), cfg.en_font)
    f.set(qn('w:cs'), cfg.ar_font)
    for a in ('w:asciiTheme', 'w:hAnsiTheme', 'w:eastAsiaTheme', 'w:cstheme'):
        if f.get(qn(a)) is not None:
            del f.attrib[qn(a)]


def setup_document(cfg):
    doc = Document()
    sec = doc.sections[0]
    if cfg.paper == 'a4':
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    else:
        sec.page_width, sec.page_height = Cm(21.59), Cm(27.94)
    sec.orientation = WD_ORIENT.PORTRAIT
    for side in ('left_margin', 'right_margin', 'top_margin', 'bottom_margin'):
        setattr(sec, side, Cm(cfg.margins))
    if cfg.doc_rtl:
        sect_bidi(sec._sectPr)
    st = doc.styles['Normal']
    st.font.name = cfg.en_font; st.font.size = Pt(cfg.size)
    rPr = st.element.get_or_add_rPr()
    rf = rPr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rPr.insert(0, rf)
    for a in ('ascii', 'hAnsi', 'eastAsia'):
        rf.set(qn(f'w:{a}'), cfg.en_font)
    rf.set(qn('w:cs'), cfg.ar_font)
    lang = OxmlElement('w:lang'); lang.set(qn('w:val'), 'en-US'); lang.set(qn('w:bidi'), 'ar-SA'); rPr.append(lang)
    szcs = OxmlElement('w:szCs'); szcs.set(qn('w:val'), str(int(cfg.size * 2))); rPr.append(szcs)
    for lvl, sz in ((1, cfg.size + 6), (2, cfg.size + 2), (3, cfg.size), (4, cfg.size)):
        hs = doc.styles[f'Heading {lvl}']
        hs.font.size = Pt(sz); hs.font.bold = True; hs.font.color.rgb = RGBColor.from_string(cfg.color)
        hs.font.name = cfg.en_font
        style_fonts(hs, cfg)
    # Document title uses the built-in Title style: it has no outline level,
    # so it never lands in Word's table of contents (Heading 1 would).
    ts = doc.styles['Title']
    ts.font.size = Pt(cfg.size + 6); ts.font.bold = True; ts.font.color.rgb = RGBColor.from_string(cfg.color)
    ts.font.name = cfg.en_font
    tp = ts.element.get_or_add_pPr()
    for tag in ('w:pBdr', 'w:contextualSpacing'):
        el = tp.find(qn(tag))
        if el is not None:
            tp.remove(el)
    style_fonts(ts, cfg)
    return doc


def number_rtl(text):
    """'2.1 title' -> '2<RLM>.<RLM>1 title'. In a right-to-left heading the plain digits run left to
    right and show as 2.1 read from the left; RLM around each dot makes the main number sit on the
    right (Arabic reading order), the way a hand-formatted Arabic thesis shows it."""
    return HNUM_RE.sub(lambda m: (RLM + '.' + RLM).join(m.group(1).split('.')), text)


def add_heading(doc, text, level, cfg):
    rtl = is_rtl_text(text, cfg.doc_rtl)
    if rtl:
        text = number_rtl(text)
    # '#' is the document title: Title style, kept out of the table of contents
    p = doc.add_paragraph(style='Title' if level == 1 else f'Heading {min(level, 4)}')
    set_par_dir(p, rtl)
    sizes = {1: cfg.size + 6, 2: cfg.size + 2, 3: cfg.size, 4: cfg.size}
    add_inline(p, text, cfg, rtl, size=sizes[min(level, 4)], bold=True)
    centered = level == 1 or bool(CENTER_H_RE.match(text))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else START
    para_spacing(p, cfg, before=10 if level <= 2 else 6, after=6)
    p.paragraph_format.keep_with_next = True


def add_paragraph(doc, text, cfg):
    rtl = is_rtl_text(text, cfg.doc_rtl)
    p = doc.add_paragraph()
    set_par_dir(p, rtl)
    if CAPTION_RE.match(text):
        add_inline(p, text, cfg, rtl, bold=True, size=cfg.size)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para_spacing(p, cfg, before=6, after=4)
        p.paragraph_format.keep_with_next = True
        return
    if SOURCE_RE.match(text):
        add_inline(p, text, cfg, rtl, size=cfg.size - 2)
        p.alignment = START
        para_spacing(p, cfg, before=4, after=10)
        return
    add_inline(p, text, cfg, rtl, size=cfg.size)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para_spacing(p, cfg, before=10 if cfg.after_table else 0)


def add_reference(doc, text, cfg):
    rtl = is_rtl_text(text, cfg.doc_rtl)
    p = doc.add_paragraph()
    set_par_dir(p, rtl)
    add_inline(p, text, cfg, rtl, size=cfg.size)
    p.alignment = START
    pf = p.paragraph_format
    pf.left_indent = Cm(0.635); pf.first_line_indent = Cm(-0.635)
    para_spacing(p, cfg, after=6)


def new_num_restart(doc):
    """Fresh w:num for 'List Number' so each numbered list restarts at 1."""
    numbering = doc.part.numbering_part.element
    sid = doc.styles['List Number'].element.find('.//' + qn('w:numId')).get(qn('w:val'))
    absid = None
    for num in numbering.findall(qn('w:num')):
        if num.get(qn('w:numId')) == sid:
            absid = num.find(qn('w:abstractNumId')).get(qn('w:val'))
    new_id = max(int(n.get(qn('w:numId'))) for n in numbering.findall(qn('w:num'))) + 1
    num = OxmlElement('w:num'); num.set(qn('w:numId'), str(new_id))
    a = OxmlElement('w:abstractNumId'); a.set(qn('w:val'), absid); num.append(a)
    ov = OxmlElement('w:lvlOverride'); ov.set(qn('w:ilvl'), '0')
    so = OxmlElement('w:startOverride'); so.set(qn('w:val'), '1'); ov.append(so); num.append(ov)
    numbering.append(num)
    return new_id


def add_list_item(doc, text, ordered, level, cfg, number):
    rtl = is_rtl_text(text, cfg.doc_rtl)
    style = 'List Number' if ordered else 'List Bullet'
    if level > 0:
        style += f' {min(level + 1, 3)}'
    try:
        p = doc.add_paragraph(style=style)
        p.paragraph_format.left_indent = None
    except KeyError:
        p = doc.add_paragraph()
        text = (f'{number}. ' if ordered else '• ') + text
    if ordered and level == 0 and p.style.name.startswith('List Number'):
        if number == 1 or getattr(cfg, '_cur_num', None) is None:
            cfg._cur_num = new_num_restart(doc)
        pPr = p._p.get_or_add_pPr()
        numPr = OxmlElement('w:numPr')
        il = OxmlElement('w:ilvl'); il.set(qn('w:val'), '0'); numPr.append(il)
        ni = OxmlElement('w:numId'); ni.set(qn('w:val'), str(cfg._cur_num)); numPr.append(ni)
        pPr.insert(1, numPr)
    set_par_dir(p, rtl)
    add_inline(p, text, cfg, rtl, size=cfg.size)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para_spacing(p, cfg, after=4, line=max(cfg.line, 1.16))


# ---------------- equations (native Word OMML) ----------------
MATH_CMD = {'approx': '≈', 'times': '×', 'div': '÷', 'cdot': '·', 'le': '≤', 'leq': '≤', 'ge': '≥',
            'geq': '≥', 'neq': '≠', 'ne': '≠', 'pm': '±', 'mp': '∓', 'minus': '−', 'sum': '∑',
            'infty': '∞', 'to': '→', 'rightarrow': '→', 'Rightarrow': '⇒', 'alpha': 'α', 'beta': 'β',
            'gamma': 'γ', 'delta': 'δ', 'Delta': 'Δ', 'sigma': 'σ', 'Sigma': 'Σ', 'mu': 'μ', 'pi': 'π',
            'theta': 'θ', 'lambda': 'λ', 'rho': 'ρ', 'epsilon': 'ε', '%': '%', '$': '$', '{': '{', '}': '}'}
MATH_SKIP = {'left', 'right', 'displaystyle', 'quad', 'qquad', ',', ';', ':', '!', ' ', 'big', 'Big', 'mathrm'}
# A formula line written without $ delimiters: a symbol, '=', then numbers, symbols and operators only.
BARE_EQ_RE = re.compile(r"^[A-Za-z][A-Za-z0-9']*(?:_\{?[A-Za-z0-9]+\}?)?\s*(?:\([^)]*\))?\s*="
                        r"[\sA-Za-z0-9.,+\-−=()\[\]_{}^\\'×÷*/≈<>≤≥·%]+$")
MD_UNESCAPE_RE = re.compile(r'\\([_*#\-.^~`|()!+=<>])')


def _x(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class Omml:
    def __init__(self, cfg):
        sz = str(int(cfg.math_size * 2))
        self.rpr = (f'<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/>'
                    f'<w:color w:val="{cfg.color}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>')
        self.text_rpr = (f'<w:rPr><w:rFonts w:ascii="{cfg.en_font}" w:hAnsi="{cfg.en_font}" w:cs="{cfg.ar_font}"/>'
                         f'<w:color w:val="{cfg.color}"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/><w:rtl/></w:rPr>')

    def run(self, t, normal=False):
        if normal:
            return f'<m:r><m:rPr><m:nor/></m:rPr>{self.text_rpr}<m:t xml:space="preserve">{_x(t)}</m:t></m:r>'
        return f'<m:r>{self.rpr}<m:t>{_x(t)}</m:t></m:r>'

    def parse(self, s):
        nodes, i, n = [], 0, len(s)

        def group():
            nonlocal i
            while i < n and s[i] == ' ':
                i += 1
            if i < n and s[i] == '{':
                d, j = 1, i + 1
                while j < n and d:
                    d += {'{': 1, '}': -1}.get(s[j], 0); j += 1
                inner = s[i + 1:j - 1]; i = j
                return self.parse(inner)
            if i < n and s[i] == '\\':
                m = re.match(r'\\([A-Za-z]+|.)', s[i:]); i += len(m.group(0))
                return self.run(MATH_CMD.get(m.group(1), m.group(1)))
            c = s[i] if i < n else ''; i += 1
            return self.run(c)

        while i < n:
            c = s[i]
            if c.isspace():
                i += 1; continue
            if c == '\\':
                m = re.match(r'\\([A-Za-z]+|.)', s[i:]); name = m.group(1); i += len(m.group(0))
                if name in MATH_SKIP:
                    continue
                if name == 'frac':
                    a, b = group(), group()
                    nodes.append({'xml': f'<m:f><m:num>{a}</m:num><m:den>{b}</m:den></m:f>'})
                elif name == 'sqrt':
                    a = group()
                    nodes.append({'xml': f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{a}</m:e></m:rad>'})
                elif name in ('text', 'textrm', 'mbox', 'operatorname'):
                    j = s.find('}', i)
                    txt = s[i + 1:j] if i < n and s[i] == '{' and j > 0 else ''
                    i = j + 1 if j > 0 else n
                    nodes.append({'xml': self.run(txt, normal=bool(AR_RE.search(txt)))})
                else:
                    nodes.append({'xml': self.run(MATH_CMD.get(name, name))})
                continue
            if c in '_^':
                i += 1
                base = nodes.pop() if nodes else {'xml': self.run('')}
                g = group()
                if c == '^' and 'sub' in base:
                    nodes.append({'xml': f'<m:sSubSup><m:e>{base["base"]}</m:e><m:sub>{base["sub"]}</m:sub><m:sup>{g}</m:sup></m:sSubSup>'})
                elif c == '_':
                    nodes.append({'xml': f'<m:sSub><m:e>{base["xml"]}</m:e><m:sub>{g}</m:sub></m:sSub>',
                                  'base': base['xml'], 'sub': g})
                else:
                    nodes.append({'xml': f'<m:sSup><m:e>{base["xml"]}</m:e><m:sup>{g}</m:sup></m:sSup>'})
                continue
            if c == '{':
                nodes.append({'xml': group()}); continue
            if c.isalpha() and c.isascii() or c in 'αβγδΔσΣμπθλρε':
                j = i + 1
                while j < n and (s[j].isascii() and s[j].isalpha()):
                    j += 1
                while j < n and s[j] == "'":
                    j += 1
                nodes.append({'xml': self.run(s[i:j].replace("'", '′'))}); i = j; continue
            j = i
            while j < n and not (s[j].isascii() and s[j].isalpha()) and s[j] not in '\\_^{ ':
                j += 1
            if j == i:
                j = i + 1
            nodes.append({'xml': self.run(s[i:j].replace('-', '−').replace('*', '×'))}); i = j
        return ''.join(nd['xml'] for nd in nodes)


def math_source(s):
    """Undo markdown escaping and fold math-italic letters (𝑍 -> Z) so the parser sees plain LaTeX."""
    s = unicodedata.normalize('NFKC', s).replace('′', "'")
    return MD_UNESCAPE_RE.sub(r'\1', s).strip()


def is_bare_equation(s):
    if AR_RE.search(s):
        return False
    t = math_source(s)
    return bool(BARE_EQ_RE.match(t)) and bool(re.search(r'[\d_\\^]', t.split('=', 1)[1]))


def add_equation(doc, src, cfg):
    p = doc.add_paragraph()
    set_par_dir(p, False)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para_spacing(p, cfg, before=4, after=4, line=1.0)
    p.paragraph_format.keep_with_next = True
    xml = Omml(cfg).parse(math_source(src))
    p._p.append(parse_xml(f'<m:oMathPara xmlns:m="{M_NS}" xmlns:w="{W_NS}"><m:oMath>{xml}</m:oMath></m:oMathPara>'))
    cfg.eq_count += 1


# ---------------- cover page and table of contents ----------------
def toc_styles(doc, cfg):
    """TOC 1-4 paragraph styles: right-to-left, house font, page number at the far end after dot leaders."""
    usable = (21.0 if cfg.paper == 'a4' else 21.59) - 2 * cfg.margins
    pos = str(int(usable / 2.54 * 1440))
    for lvl in (1, 2, 3, 4):
        name = f'toc {lvl}'
        try:
            st = doc.styles[name]
        except KeyError:
            st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            st.element.set(qn('w:styleId'), f'TOC{lvl}')
        st.base_style = doc.styles['Normal']
        st.font.size = Pt(cfg.size - 2); st.font.bold = (lvl <= 2)
        style_fonts(st, cfg)
        pPr = st.element.get_or_add_pPr()
        if cfg.doc_rtl and pPr.find(qn('w:bidi')) is None:
            pPr.append(OxmlElement('w:bidi'))
        tabs = OxmlElement('w:tabs'); tab = OxmlElement('w:tab')
        tab.set(qn('w:val'), 'right'); tab.set(qn('w:leader'), 'dot'); tab.set(qn('w:pos'), pos)
        tabs.append(tab); pPr.append(tabs)
        sp = OxmlElement('w:spacing'); sp.set(qn('w:before'), '0'); sp.set(qn('w:after'), '60')
        pPr.append(sp)
        ind = OxmlElement('w:ind'); ind.set(qn('w:start'), str(max(lvl - 2, 0) * 400)); pPr.append(ind)


def add_toc(doc, cfg):
    p = doc.add_paragraph()
    set_par_dir(p, cfg.doc_rtl)
    add_inline(p, cfg.toc_title, cfg, cfg.doc_rtl, size=cfg.size + 2, bold=True)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para_spacing(p, cfg, before=0, after=12)
    toc_styles(doc, cfg)
    p = doc.add_paragraph()
    set_par_dir(p, cfg.doc_rtl)

    def fld(kind):
        r = p.add_run(); fc = OxmlElement('w:fldChar'); fc.set(qn('w:fldCharType'), kind)
        if kind == 'begin':
            fc.set(qn('w:dirty'), 'true')
        r._r.append(fc)
    fld('begin')
    r = p.add_run(); it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve')
    it.text = f' TOC \\o "{cfg.toc_levels}" \\h \\z \\u '; r._r.append(it)
    fld('separate')
    r = p.add_run(cfg.toc_hint); style_run(r, cfg, cfg.doc_rtl, size=cfg.size - 2)
    fld('end')
    # Word fills every field (the contents with real page numbers) when the file opens.
    upd = OxmlElement('w:updateFields'); upd.set(qn('w:val'), 'true')
    doc.settings.element.append(upd)


GENERIC_HEAD_RE = re.compile(r'^(البيان|البند|العنصر|الحقل|التفاصيل|القيمة|المعلومات|البيانات|Item|Field|Details|Value|Info)$', re.I)


def add_cover_fields(doc, rows, cfg):
    """A table on the cover becomes centered lines, never a Word table.
    Two columns with a generic header (البيان | التفاصيل) or none: 'label: value' per row.
    Otherwise (a team list: الاسم | الرقم الجامعي): the header as a bold line, then each row joined by ' - '."""
    header, body = rows[0], rows[1:]
    two = max(len(r) for r in rows) == 2
    if two and all(GENERIC_HEAD_RE.match(c.strip('* ')) or not c for c in header):
        lines = [f'**{r[0]}:** {r[1]}' if r[0] else r[1] for r in body if len(r) >= 2]
    elif two and not body:
        lines = [f'**{header[0]}:** {header[1]}']
    else:
        lines = ['**' + ' - '.join(c for c in header if c) + '**'] + [' - '.join(c for c in r if c) for r in body]
    for t in lines:
        p = doc.add_paragraph(); rtl = is_rtl_text(t, cfg.doc_rtl); set_par_dir(p, rtl)
        add_inline(p, t, cfg, rtl, size=cfg.size)
        cfg.cover_fields.add(p._p)


def layout_cover(doc, cfg):
    """Cover page layout: institution lines at the top (bold, tight), the title lower down and large,
    the fields (names, IDs, supervisor) under it, and the last line (date / year) pushed down."""
    paras = [p for p in doc.paragraphs if ''.join(p._p.itertext()).strip() or p._p.find('.//' + qn('w:drawing')) is not None]
    ti = next((k for k, p in enumerate(paras) if p.style.name == 'Title'), None)
    for k, p in enumerate(paras):
        if p._p.find('.//' + qn('m:oMathPara')) is not None:
            continue
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format; pf.first_line_indent = None; pf.left_indent = None
        if ti is None:
            para_spacing(p, cfg, before=0, after=10); continue
        if k < ti:  # institution block
            para_spacing(p, cfg, before=0, after=2, line=1.0)
            for r in p.runs:
                r.bold = True
        elif k == ti:  # title
            para_spacing(p, cfg, before=110 if ti else 160, after=70, line=1.0)
            for r in p.runs:
                r.font.size = Pt(cfg.size + 10); r._r.get_or_add_rPr()
                rpr = r._r.rPr; cs = rpr.find(qn('w:szCs'))
                if cs is None:
                    cs = OxmlElement('w:szCs'); rpr.append(cs)
                cs.set(qn('w:val'), str(int((cfg.size + 10) * 2)))
        else:  # fields under the title
            last = k == len(paras) - 1 and k > ti + 1 and p._p not in cfg.cover_fields
            para_spacing(p, cfg, before=70 if last else 0, after=8, line=1.0)


def end_front_matter(doc, cfg):
    """Cover done: lay it out, add the contents page, and start the body in a section numbered from 1."""
    body = doc.element.body
    # a trailing '---' page break would leave a blank page before the section break
    last = body[-2] if body[-1].tag == qn('w:sectPr') else body[-1]
    if last.tag == qn('w:p') and last.find('.//' + qn('w:br')) is not None and not ''.join(last.itertext()).strip():
        body.remove(last)
    layout_cover(doc, cfg)
    if cfg.toc_on:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        add_toc(doc, cfg)
    doc.add_section(WD_SECTION.NEW_PAGE)
    cfg.front = True


# ---------------- images ----------------
# Claude Docs' markdown export drops pictures ("&#91;image: <alt>\]") and charts/widgets
# ("&#91;embedded content: <caption>\]"), leaving those placeholders.
# The skill fetches each picture and passes them in document order with --images (a JSON list of
# {"alt", "path"}; a chart's "alt" is its caption); plain markdown images "![alt](local/path.png)" also work.
IMG_RE = re.compile(r'^(?:&#91;|\\?\[)image:\s*(.*?)\\?\]$|^!\[([^\]]*)\]\(([^)\s]+)\)$'
                    r'|^(?:&#91;|\\?\[)embedded content:\s*(.*?)\\?\]$')


def load_images(path):
    if not path:
        return []
    data = json.load(open(path, encoding='utf-8'))
    return [d if isinstance(d, dict) else {'alt': '', 'path': d} for d in data]


def add_image(doc, cfg, src):
    """Centered picture, scaled down to the text width (and at most 18 cm tall). False if the file is missing."""
    from docx.image.image import Image as DocxImage
    if not src or not os.path.exists(src):
        return False
    img = DocxImage.from_file(src)
    w_cm = img.px_width / (img.horz_dpi or 96) * 2.54
    h_cm = img.px_height / (img.vert_dpi or 96) * 2.54
    usable = (21.0 if cfg.paper == 'a4' else 21.59) - 2 * cfg.margins
    scale = min(1.0, usable / w_cm, 18.0 / h_cm)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = Pt(6); pf.space_after = Pt(4); pf.line_spacing = 1.0
    pf.keep_with_next = True
    p.add_run().add_picture(src, width=Cm(w_cm * scale))
    return True


def handle_image(doc, cfg, match, placeholder):
    """Returns (placeholder_text or None, caption or None) for the caller to write as paragraphs."""
    caption = match.group(4)
    alt = (match.group(1) or match.group(2) or caption or '').strip()
    src = match.group(3)
    if src is None:
        entry = cfg.images.pop(0) if cfg.images else None
        src = entry.get('path') if entry else None
        if entry and entry.get('alt') and alt and entry['alt'].strip() != alt:
            print(f'warning: image order mismatch: placeholder "{alt[:40]}" got "{entry["alt"][:40]}"', file=sys.stderr)
    if add_image(doc, cfg, src):
        cfg.img_ok += 1
        return None, (caption.strip() if caption else None)
    cfg.img_missing.append(alt[:40])
    return placeholder.format(alt=alt), None


def split_row(line):
    s = line.strip()
    if s.startswith('|'): s = s[1:]
    if s.endswith('|'): s = s[:-1]
    cells, cur, esc = [], '', False
    for ch in s:
        if esc:
            cur += ch; esc = False
        elif ch == '\\':
            esc = True
        elif ch == '|':
            cells.append(cur.strip()); cur = ''
        else:
            cur += ch
    cells.append(cur.strip())
    return cells


def add_table(doc, rows, cfg):
    header, body = rows[0], rows[1:]
    ncols = max(len(r) for r in rows)
    rtl = is_rtl_text(' '.join(' '.join(r) for r in rows), cfg.doc_rtl)
    t = doc.add_table(rows=1 + len(body), cols=ncols)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_borders(t)
    if rtl:
        table_rtl(t)
    for ri, r in enumerate([header] + body):
        row = t.rows[ri]
        no_split(row, header=(ri == 0))
        for ci in range(ncols):
            txt = r[ci] if ci < len(r) else ''
            cell = row.cells[ci]
            p = cell.paragraphs[0]
            crtl = is_rtl_text(txt, rtl)
            set_par_dir(p, crtl)
            add_inline(p, txt, cfg, crtl, size=cfg.table_size, bold=(ri == 0))
            numeric = bool(re.fullmatch(r'[\d٠-٩.,%\s/\-–]+[مهـ]*', txt)) or txt == ''
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (ri == 0 or numeric) else START
            para_spacing(p, cfg, before=2, after=2, line=1.0)
            tcPr = cell._tc.get_or_add_tcPr()
            va = OxmlElement('w:vAlign'); va.set(qn('w:val'), 'center'); tcPr.append(va)
            if ri == 0:
                cell_shade(cell, 'E7E6E6')
    usable = (21.0 if cfg.paper == 'a4' else 21.59) - 2 * cfg.margins
    lens = [max(len(r[c]) if c < len(r) else 0 for r in rows) for c in range(ncols)]
    weights = [min(max(l, 8), 50) for l in lens]
    tot = sum(weights)
    widths = [max(w / tot, 0.18) for w in weights]
    s = sum(widths); widths = [w / s * usable for w in widths]
    t.autofit = False
    for ci, gc in enumerate(t._tbl.tblGrid.findall(qn('w:gridCol'))):
        gc.set(qn('w:w'), str(int(widths[ci] / 2.54 * 1440)))
    lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); t._tbl.tblPr.append(lay)
    for row in t.rows:
        for ci, cell in enumerate(row.cells):
            cell.width = Cm(widths[ci])
    mar = OxmlElement('w:tblCellMar')
    for side in ('left', 'right'):
        e = OxmlElement(f'w:{side}'); e.set(qn('w:w'), '100'); e.set(qn('w:type'), 'dxa'); mar.append(e)
    t._tbl.tblPr.append(mar)
    cfg.after_table = True


# A heading that only labels the cover ("## صفحة الغلاف"): its content joins the cover, the heading is dropped.
COVER_H_RE = re.compile(r'^(صفحة\s+)?(ال)?غلاف|^صفحة\s+العنوان$|^(cover|title)(\s+page)?$', re.I)


def is_cover_heading(text):
    return bool(COVER_H_RE.match(text.strip('*_: ').strip()))


def has_cover(lines):
    """True when the doc has a cover: a title plus at least one more block before the first '##'
    (a '## صفحة الغلاف' heading does not end the cover; it always means there is one)."""
    blocks = 0
    for line in lines:
        s = line.strip()
        hm = re.match(r'^#{2,6}\s+(.*)$', s)
        if hm and is_cover_heading(hm.group(1)):
            return True
        if hm:
            break
        if not s or s in ('---', '***', '___'):
            continue
        if (BYLINE_RE.match(s) and '·' in s) or re.match(r'^@\S+$', s):  # date · @name line
            continue
        blocks += 1
    return blocks >= 2


def convert(md, out, cfg):
    doc = setup_document(cfg)
    lines = md.replace('\r\n', '\n').split('\n')
    i, n = 0, len(lines)
    in_refs = False
    ol_counter = 0
    cover = cfg.cover == 'on' or (cfg.cover == 'auto' and has_cover(lines))
    cfg.toc_on = cfg.toc == 'on' or (cfg.toc == 'auto' and cover)
    if cfg.toc_on and not cover:
        add_toc(doc, cfg)
        doc.add_section(WD_SECTION.NEW_PAGE)
        cfg.front = True
    in_front = cover
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1; ol_counter = 0; continue
        if s in ('---', '***', '___'):
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            i += 1; continue
        if s.startswith('```'):
            i += 1; buf = []
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i]); i += 1
            i += 1
            p = doc.add_paragraph(); set_par_dir(p, False)
            r = p.add_run('\n'.join(buf)); style_run(r, cfg, False, size=10, mono=True)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue
        # display math: $$...$$ (one or more lines), \[...\], a line that is only $...$
        se = s.replace('\\$', '$')
        if se.startswith('$$') or se.startswith('\\['):
            close = '$$' if se.startswith('$$') else '\\]'
            buf = se[2:]
            i += 1
            while not buf.rstrip().endswith(close) and i < n:
                buf += ' ' + lines[i].strip().replace('\\$', '$'); i += 1
            buf = buf.rstrip()
            if buf.endswith(close):
                buf = buf[:-2]
            for part in re.split(r'\\\\', buf):
                if part.strip():
                    add_equation(doc, part, cfg)
            cfg.after_table = False
            continue
        mm = re.fullmatch(r'\$([^$]+)\$', se)
        if mm or is_bare_equation(s):
            add_equation(doc, mm.group(1) if mm else s, cfg)
            cfg.after_table = False
            i += 1; continue
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            cfg.after_table = False
            level = len(m.group(1)); text = m.group(2).strip()
            if level >= 2 and is_cover_heading(text) and not cfg.front and cfg.cover != 'off':
                in_front = True  # cover label: drop it, its content stays on the cover
                i += 1; continue
            if in_front and level >= 2:
                end_front_matter(doc, cfg)
                in_front = False
            add_heading(doc, text, level, cfg)
            in_refs = bool(re.search(r'(المراجع|مراجع|References|Bibliography|المصادر)', text))
            if level == 1 and not cfg.keep_byline:
                j = i + 1
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and ((BYLINE_RE.match(lines[j].strip()) and '·' in lines[j]) or re.match(r'^\s*@\S+\s*$', lines[j])):
                    i = j
            i += 1; continue
        im = IMG_RE.match(s)
        if im:
            cfg.after_table = False
            text, caption = handle_image(doc, cfg, im, '[صورة: {alt}]')
            for t in (text, caption):
                if t:
                    add_paragraph(doc, t, cfg)
            i += 1; continue
        if s.startswith('|') and i + 1 < n and re.match(r'^\s*\|?\s*:?-{2,}', lines[i + 1]):
            rows = [split_row(s)]
            i += 2
            while i < n and lines[i].strip().startswith('|'):
                rows.append(split_row(lines[i])); i += 1
            if in_front:
                add_cover_fields(doc, rows, cfg)
            else:
                add_table(doc, rows, cfg)
            continue
        lm = re.match(r'^(\s*)([-*+]|\d+[.)])\s+(.*)$', line)
        if lm:
            indent = len(lm.group(1).replace('\t', '    ')) // 2
            ordered = lm.group(2)[0].isdigit()
            ol_counter = ol_counter + 1 if ordered else ol_counter
            add_list_item(doc, lm.group(3).strip(), ordered, min(indent, 2), cfg, ol_counter)
            i += 1; continue
        if s.startswith('>'):
            add_paragraph(doc, s.lstrip('>').strip(), cfg)
            i += 1; continue
        buf = [s]; i += 1
        while (not in_front and i < n and lines[i].strip() and not re.match(r'^(#{1,6}\s|\||[-*+]\s|\d+[.)]\s|```|>|\\?\$|\\\[)', lines[i].strip())
               and not is_bare_equation(lines[i].strip())):
            buf.append(lines[i].strip()); i += 1
        text = ' '.join(buf)
        if in_refs and len(text) > 40:
            add_reference(doc, text, cfg)
        else:
            add_paragraph(doc, text, cfg)
        if not SOURCE_RE.match(text):
            cfg.after_table = False
    if in_front:  # a cover with no '##' after it
        end_front_matter(doc, cfg)
    body_sec = doc.sections[-1]
    if cfg.front:
        body_sec.footer.is_linked_to_previous = False
        restart_page_numbers(body_sec._sectPr, 1)
    add_page_number(body_sec, cfg)
    doc.core_properties.title = next((l[2:].strip() for l in lines if l.startswith('# ')), '')
    doc.save(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input'); ap.add_argument('output')
    ap.add_argument('--ar-font', default='Traditional Arabic')
    ap.add_argument('--en-font', default='Traditional Arabic')
    ap.add_argument('--size', type=float, default=16)
    ap.add_argument('--table-size', type=float, default=14)
    ap.add_argument('--math-size', type=float, default=14, help='equation font size (Cambria Math)')
    ap.add_argument('--color', default='0D0D0D')
    ap.add_argument('--line', type=float, default=1.08)
    ap.add_argument('--margins', type=float, default=2.54)
    ap.add_argument('--paper', default='a4', choices=['a4', 'letter'])
    ap.add_argument('--keep-byline', action='store_true')
    ap.add_argument('--dir', default='auto', choices=['auto', 'rtl', 'ltr'])
    ap.add_argument('--images', help='JSON list of {"alt", "path"} in document order')
    ap.add_argument('--cover', default='auto', choices=['auto', 'on', 'off'],
                    help='blocks before the first ## become a cover page (auto: when there is more than the title)')
    ap.add_argument('--toc', default='auto', choices=['auto', 'on', 'off'],
                    help='table of contents page after the cover (auto: when there is a cover)')
    ap.add_argument('--toc-levels', default='2-3', help='heading levels in the contents: ## = 2, ### = 3')
    ap.add_argument('--toc-title', default=None)
    cfg = ap.parse_args()
    cfg.images = load_images(cfg.images)
    cfg.img_ok, cfg.img_missing = 0, []
    cfg.after_table = False
    cfg.eq_count = 0
    cfg.front = False
    cfg.cover_fields = set()
    md = load_markdown(cfg.input)
    if cfg.dir == 'auto':
        cfg.doc_rtl = len(AR_RE.findall(md)) > len(LATIN_RE.findall(md))
    else:
        cfg.doc_rtl = cfg.dir == 'rtl'
    if cfg.toc_title is None:
        cfg.toc_title = 'فهرس المحتويات' if cfg.doc_rtl else 'Contents'
    cfg.toc_hint = ('يُحدَّث الفهرس عند فتح الملف في Word؛ أو انقر عليه بالزر الأيمن ثم «تحديث الحقل».'
                    if cfg.doc_rtl else 'Word fills the contents when the file opens; or right-click it and choose Update Field.')
    convert(md, cfg.output, cfg)
    print(f'OK -> {cfg.output}  (direction: {"RTL" if cfg.doc_rtl else "LTR"})')
    print(f'cover+contents: {"yes" if cfg.front else "no"}; equations: {cfg.eq_count}')
    print(f'images: {cfg.img_ok} embedded, {len(cfg.img_missing)} missing'
          + (f' ({", ".join(cfg.img_missing)})' if cfg.img_missing else ''))


if __name__ == '__main__':
    main()
