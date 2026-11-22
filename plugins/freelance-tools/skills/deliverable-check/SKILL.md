---
name: deliverable-check
description: Pre-delivery check for docx, pptx, xlsx and pdf files. Removes what must not reach the client (comments, tracked changes, speaker notes, slide footers, metadata, fill-in fields, notes to the writer or student, chatbot residue, tool marks, unrequested in-text citations, brief traps), checks the file against the brief, then writes a clean copy. Triggers on "ready to deliver", "check before sending", "قبل التسليم", "نظّف الملف", "راجع الملف للتسليم".
version: '0.3.1'
---

# Deliverable check

A delivered file carries only what the brief asked for, in the brief's language, with nothing addressed to Dawood or to the student. The script does the deterministic work; the brief settles the rest.

Script: `${CLAUDE_PLUGIN_ROOT}/skills/deliverable-check/scripts/deliverable_check.py` (needs `lxml` and `pypdf`; install with `pip install --break-system-packages lxml pypdf` when the import fails). Written below as `SCRIPT`.

Formatting script: `${CLAUDE_PLUGIN_ROOT}/skills/deliverable-check/scripts/format_check.py` (needs `lxml`; it imports `SCRIPT`, so keep both files together). It scans a docx for Calibri in English text, code or command text inside a box, header or footer text besides page numbers, and self-notes; a pptx for a deck title repeated on the slides, source lines or image credits, and self-notes; and code files for comments. It never edits. Written below as `FORMAT`.

## Global rule: requirements first

Before applying any rule in this skill, read the task requirements (the brief). When a rule conflicts with the requirements, the requirements win: skip that rule for this task and name it in the final message as excluded, with the requirement that overrides it. Examples: the brief asks for comments in the code, a branded or colored report, Calibri, a code box in the document, sources on the slides, the title in the header, or a naming pattern. Apply every rule the requirements do not contradict.

Skip a check with `--skip NAME` (repeatable) on every `SCRIPT` and `FORMAT` command, so the excluded check is neither reported nor cleaned.

- `SCRIPT` names (categories): `trap`, `filename`, `comments`, `tracked_changes`, `speaker_notes`, `slide_footer`, `metadata`, `hidden`, `placeholder`, `note`, `residue`, `ai_style`, `citations`, `format`.
- `FORMAT` names: `calibri`, `code-box`, `header-title`, `slide-repeat`, `slide-sources`, `self-notes`, `code-comments`.

Example: the brief asks for the title in the header and for comments in the code: `python3 FORMAT FILE --skip header-title --skip code-comments`.

## Delivery policy

Dawood's standing defaults. Apply them without asking (subject to the global rule) and list what changed in the final message.

### Content

- Comments, tracked changes (accepted), speaker notes, slide footer and date text, metadata: removed by `clean`. Author fields stay blank unless Dawood names an author.
- Fill-in fields are blanked and their label kept: `Student: [Full name] — ID [Student ID]` becomes `Student:`. The student writes his own details.
- Notes to the writer or student, tool and watermark marks, chatbot residue, markdown leftovers: deleted.
- Self-notes: never write a note, assumption, reminder or reasoning for your own understanding into a deliverable. That covers document text, slides, cells, hidden text, comments, metadata and code comments. Keep it in the chat. When you find one in a file, delete it.
- In-text citations stay only when the brief requires them. Otherwise clean with `--strip-citations`; the reference list stays.
- The reference list follows the output language: an Arabic deliverable with an all-English reference list is a finding.
- Every trap word from the brief is gone.

### Presentations

- No speaker notes. `clean` removes them; never add new ones.
- No sources and no image credits on the slides, and no references slide, unless the brief asks for them.
- No deck title or author name repeated on every slide as a footer. Only slide numbers.

### Report formatting

- A report that comes with a non-document project (a website, an app, a design, code) is a plain document: normal headings and tables, black text on white. It does not use the project's theme colors, gradients, fonts or branding. Only the project itself carries its design.
- An English docx uses Arial or Times New Roman for body text, headings and tables. Replace Calibri (the Word default) with one of them; use one family per document. Arabic text keeps the font the Arabic rules or the brief set.
- Code, commands, terminal output and similar technical text inside a docx go in ordinary paragraphs. Add no background shading, no borders and no single-cell table around them.
- Headers and footers of a report carry the page number only. Do not put the report title or the author name in them.

### Code files

- Deliver code with as few comments as it can carry: none by default. Add comments only when the requirements ask for them, and then only the kind and amount asked for.
- Do not add comments that restate the line below them, section banners, header blocks, or a docstring on every function. Delete such comments when cleaning code you wrote.

### File names

- The delivered file is named with words separated by spaces or hyphens, in Arabic or English, with no underscores and no `.clean` suffix: `تقرير التدريب الميداني.docx`, `Asthma-Presentation.pptx`. A naming rule in the brief replaces this one and is followed exactly.

Ask Dawood only about: content the brief did not ask for, a reference list in the wrong language (it needs new sources), dense citations when citations are required, and long `ai_style` rewrites.

## Steps

1. **Load the brief.** Take the first that exists: a `brief.md` written by project-analyzer (attached, in the working folder, or pasted), the requirements already in the conversation, or the brief Dawood sends when asked once. Fill each field of `references/brief-format.md` from it. Done when every field holds a value or `unknown`. When no brief can be had, mark the brief checks skipped and continue with the file checks. Then list the policy rules the requirements override (global rule): these become the `--skip` names for every command below.

