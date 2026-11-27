---
name: arabic-docx
description: Builds Arabic right-to-left Word .docx files (Saudi thesis house style), from a Claude Doc or written directly. Use for Claude Doc to Word (تحويل المستند إلى ورد), a Word file with no Claude Doc (docx مباشرة), or a formal report with cover and contents (غلاف + فهرس).
---

# Arabic docx (Claude Doc → Word, or Word directly)

Turn a Claude Doc, or content you write yourself, into a .docx that opens in Word already in its **house style**: the tables below are the single source of truth for each language, and a client's template overrides them value by value. You build each file with a short python-docx builder that you write in the scratch folder, following `references/docx-recipes.md`; that file holds the exact XML for each element, and every rule in it comes from a render that went wrong.

- Arabic doc → the Arabic house style (right-to-left paragraphs and tables, Traditional Arabic, thesis spacing, cover and contents pages, native Word equations)
For a document written in English, use the `english-docx` skill instead. The client's instructions win when they name a style. Read `references/formal-layout.md` only for what the house style lacks: an APA reference list for an Arabic report, charts drawn from data, or a contents page with its page numbers already written in.

**Two routes.** Pick one before step 1:

- **From a Claude Doc**: the user gives a doc link or asks to convert a doc. Run every step.
- **Direct**: the user wants a Word file and gives no Claude Doc. In place of steps 1 to 3, write the content to `<scratch>/<title>.md` by the rules in `references/writing-markdown.md`, then run steps 4 to 8 on it. Done when the file holds every section the user asked for, written in full, and every cover field is either filled or left as its label with an empty value.

A client's existing .docx to fill or edit takes neither route: edit that file in place, keeping its styles.

Build the final file with your builder. The connector's own `docx` export carries no bidi settings, so its Arabic tables and paragraphs come out mirrored.

## Steps

1. **Locate.** Call Claude Docs `read` with `ref: {object: "project", id: <doc id>}`. For a short `claude.ai/artifact/...` link, `Artifact` read it first to get the doc id. Done when you hold the doc id and the file id of every tab.
2. **Export.** For each tab, call Claude Docs `export` with `format: "markdown"`. Large results are saved to a JSON file and the tool message names its path: read its `data.bytes_b64` (base64 of the markdown). Small inline results: decode the value. Write each tab's markdown to `<scratch>/<tab>.md`. Done when every tab has an input file on disk.
3. **Pictures.** The export's `notes` list each dropped construct; images become `&#91;image: <alt>\]` lines and charts or other widgets become `&#91;embedded content: <caption>\]`. When the notes report any, fetch every one, in document order:
   - Read the tab with `payload: {"projection": "outline"}`. Each picture is a `<media blob='blob/<id>' alt='…'/>`, each chart an `<embed ref='node/<id>' caption='…'/>`. A `<gap>` inside a list or table hides its blocks; read that block with `{"kind": "view", "parentId": "<its id>"}` when the outline shows fewer pictures than the notes count.
   - Picture: `read` `ref: {object: "blob", id: "<id>"}` gives its `asset`; then `Artifact` read with the doc's link and `path: "<asset>"` saves the file and prints its path.
   - Chart: `read` `ref: {object: "node", id: "<id>"}`, `engine: "widget"`, `payload: {"kind": "screenshot"}` saves a PNG and prints its path.
   - Write `<scratch>/images.json` as a list of `{"alt": "<alt or caption>", "path": "<file>"}` in the order they appear.
   Done when the list holds one entry per dropped picture and chart.
