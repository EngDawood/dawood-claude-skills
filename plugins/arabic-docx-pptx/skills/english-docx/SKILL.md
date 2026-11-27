---
name: english-docx
description: Builds English Word .docx files in a plain, normal look (Times New Roman, simple headings, simple tables), from a Claude Doc or written directly. APA, MLA or other styles only when the user names one. Use for Claude Doc to Word in English, an English Word file with no Claude Doc, a simple report, assignment, letter or notes in docx.
---

# English docx (Claude Doc → Word, or Word directly)

Turn a Claude Doc, or content you write yourself, into a normal-looking English .docx. Default is **plain and simple** with a separate cover page and a table of contents; no academic formatting. You build each file with a short python-docx builder that you write in the scratch folder, following `references/docx-recipes.md`.

- **Check the user's customization first, before using any style of this skill.** Look, in this order, for: (1) formatting the user named in the request or the brief (font, size, spacing, margins, paper, headings, cover, style guide); (2) a template or sample .docx the user attached or pointed to (copy its styles, do not rebuild them); (3) formatting rules in the conversation, the project files, or a client brief. Every value found there wins over this skill's value, one value at a time. Only the values the user left open fall back to the plain style below. Done when you can say, per value, whether it came from the user or from the plain style.
- Nothing customized → the plain style below.
- User names APA 7 (or a client template says so) → read `references/apa7.md` and use it in place of the plain style. Never use APA on your own.
- Another named style (MLA, Harvard, IEEE): follow the user's rules value by value; the plain style fills the gaps.
- **Cover and contents by default.** Every document gets a cover page that is **its own separate page** (alone on page 1, its content centered across and down the page, no page number) and a table of contents on the next page; the body starts on a new page numbered from 1 (see *Cover page* and *Table of contents* in `docx-recipes.md`). The cover shows the title and whatever title-page lines the content or the user gave (institution, name fields, date); never invent fields. Leave both out only when the user says so, or for a letter, memo or note of one or two pages. APA's own title page is not this cover.
- Arabic or mixed Arabic/English document: use the `arabic-docx` skill instead.

**Two routes.** Pick one before step 1:

- **From a Claude Doc**: the user gives a doc link or asks to convert a doc. Run every step.
- **Direct**: no Claude Doc. Write the content to `<scratch>/<title>.md` (see *Writing the markdown*), then run steps 0 and 4 to 7. Done when the file holds every section asked for, in full.

A client's existing .docx to fill or edit takes neither route: edit that file in place, keeping its styles.

## Steps

0. **Customization.** Run the first bullet above. Done when each value has a source (user or plain style).
1. **Locate.** Call Claude Docs `read` with `ref: {object: "project", id: <doc id>}`. For a short `claude.ai/artifact/...` link, `Artifact` read it first to get the doc id. Done when you hold the doc id and the file id of every tab.
2. **Export.** For each tab, call Claude Docs `export` with `format: "markdown"`. Large results are saved to a JSON file and the tool message names its path: read its `data.bytes_b64` (base64 of the markdown). Small inline results: decode the value. Write each tab's markdown to `<scratch>/<tab>.md`. Done when every tab has an input file on disk.
3. **Pictures.** The export's `notes` list each dropped construct; images become `[image: <alt>]` lines and charts `[embedded content: <caption>]`. When the notes report any, fetch every one, in document order:
   - Read the tab with `payload: {"projection": "outline"}`. Each picture is a `<media blob='blob/<id>' alt='…'/>`, each chart an `<embed ref='node/<id>' caption='…'/>`.
   - Picture: `read` `ref: {object: "blob", id: "<id>"}` gives its `asset`; then `Artifact` read with the doc's link and `path: "<asset>"` saves the file.
   - Chart: `read` `ref: {object: "node", id: "<id>"}`, `engine: "widget"`, `payload: {"kind": "screenshot"}` saves a PNG.
   - Write `<scratch>/images.json` as a list of `{"alt": "<alt or caption>", "path": "<file>"}` in order.
