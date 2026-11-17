# dawood-skills

A plugin marketplace for my skills. Each plugin lives in its own folder under `plugins/`.

العربية: [README.md](README.md)

## Plugins

| Plugin | Skills | What it does |
|---|---|---|
| freelance-tools | project-analyzer, deliverable-check | Analyzes a new project brief before work starts, and checks delivery files (docx, pptx, xlsx, pdf) before sending, then writes a clean copy. |
| google-forms-script-generator | google-forms-script-generator | Turns survey questions into an Apps Script that builds the Google Form. |
| user-docx | user-docx | Creates and edits Word files, including comments, tracked changes and Markdown to Word. |
| arabic-docx-pptx | doc-to-word-rtl, arabic-pptx | Arabic right-to-left Word and PowerPoint. Its skills are copied automatically from the source repos (see below). |
| find-oss-alternative | find-oss-alternative | Finds open-source alternatives to a product, tool or feature before building from scratch, with a Use / Borrow / Avoid / Build New recommendation. Its skill is copied automatically from the source repo. |

## Install

```
/plugin marketplace add EngDawood/dawood-claude-skills
/plugin install freelance-tools@dawood-skills
/plugin install google-forms-script-generator@dawood-skills
/plugin install user-docx@dawood-skills
/plugin install arabic-docx-pptx@dawood-skills
/plugin install find-oss-alternative@dawood-skills
```

## arabic-docx-pptx sync

`.github/workflows/sync-arabic-docx-pptx.yml` runs daily (and on demand from the Actions tab) and copies the two skills from:

- [claude-doc-to-docx-arabic](https://github.com/EngDawood/claude-doc-to-docx-arabic) into `skills/doc-to-word-rtl`
- [arabic-pptx-skill](https://github.com/EngDawood/arabic-pptx-skill) (the current name of the claude-slide-to-pptx-arabic repo) into `skills/arabic-pptx`

When something changed it commits to the default branch and bumps the patch version in `plugin.json`, because installed plugins only update on a new version. If `plugin.json` has no `version`, it adds 0.1.0. `SOURCES.md` records each source repo's version. Do not edit these two skills here; edit them in their source repos. Run locally with `.github/scripts/sync-arabic-docx-pptx.sh`.

## find-oss-alternative sync

`.github/workflows/sync-find-oss-alternative.yml` runs daily (and on demand from the Actions tab) and copies the skill from [lumpinif/find-oss-alternative](https://github.com/lumpinif/find-oss-alternative) into `skills/find-oss-alternative`, without the assets and docs folders (demo video and report page). Same mechanism as arabic-docx-pptx: commits to the default branch on change, bumps the patch version in `plugin.json`, and records the source version in `SOURCES.md`. Do not edit the skill here. Run locally with `.github/scripts/sync-find-oss-alternative.sh`.

## Brief scanner

```
python3 plugins/freelance-tools/skills/project-analyzer/scripts/scan_brief.py brief.pdf
```

Finds hidden text (white, tiny font, Word hidden text, off-slide shapes, image alt text, comments) and AI-directed phrases in Arabic and English, and extracts trap words. Supports docx, pptx, pdf, html, md and txt. Needs `pip install lxml pdfplumber`.

## Testing deliverable-check

```
pip install lxml pypdf python-docx python-pptx openpyxl
python3 tests/run_tests.py
```

The PDF case needs LibreOffice.

## License

MIT
