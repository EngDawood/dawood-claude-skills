# Word recipes (python-docx + raw OOXML)

How to make each element in python-docx for the plain English style. `qn` and `OxmlElement` come from `docx.oxml.ns` and `docx.oxml`. `w:sz` is in half-points (11 pt = 22).

## Builder shape

One file, `<scratch>/build.py`, that reads the markdown, walks it line by line into blocks, and writes the .docx. Parse:

- `#` title, `##`/`###`/`####` headings.
- Pipe tables (header line, then a `|---|` line), `- ` / `1. ` lists (indent 2 spaces = one level), `> ` quotes as plain paragraphs, fenced code as a Consolas 10 paragraph.
- Display math: `$$…$$` (may span lines), `\[…\]`, a line that is only `$…$`.
- Pictures: `![alt](path)` lines and the export's `[image: alt]` / `[embedded content: caption]` placeholders, filled in order from `images.json`.
- Inline `**bold**`, `*italic*`, `` `code` ``, `[text](url)` (keep the text); unescape `\* \_ \[ \] \# \- \.`.
- A paragraph is consecutive non-blank lines joined by spaces. `---` is a page break. The `date · @name` line right under the `#` title is dropped.

Print one summary line at the end: `cover no|yes (separate page); toc no|yes; equations N; images N embedded, M missing; tables N`.

## Document setup

- Values below are the plain-style defaults. Replace each one the user customized (font, size, spacing, margins, paper, heading sizes); with a user template, open it and add content to it so its styles stay.
- A4, portrait, margins 2.54 cm.
- `Normal` style: the chosen family (Arial, or Times New Roman when asked) at 11 pt, set on every style and run; never leave the Word default Calibri, colour black, line spacing 1.15, 8 pt after. Remove any `w:asciiTheme`/`w:hAnsiTheme`/`w:eastAsiaTheme`/`w:cstheme` attributes from `w:rFonts` in every style you touch; theme fonts override the face you set.
- `Title` 20 bold, left; `Heading 1`–`3` = `##`/`###`/`####` at 16 / 13 / 11 bold, black, 12 before and 4 after, keep with next. Remove the Title style's `w:pBdr`.
- Footer: centered `PAGE` field (begin / instrText `PAGE` / end, 10 pt).

## Paragraphs and runs

- Every run sets `w:rFonts` (ascii/hAnsi/eastAsia), `w:sz`, colour; bold adds `w:b`, italic `w:i`.
- Body is left-aligned (no `w:jc`), no first-line indent.
- Caption line (`Table n: …`, `Figure n: …`): 10 pt italic, 6 before, 4 after, keep with next.

## Lists

- `List Bullet` / `List Number` styles (`List Bullet 2`, `List Number 2` for level 1), 4 pt after.
- **Every numbered list restarts at 1**: for each new list, add a `w:num` to the numbering part that points at the same `w:abstractNumId` as `List Number`'s num and carries `<w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride>`; give each item `<w:numPr><w:ilvl w:val="0"/><w:numId w:val="<new id>"/></w:numPr>` as the second child of its `w:pPr`. A blank line ends a list.

## Tables

- `w:tblBorders` top/left/bottom/right/insideH/insideV, each `single`, `sz=4`, colour BFBFBF.
- Header row: `<w:tblHeader w:val="true"/>`, bold, shading `<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>`. Every row `<w:cantSplit w:val="true"/>`.
- Cells: 10.5 pt, 2 pt before/after, line 1.0, `<w:vAlign w:val="center"/>`; numeric cells (digits, `% . , / -`) right-aligned, text left.
- Width: full text width (15.92 cm), `<w:tblLayout w:type="fixed"/>`. Column weight = longest cell text length clamped to 8–50, each column at least 12% before normalising. Set `w:gridCol` widths and every cell's width in twips (cm / 2.54 × 1440), cell margins left/right 100 twips.
- 10 pt space before the paragraph that follows a table.

## Equations (native OMML)

A centered paragraph, 4 pt before and after, line 1.0, keep with next, holding `<m:oMathPara><m:oMath>…</m:oMath></m:oMathPara>` (`m` = `http://schemas.openxmlformats.org/officeDocument/2006/math`). Never an image or plain text.

- Run: `<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr><m:t>Z</m:t></m:r>` (12 pt).
- `X_1` → `m:sSub`; `x^2` → `m:sSup`; both → `m:sSubSup`.
- `\frac{a}{b}` → `<m:f><m:num>a</m:num><m:den>b</m:den></m:f>`; `\sqrt{a}` → `<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>a</m:e></m:rad>`.
- `\text{…}`: a run with `<m:rPr><m:nor/></m:rPr>`.
- Symbols: `\approx` ≈, `\times` ×, `\div` ÷, `\cdot` ·, `\le` ≤, `\ge` ≥, `\ne` ≠, `\pm` ±, `\sum` ∑, `\infty` ∞, `\to` →, Greek names → letters; drop `\left \right \displaystyle \quad \,`. `-` → `−`, `*` → `×`.
- Before parsing: NFKC-normalise, undo markdown escapes, drop spaces (a space inside `m:t` renders as a wide gap). `\\` splits a block into one equation per line.

## Pictures

Centered paragraph, 6 before, 4 after, keep with next; width scaled down to the text width and height to at most 18 cm (`run.add_picture(path, width=…)`). A chart's caption goes under it. A missing file leaves `[image: alt]` as text and counts as missing.

## Cover page (separate page) and contents page

Everything before the first real `##` is the cover, when there is more than a title.

- **Own section**: the cover is the first section and holds only its own lines. The body is a new section (`WD_SECTION.NEW_PAGE`), so the cover always sits alone on page 1.
- **Layout**: each line its own centered paragraph. Lines above the `#` title (institution block): bold, 0 before, 2 after. Title: 26 pt bold (set `w:szCs` too), 110 pt before (160 when nothing sits above it), 70 after. Lines under the title (fields as `label: value`): 0 before, 8 after. A standalone last line (a date) gets 70 pt before.
- **A table on the cover is printed as lines**, never as a Word table: two columns with a generic header (Item, Field, Details, Value) or a lone row become one `**label:** value` line per row; otherwise the header joined by ` - ` in bold, then each row joined by ` - `.
- **No header, footer or page number on the cover.** The body section's footer is unlinked from the previous one and holds the centered `PAGE` field; add `<w:pgNumType w:start="1"/>` right after `w:pgMar` so the body's first page is numbered 1.
- A trailing page break at the end of the cover is removed, so no blank page appears; the section break does the work.
- **Contents page** (only when asked): between the cover and the body, a centered bold `Contents` 16 pt, then one paragraph holding a TOC field (`TOC \o "2-3" \h \z \u`, begin/instr/separate/hint/end runs, `w:dirty="true"`), plus `<w:updateFields w:val="true"/>` in settings so Word fills it on open. Verify by rendering: LibreOffice shows the hint line, Word fills the entries.
- No cover: one section, page number in the footer from page 1.

## Metadata and clean output

Before saving: `cp = doc.core_properties`; set `author`, `last_modified_by`, `title`, `subject`, `keywords`, `comments`, `category` to `''` (python-docx's default template stamps its own name in them). Never create a comments part, `w:ins`/`w:del`, `w:vanish` or highlights. Code goes in ordinary paragraphs with no shading or borders. Headers and footers hold the page number only.