4. **Write the builder.** Read `references/docx-recipes.md` in full, then write `<scratch>/build.py` (python-docx; `pip install python-docx` when the import fails) that turns the markdown into the .docx by those recipes and the house-style table for the doc's language, and prints the summary line the recipes define. Pass the client's template values (font, size, margins, paper) in place of the house-style ones. Reuse the same builder for every later file in the session. Done when every element the markdown contains has its recipe in the builder.
5. **Build.** `python3 <scratch>/build.py <input.md> "<doc title>.docx" [<scratch>/images.json]`. Done when the file passes the delivery-clean list (`unzip -l` shows no `word/comments.xml`, `word/document.xml` has no `w:ins`, `w:del` or `w:vanish`, `docProps/core.xml` has empty author and last-modified-by) and the summary line shows direction RTL, `cover yes` and `toc yes` when the doc has cover lines before its first `##`, an `equations` count equal to the formulas in the doc, and `0 missing` images.
6. **Verify.** `soffice --headless --convert-to pdf` (set `HOME=/tmp SAL_USE_VCLPLUGIN=svp` when it complains about a display), then `pdftoppm -r 60 -png` and view the cover page, the contents page, a body page, a table page, a numbered-list page, a page with a formula, and a page with a picture when there is one. Done when every page viewed passes every check:
   - layout matches the house-style table (first table column on the right, grey header row);
   - the cover sits alone on page 1 and shows only its own lines, centered: institution block on top, title large below it, fields as `label: value` lines; the contents page follows, and the body's first page is numbered 1 (LibreOffice shows the contents hint line instead of entries; Word fills the entries on open);
   - headings placed per the house style (right-aligned Arabic headings sit on the right edge), and a multi-level number such as 2.1 shows the main number 2 on the right;
   - every formula is a centered equation with real subscripts, with no leftover `_`, `\`, or `$`;
   - each picture centered within the margins, its caption under it;
   - each numbered list starts at 1;
   - no box glyphs or reversed words.
   The render box usually lacks Traditional Arabic and substitutes a fallback face; judge layout, not typeface.
7. **Deliver.** Send the file (SendUserFile where the session has it), one clean file named after the doc title in the doc's language. Tell the user that Word asks to update fields when the file opens: answering Yes fills the contents with page numbers. Name anything still missing (comments, a picture that could not be fetched, every empty field the person must fill) so the user can add it by hand.
8. **Lesson.** Every run that hit a defect (a failed step, a wrong render, a user correction to the output) ends with a lesson for this skill. Done when each defect is either fixed in the skill's source or the user declined the fix:
   - Name the defect and its root cause in one line each, then propose the smallest change that prevents it: a recipe, the house-style table, or a step here.
   - Make the change only after the user approves the proposal.
   - Apply it in a working copy of this skill, rerun steps 5 and 6 with the fixed builder on the same doc, and send the user the new .docx.
   - Once the user confirms the new output is correct, carry the change to the skill's source. A user who maintains the plugin (a clone of `EngDawood/arabic-docx-pptx-skills` or a fork): commit it there and raise `version` in `.claude-plugin/plugin.json`. Any other user: send the change as a patch file, ready to attach to an issue at https://github.com/EngDawood/arabic-docx-pptx-skills/issues.
   - A defect the user declines stays as it is; keep the deliverable from step 7.

## Delivery-clean output (built in)

The file leaves the builder ready to hand over; nothing is cleaned afterwards. Every rule applies unless the user's brief says otherwise (say which rule you skipped and why).

- **Metadata blank**: set `core_properties` author, last_modified_by, title, subject, keywords, comments and category to empty strings (python-docx's template stamps its own name in them). No company, no custom properties, no thumbnail.
- **No comments, tracked changes, hidden text or highlights** anywhere in the file.
- **Fill-in fields** keep their label and leave the value empty: `الطالبة:`, not `الطالبة: [الاسم]`. The person writes his own details.
- **No notes to the writer or student, no self-notes, no assumptions or reminders**, no chatbot phrases ("Here is", "I hope this helps"), no tool or watermark marks, no markdown leftovers (`**`, `#`, `|---|`, `$$`) in the text. Keep reasoning in the chat.
- **In-text citations** only when the brief or the user requires them; otherwise write the body without `(Author, year)` and keep the reference list. The reference list is in the document's language.
- **Headers and footers** hold the page number only: no report title, no author name.
- **Code, commands and terminal output** go in ordinary paragraphs: no shading, no borders, no single-cell table around them.
- **Plain look**: black text on white; a report that comes with a project (a website, an app, a design) does not use the project's colors, gradients or branding.
- **File name**: words separated by spaces or hyphens, no underscores, no `.clean` suffix (`تقرير التدريب الميداني.docx`); a naming rule in the brief replaces this.

## Arabic house style

Taken from a hand-formatted Saudi master's thesis chapter.

| Element | Style |
|---|---|
| Page | A4, margins 2.54 cm, centered page number |
| Cover page | every block before the first `##` (a `## صفحة الغلاف` heading is dropped and its content kept), alone on page 1, no page number, every line centered and its own paragraph: institution lines bold at the top, title 26 pt lower down, fields under it, a closing date line pushed down; a cover table becomes `label: value` lines; added when there is more than the title |
| Contents page | page 2, title فهرس المحتويات, a TOC field of `##`–`###` with dot leaders, filled by Word on open (`updateFields`) |
| Body page numbers | new section after the contents, numbering starts at 1 |
| Body | Traditional Arabic 16, colour 0D0D0D, justified, line 1.08, 8 pt after |
| `#` | 22 bold, centered; Title style, so it stays out of the table of contents |
| `##` | 18 bold |
| `###` | 16 bold |
| Heading alignment | centered when it opens with المحور / الفصل / مراجع / المراجع; right otherwise (أولاً، 1.، خلاصة) |
| Multi-level heading number (2.1, 5.3.2) | RLM on both sides of each dot, so the main number sits on the right in Arabic reading order |
| Equations | native Word equations (OMML), Cambria Math 14, centered, left-to-right; LaTeX subset: `_` `^` `\frac` `\sqrt` `\text` `\approx` `\times` `\div` `\le` `\ge` Greek letters |
| Caption `جدول (n): …` | 16 bold centered, kept with the table |
| Table | full width, 14 pt, header bold on E7E6E6 repeated each page, rows unsplit, cells vertically centered, text right, numbers centered |
| After a table | 10 pt space before the next paragraph |
| Lists | 16 pt, 4 pt after, every numbered list restarts at 1 |
| References (under a heading with المراجع / References) | right-aligned, hanging indent 0.635 cm |
| English-only paragraph | left-to-right, same font |
| Pictures and charts | centered, scaled to the text width (at most 18 cm tall); a chart's caption under it |
| Right-aligned text | no `jc` set, so Word aligns it to the start (right) of the RTL line; `jc="right"` would land on the left |
| `date · @name` line under the title | removed |
| `---` | page break (dropped when it ends the cover, so no blank page) |
