# Word recipes (python-docx + raw OOXML)

How to make each house-style element in python-docx. Each rule was learned from a render that came out wrong; follow it as written. `qn` and `OxmlElement` come from `docx.oxml.ns` and `docx.oxml`. Sizes: `w:sz` and `w:szCs` are half-points (16 pt = 32).

## Builder shape

One file, `<scratch>/build.py`, that reads the markdown, walks it line by line into blocks, and writes the .docx. Parse:

- `#` title, `##`/`###`/`####` headings; a `## صفحة الغلاف` (or `الغلاف`, `Cover Page`, `Title Page`) heading is dropped and its content joins the cover.
- Pipe tables (header line, then a `|---|` line), `- ` / `1. ` lists (indent 2 spaces = one level), `> ` quotes as plain paragraphs, fenced code as a left-to-right Consolas 10 paragraph.
- Display math: `$$…$$` (may span lines), `\[…\]`, a line that is only `$…$`, and a bare formula line (no Arabic, `symbol = numbers/symbols/operators`, e.g. `Z = 3.3X_1 + 1.2X_2`).
- Pictures: `![alt](path)` lines, and the export's `&#91;image: alt\]` / `&#91;embedded content: caption\]` placeholders, filled in order from `images.json`.
- Inline `**bold**`, `*italic*`, `` `code` ``, `[text](url)` (keep the text); unescape `\* \_ \[ \] \# \- \.`.
- A paragraph is consecutive non-blank lines joined by spaces, except on the cover, where each line is its own paragraph.
- `---` is a page break. The `date · @name` line right under the `#` title is dropped.

At the end the builder prints one summary line: `direction RTL|LTR; cover yes|no; toc yes|no; equations N; images N embedded, M missing; tables N`.

## Direction

- Document direction: Arabic letters outnumber Latin letters in the whole text.
- A paragraph is right-to-left when it has Arabic letters and they are at least 30% of its Latin letter count; with no letters at all it takes the document direction.
- Arabic letters: U+0600–06FF, 0750–077F, 08A0–08FF, FB50–FDFF, FE70–FEFF.

## Document setup

- A4 21 × 29.7 cm, portrait, all margins 2.54 cm.
- Section direction: `<w:bidi/>` in `w:sectPr`, inserted **before** `w:textDirection`, `w:rtlGutter`, `w:docGrid` or `w:printerSettings` (schema order; elsewhere Word repairs the file).
- `Normal` style: size 16 pt, `w:rFonts` ascii/hAnsi/eastAsia = Latin font, `w:cs` = Arabic font (both Traditional Arabic by default), `<w:lang w:val="en-US" w:bidi="ar-SA"/>`, `<w:szCs w:val="32"/>`. Remove any `w:asciiTheme`/`w:hAnsiTheme`/`w:eastAsiaTheme`/`w:cstheme` attributes from `w:rFonts`, in every style you touch; theme fonts override the faces you set.
- `Heading 1`–`4`: sizes 22 / 18 / 16 / 16 pt, bold, colour 0D0D0D, the same rFonts.
- `Title` style for the `#` line (it has no outline level, so it stays out of the contents): 22 pt bold; remove its `w:pBdr` and `w:contextualSpacing`.

## Paragraphs and runs

- Right-to-left paragraph: `<w:bidi w:val="1"/>` in `w:pPr`, placed right after `w:pStyle` (first child when there is none). A left-to-right paragraph has no `w:bidi`.
- Every run: `w:rFonts` (ascii/hAnsi/eastAsia Latin font, `w:cs` Arabic font), `w:sz` and `w:szCs` both set, colour 0D0D0D; bold adds `w:b` **and** `w:bCs`, italic `w:i` and `w:iCs` (Arabic text reads the Cs variants). A run with Arabic text in a right-to-left paragraph also gets `<w:rtl w:val="1"/>`.
- Body: justified, line spacing 1.08, 0 before, 8 pt after; 10 pt before when it directly follows a table.
- **Start alignment**: leave `w:jc` unset. In a right-to-left paragraph `jc="right"` means the line's end, the LEFT edge.
- Headings: `#` centered; `##`+ centered when the text starts with المحور / الفصل / مراجع / المراجع / قائمة / ملخص / Chapter / References / Abstract, start-aligned otherwise; 10 pt before (6 for `###`+), 6 after, keep with next.
- Multi-level heading number (`2.1`, `5.3.2` at the start of a right-to-left heading): put U+200F (RLM) on both sides of every dot, `2‏.‏1`, so the main number sits on the right.
- Caption line (`جدول (n): …`, `شكل (n)`, `Table n`, `Figure n`): bold, centered, 6 before, 4 after, keep with next.
- `المصدر: …` / `Source: …` line: 14 pt, start-aligned, 4 before, 10 after.
- References (paragraphs under a heading containing المراجع / مراجع / المصادر / References / Bibliography, longer than 40 characters): start-aligned, hanging indent 0.635 cm (`left_indent = Cm(0.635)`, `first_line_indent = Cm(-0.635)`), 6 after.

## Lists

- `List Bullet` / `List Number` styles (`List Bullet 2`, `List Number 2` for level 1), 16 pt, justified, line 1.16, 4 pt after; clear `left_indent` so the style's indent applies.
- **Every numbered list restarts at 1**: for each new list, add a `w:num` to the numbering part that points at the same `w:abstractNumId` as `List Number`'s num and carries `<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>`; give each item `<w:numPr><w:ilvl w:val="0"/><w:numId w:val="<new id>"/></w:numPr>` as the second child of its `w:pPr`. A blank line ends a list.

## Tables