2. **Scan.** Run `python3 SCRIPT scan FILE... --find WORD` with one `--find` per trap word and one `--skip` per excluded category. For every docx, pptx and code file, also run `python3 FORMAT FILE... --find WORD` with one `--skip` per excluded check. Scan never edits. Done when every file has a report.

3. **Check against the brief.** Compare the file with each brief field: output language, length (slides, words, pages), required sections present, citation and reference rules, format (style guide, RTL, template). For the formatting rules, check the report is plain when it comes with a project (by eye: `FORMAT` does not see colors), and take the `FORMAT` findings for Calibri in an English docx, code or command text in a box, header or footer text, a repeated deck title, sources on slides, self-notes, and comments in code files. List anything present that the brief did not ask for as off-brief content. Done when each field is marked `match`, `mismatch` or `skipped`.

4. **Clean.** Run `python3 SCRIPT clean FILE --find WORD...` with the same `--skip` names, adding `--strip-citations` (docx) when the brief does not require in-text citations and `--thin-citations` when it does. The original stays untouched. Done when `<name>.clean.<ext>` exists and its re-scan shows zero `auto` findings. `clean` does not touch fonts, boxes, headers, sources on slides, self-notes or code comments; step 5 does.

5. **Fix the rest on the clean copy.** Edit with the matching format skill (docx, pptx, xlsx, pdf). Policy items first, without asking: delete notes, self-notes, tool marks, residue and trap words; blank fill-in fields the script could not reach (a field split across runs); remove citations in pptx, xlsx and pdf when the policy says so; reset a report that carries project theme colors to plain formatting; change Calibri to Arial or Times New Roman in an English docx; remove shading, borders and boxes around code and command text; reduce headers and footers to the page number; delete source lines, image credits and a repeated deck title from the slides; strip unrequested comments from code files. Then put the ask items to Dawood in one message. For `ai_style` findings, read `references/humanizer-rules.md` and rewrite by its procedure. Done when each item is fixed or Dawood chose to keep it.

6. **Verify.** Re-run `scan` and `FORMAT` on the final file with the same `--find` and `--skip` arguments. Done when only items Dawood chose to keep remain. Save the final file under its delivery name (`-o NAME` on clean, or a renamed copy). Reply in one short message: the clean file, what the policy removed, the rules excluded by the requirements (the `--skip` names and why), the brief mismatches left, and the kept items.

7. **Lessons.** After the reply in step 6, check whether this run taught something the skill does not already say: a pattern the scan missed or flagged wrongly, an error you hit, a correction from Dawood, or a better approach. If it did, send one message titled `ملاحظات للمهارة` with at most 3 proposed edits, each as: the file (`SKILL.md`, `references/*.md`, or a rule in `scripts/deliverable_check.py` or `scripts/format_check.py`), the current line, the new text, and a one-line reason. Change nothing until Dawood answers. Apply only the approved edits to the `EngDawood/dawood-claude-skills` repo on main (files under `plugins/freelance-tools/skills/deliverable-check/`) with the github-mcp tools (`gh_file_get`, then `gh_file_put` for one file or `gh_push_files` for several, in one commit). A script change also gets a case in `tests/run_tests.py` (or in a new file under `tests/` for `format_check.py`); run the tests first when a shell is available. When the github-mcp tools are not in the session, write each approved edit in the reply instead (file path, the exact old text, the exact new text) so Dawood can apply it. Done when the edits are pushed or written out, Dawood declined, or the run taught nothing new (then say nothing).

## Categories

| Category | Fix | What it covers |
|---|---|---|
| trap | manual | a trap word from the brief found in the file |
| filename | manual | file name with underscores; rename unless the brief sets a naming rule |
| comments | auto | Word comments, slide comments, cell notes, PDF annotations |
| tracked_changes | auto | insertions, deletions, formatting revisions (accepted on clean) |
| speaker_notes | auto | pptx notes |
| slide_footer | auto | text in slide footer and date placeholders |
| metadata | auto | author, last modified by, company, custom properties, thumbnail, tool name |
| placeholder | auto or manual | fill-in fields such as `[Full name]` (auto in docx and pptx); TODO, TBD, lorem ipsum, template fields, missing-source markers (manual) |
| note | manual | notes to the writer or student: "replace this with your", "ملاحظة للطالب", "قبل التسليم" |
| residue | manual | chatbot phrases, tool and watermark marks, markdown symbols, copied citation markers, odd links |
| ai_style | manual | machine-sounding patterns: not-X-but-Y contrasts, dashes as connectors, stock words, inflated or sales wording, stock closers, emoji, bold-label lists |
| citations | optional or manual | dense paragraphs; the same citation repeated in one paragraph |
| hidden | manual | hidden text, slides and sheets |
| format | manual | missing right-to-left direction, empty slides, error cells, blank pages. From `FORMAT`: Calibri in an English docx; code, command or output text inside a background box; header or footer text besides page numbers; the same text repeated on most slides; source lines and image credits on slides; self-notes; comments in code files. Project theme colors in a report are checked by eye |

The report also prints the reference list line (entries, Arabic, other) for docx and pptx.

Thresholds, regex coverage and known limits of `SCRIPT` live in `references/checks.md`. Read it when a finding looks wrong or Dawood asks how a check works. The rules of `FORMAT` are in the docstring at the top of `scripts/format_check.py`.
