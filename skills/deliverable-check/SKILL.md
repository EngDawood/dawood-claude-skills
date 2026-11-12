---
name: deliverable-check
description: Pre-delivery check for docx, pptx, xlsx and pdf files. Removes what must not reach the client (comments, tracked changes, speaker notes, slide footers, metadata, fill-in fields, notes to the writer or student, chatbot residue, tool marks, unrequested in-text citations, brief traps), checks the file against the brief, then writes a clean copy. Triggers on "ready to deliver", "check before sending", "قبل التسليم", "نظّف الملف", "راجع الملف للتسليم".
version: '0.3.0'
---

# Deliverable check

A delivered file carries only what the brief asked for, in the brief's language, with nothing addressed to Dawood or to the student. The script does the deterministic work; the brief settles the rest.

Script: `${CLAUDE_PLUGIN_ROOT}/skills/deliverable-check/scripts/deliverable_check.py` (needs `lxml` and `pypdf`; install with `pip install --break-system-packages lxml pypdf` when the import fails). Written below as `SCRIPT`.

## Delivery policy

Dawood's standing defaults. Apply them without asking and list what changed in the final message.

- Comments, tracked changes (accepted), speaker notes, slide footer and date text, metadata: removed by `clean`. Author fields stay blank unless Dawood names an author.
- Fill-in fields are blanked and their label kept: `Student: [Full name] — ID [Student ID]` becomes `Student:`. The student writes his own details.
- Notes to the writer or student, tool and watermark marks, chatbot residue, markdown leftovers: deleted.
- In-text citations stay only when the brief requires them. Otherwise clean with `--strip-citations`; the reference list stays.
- The reference list follows the output language: an Arabic deliverable with an all-English reference list is a finding.
- Every trap word from the brief is gone.
- The delivered file is named with words separated by spaces or hyphens, in Arabic or English, with no underscores and no `.clean` suffix: `تقرير التدريب الميداني.docx`, `Asthma-Presentation.pptx`. A naming rule in the brief replaces this one and is followed exactly.

Ask Dawood only about: content the brief did not ask for, a reference list in the wrong language (it needs new sources), dense citations when citations are required, and long `ai_style` rewrites.

## Steps

1. **Load the brief.** Take the first that exists: a `brief.md` written by project-analyzer (attached, in the working folder, or pasted), the requirements already in the conversation, or the brief Dawood sends when asked once. Fill each field of `references/brief-format.md` from it. Done when every field holds a value or `unknown`. When no brief can be had, mark the brief checks skipped and continue with the file checks.

2. **Scan.** Run `python3 SCRIPT scan FILE... --find WORD` with one `--find` per trap word. Scan never edits. Done when every file has a report.

3. **Check against the brief.** Compare the file with each brief field: output language, length (slides, words, pages), required sections present, citation and reference rules, format (style guide, RTL, template). List anything present that the brief did not ask for as off-brief content. Done when each field is marked `match`, `mismatch` or `skipped`.

4. **Clean.** Run `python3 SCRIPT clean FILE --find WORD...`, adding `--strip-citations` (docx) when the brief does not require in-text citations and `--thin-citations` when it does. The original stays untouched. Done when `<name>.clean.<ext>` exists and its re-scan shows zero `auto` findings.

5. **Fix the rest on the clean copy.** Edit with the matching format skill (docx, pptx, xlsx, pdf). Policy items first, without asking: delete notes, tool marks, residue and trap words; blank fill-in fields the script could not reach (a field split across runs); remove citations in pptx, xlsx and pdf when the policy says so. Then put the ask items to Dawood in one message. For `ai_style` findings, read `references/humanizer-rules.md` and rewrite by its procedure. Done when each item is fixed or Dawood chose to keep it.

6. **Verify.** Re-run `scan` on the final file with the same `--find` words. Done when only items Dawood chose to keep remain. Save the final file under its delivery name (`-o NAME` on clean, or a renamed copy). Reply in one short message: the clean file, what the policy removed, the brief mismatches left, and the kept items.

7. **Lessons.** After the reply in step 6, check whether this run taught something the skill does not already say: a pattern the scan missed or flagged wrongly, an error you hit, a correction from Dawood, or a better approach. If it did, send one message titled `ملاحظات للمهارة` with at most 3 proposed edits, each as: the file (`SKILL.md`, `references/*.md`, or a rule in `scripts/deliverable_check.py`), the current line, the new text, and a one-line reason. Change nothing until Dawood answers. Apply only the approved edits to the `EngDawood/dawood-claude-skills` repo on main (files under `skills/deliverable-check/`) with the github-mcp tools (`gh_file_get`, then `gh_file_put` for one file or `gh_push_files` for several, in one commit). A script change also gets a case in `tests/run_tests.py`; run the tests first when a shell is available. When the github-mcp tools are not in the session, write each approved edit in the reply instead (file path, the exact old text, the exact new text) so Dawood can apply it. Done when the edits are pushed or written out, Dawood declined, or the run taught nothing new (then say nothing).

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
| format | manual | missing right-to-left direction, empty slides, error cells, blank pages |

The report also prints the reference list line (entries, Arabic, other) for docx and pptx.

Thresholds, regex coverage and known limits live in `references/checks.md`. Read it when a finding looks wrong or Dawood asks how a check works.