- Right-to-left table (its text is mostly Arabic): `<w:bidiVisual w:val="1"/>` as the **first** child of `w:tblPr`. The first column then sits on the right; keep cells in logical order.
- Borders: `w:tblBorders` with top/left/bottom/right/insideH/insideV, each `single`, `sz=8`.
- Header row: `<w:tblHeader w:val="true"/>` (repeats on each page), bold, shading `<w:shd w:val="clear" w:color="auto" w:fill="E7E6E6"/>`. Every row `<w:cantSplit w:val="true"/>`.
- Cells: 14 pt, 2 pt before/after, line 1.0, `<w:vAlign w:val="center"/>`; header and numeric cells (digits, `% . , / -`, a trailing م or هـ) centered, text cells start-aligned; each cell paragraph gets its own direction.
- Width: full text width (15.92 cm on A4), centered. Column weight = longest cell text length clamped to 8–50, each column at least 18% before normalising. Set `w:gridCol` widths in twips (cm / 2.54 × 1440), every cell's width, `<w:tblLayout w:type="fixed"/>`, and cell margins left/right 100 twips.

## Cover page, contents page, page numbers

Everything before the first real `##` is the cover.

- **Cover layout**: each line its own centered paragraph. Lines above the `#` title: bold, 0 before, 2 after, line 1.0 (the institution block at the top). Title: 26 pt bold (set `w:szCs` too), 110 pt before (160 when nothing sits above it), 70 after. Lines under the title: 0 before, 8 after. The last line, when it is a standalone line (a date or year) and not a field, gets 70 pt before.
- **A table on the cover is printed as lines, never as a Word table.** Two columns with a generic header (البيان, البند, العنصر, الحقل, التفاصيل, القيمة, Item, Field, Details, Value) or a lone row: one `**label:** value` line per row. Otherwise (a team list): the header joined by ` - ` in bold, then each row joined by ` - `.
- A trailing page break at the end of the cover is removed, so no blank page appears.
- **Contents page** (when there is a cover): a page break, a centered bold title `فهرس المحتويات` (`Contents` in English) 18 pt, 12 after, then one paragraph holding a TOC field: run `<w:fldChar w:fldCharType="begin" w:dirty="true"/>`, run `<w:instrText xml:space="preserve"> TOC \o "2-3" \h \z \u </w:instrText>`, run `<w:fldChar w:fldCharType="separate"/>`, a hint run (`يُحدَّث الفهرس عند فتح الملف في Word؛ أو انقر عليه بالزر الأيمن ثم «تحديث الحقل».`, 14 pt), run `<w:fldChar w:fldCharType="end"/>`. Add `<w:updateFields w:val="true"/>` to the settings part so Word fills the contents when the file opens.
- TOC 1–4 styles (create `toc 1`… with styleId `TOC1`… when missing): based on Normal, 14 pt, bold for levels 1–2, `w:bidi`, a right tab with dot leader at the text width in twips, 0 before / 60 twips after, start indent `(level − 2) × 400` twips.
- Then a new section (`WD_SECTION.NEW_PAGE`) for the body. Its footer is unlinked from the previous one and holds a centered `PAGE` field (begin / instrText `PAGE` / end, 11 pt); its `w:pgNumType w:start="1"` goes right after `w:pgMar`. The cover section has no footer, so the cover and contents pages carry no number.
- No cover: one section, page number in the footer from page 1.

## Equations (native OMML)

A centered left-to-right paragraph (no `w:bidi`), 4 pt before and after, line 1.0, keep with next, holding `<m:oMathPara><m:oMath>…</m:oMath></m:oMathPara>` (`m` = `http://schemas.openxmlformats.org/officeDocument/2006/math`). Never an image or plain text.

- Run: `<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:color w:val="0D0D0D"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr><m:t>Z</m:t></m:r>` (14 pt).
- `X_1` → `<m:sSub><m:e>X</m:e><m:sub>1</m:sub></m:sSub>`; `x^2` → `m:sSup` with `m:sup`; both → `m:sSubSup`.
- `\frac{a}{b}` → `<m:f><m:num>a</m:num><m:den>b</m:den></m:f>`; `\sqrt{a}` → `<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>a</m:e></m:rad>`.
- `\text{…}`: a run with `<m:rPr><m:nor/></m:rPr>` and the body fonts (`w:rtl` when Arabic).
- Symbols: `\approx` ≈, `\times` ×, `\div` ÷, `\cdot` ·, `\le` ≤, `\ge` ≥, `\ne` ≠, `\pm` ±, `\sum` ∑, `\infty` ∞, `\to` →, Greek names → letters; drop `\left \right \displaystyle \quad \,`. `-` → `−`, `*` → `×`, `'` → `′`.
- Before parsing: NFKC-normalise (folds math-italic letters such as 𝑍), undo markdown escapes, and drop spaces (a space inside `m:t` renders as a wide gap). `\\` splits a display block into one equation per line.

## Pictures

Centered paragraph, 6 before, 4 after, line 1.0, keep with next; width scaled down to the text width and the height to at most 18 cm (`run.add_picture(path, width=…)`). A chart's caption goes under it as a caption line. A missing file leaves `[صورة: alt]` as text and counts as missing.

## Metadata and clean output

Before saving: `cp = doc.core_properties`; set `author`, `last_modified_by`, `title`, `subject`, `keywords`, `comments`, `category` to `''` (python-docx's default template stamps its own name in them). Never create a comments part, `w:ins`/`w:del`, `w:vanish` or highlights. Code goes in ordinary paragraphs with no shading or borders. Headers and footers hold the page number only.
