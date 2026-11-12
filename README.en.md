# dawood-claude-skills

My daily freelance skills, bundled as one plugin named `freelance-tools`.

Arabic: [README.md](README.md)

## Skills

| Skill | What it does |
|---|---|
| project-analyzer | Analyzes a new project brief: deliverables, an execution plan (who does each part: Claude here, Claude Code, Claude Desktop, me, or the student, and with which tool or connector), hidden AI-directed traps, similar past projects, a time estimate and a ready WhatsApp reply. Writes `brief.md` on request for [deliverable-check](#deliverable-check) to read before delivery. |
| deliverable-check | Checks deliverables (docx, pptx, xlsx, pdf) before sending: strips comments, tracked changes, speaker notes, footers, metadata and fill-in fields; flags notes to the writer or student, chatbot residue, tool marks, unrequested citations and trap words; compares the file with the brief; writes a clean copy. |
| google-forms-script-generator | Turns survey questions into an Apps Script that builds a Google Form. |
| user-docx | Create and edit Word documents. |

## Install

```
/plugin marketplace add EngDawood/dawood-claude-skills
/plugin install freelance-tools@dawood-claude-skills
```

## Trap scanner

```
python3 skills/project-analyzer/scripts/scan_brief.py brief.pdf
```

Finds hidden text (white, tiny font, Word hidden text, off-slide shapes, image alt text, comments) and AI-directed wording in Arabic and English, and extracts trap words. Supports docx, pptx, pdf, html, md and txt. Needs `pip install lxml pdfplumber`.

## Testing deliverable-check

```
pip install lxml pypdf python-docx python-pptx openpyxl
python3 tests/run_tests.py
```

The PDF case needs LibreOffice.

## License

MIT