4. **Write the builder.** Read `references/docx-recipes.md` in full, then write `<scratch>/build.py` (python-docx; `pip install python-docx` when the import fails) that turns the markdown into the .docx and prints the summary line the recipes define. Reuse it for every later file in the session.
5. **Build.** `python3 <scratch>/build.py <input.md> "<doc title>.docx" [<scratch>/images.json]`. Done when the summary shows `equations` equal to the formulas in the doc and `0 missing` images, and the file passes the delivery-clean list: `unzip -l` shows no `word/comments.xml`, `word/document.xml` has no `w:ins`, `w:del` or `w:vanish`, and `docProps/core.xml` has empty author and last-modified-by.
6. **Verify.** `soffice --headless --convert-to pdf` (set `HOME=/tmp SAL_USE_VCLPLUGIN=svp` when it complains about a display), then `pdftoppm -r 60 -png` and view the first page (with a cover: the cover alone, then page 2 starting the body numbered 1), a table page, a list page, and pages with a formula or picture. Done when: headings, tables and lists look as the tables below say; every numbered list starts at 1; formulas are real equations with no leftover `_`, `\` or `$`; pictures sit centered with the caption under them; no box glyphs.
7. **Deliver.** Send the file (SendUserFile where the session has it), one clean file named after the doc title. Name anything missing (a picture that could not be fetched, every empty field the person must fill).

## Delivery-clean output (built in)

The file leaves the builder ready to hand over; nothing is cleaned afterwards. Every rule applies unless the user's brief says otherwise (say which rule you skipped and why).

- **Metadata blank**: set `core_properties` author, last_modified_by, title, subject, keywords, comments and category to empty strings (python-docx's template stamps its own name in them). No company, no custom properties, no thumbnail.
- **No comments, tracked changes, hidden text or highlights** anywhere in the file.
- **Fill-in fields** keep their label and leave the value empty: `Student:`, not `Student: [Full name]`. The person writes his own details.
- **No notes to the writer or student, no self-notes, no assumptions or reminders**, no chatbot phrases ("Here is", "I hope this helps"), no tool or watermark marks, no markdown leftovers (`**`, `#`, `|---|`, `$$`) in the text. Keep reasoning in the chat.
- **In-text citations** only when the brief or the user requires them; otherwise write the body without `(Author, year)` and keep the reference list. The reference list is in the document's language.
- **Headers and footers** hold the page number only: no report title, no author name.
- **Code, commands and terminal output** go in ordinary paragraphs: no shading, no borders, no single-cell table around them.
- **Plain look**: black text on white; a report that comes with a project (a website, an app, a design) does not use the project's colors, gradients or branding.
- **File name**: words separated by spaces or hyphens, no underscores, no `.clean` suffix (`Field Training Report.docx`); a naming rule in the brief replaces this.

## Plain style (default)

| Element | Style |
|---|---|
| Page | A4, margins 2.54 cm, page number centered in the footer (omit for a one-page doc) |
| Font | Times New Roman by default; Arial when the user asks for it or the template uses it. One family for the whole document: body, headings, tables, captions. Never Calibri (Word's default) |
| Body | 12 pt, black, **justified**, line spacing 1.5, 8 pt after, no first-line indent |
| `#` | document title, 20 bold, left-aligned; Title style |
| `##` | 16 bold |
| `###` | 14 bold |
| `####` | 12 bold |
| Table | full width, all thin grey borders, header bold on light grey (F2F2F2) and repeated, rows unsplit, cells 11 pt |
| Caption (`Table n: …`, `Figure n: …`) | 11 italic, **centered**; above a table, below a picture; kept with it |
| Lists | normal bullets and numbers, justified, 4 pt after, every numbered list restarts at 1 |
| Equations | native Word equations, Cambria Math 12, centered |
| Pictures | centered, scaled to the text width (at most 18 cm tall), caption under |
| Code | Consolas 10, left-aligned |
| Cover | separate first page; every line centered horizontally and the block centered vertically on the page; institution lines on top, title large, `label: value` fields under it, date line last; no header, footer or page number |
| Table of contents | on its own page after the cover, title `Contents` centered; filled by Word on open |
| `---` | page break |
| `date · @name` line under the title | removed |

## Writing the markdown (direct route)

Plain markdown. For the cover, put its lines before the first `##`, top to bottom: institution lines, `# Title`, `**Label:** value` fields, a closing date line. Then `#` title, `##`/`###` sections, pipe tables with a caption line above, `-` and `1.` lists, `$$…$$` equations, `![alt](/abs/path.png)` pictures. Write the sections the user asked for, in full prose; no filler headings. A field the user has not given keeps its label with an empty value (`Student:`).
