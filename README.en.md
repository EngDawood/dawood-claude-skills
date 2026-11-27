# dawood-skills

A plugin marketplace for my skills. Each plugin lives in its own folder under `plugins/`.

العربية: [README.md](README.md)

## Plugins

| Plugin | Skills | What it does |
|---|---|---|
| freelance-tools | project-analyzer, deliverable-check | Analyzes a new project brief before work starts, and checks delivery files (docx, pptx, xlsx, pdf) before sending, then writes a clean copy. |
| google-forms-script-generator | google-forms-script-generator | Turns survey questions into an Apps Script that builds the Google Form. |
| user-docx | user-docx | Creates and edits Word files, including comments, tracked changes and Markdown to Word. |
| arabic-docx-pptx | arabic-docx, english-docx, arabic-pptx | Arabic and English Word and Arabic right-to-left PowerPoint. Its skills are copied automatically from the source repo (see below). |
| find-oss-alternative | find-oss-alternative | Finds open-source alternatives to a product, tool or feature before building from scratch, with a Use / Borrow / Avoid / Build New recommendation. Its skill is copied automatically from the source repo. |
| steal-the-code | steal-the-code | Legacy name of find-oss-alternative (the source repo says it is no longer the maintained entry point). Its skill is copied automatically. |
| wokwi-arduino-project | wokwi-arduino-project | Builds a Wokwi simulation, the Arduino sketch and the physical wiring guide from one pin map, so all three always match. |

## Install

```
/plugin marketplace add EngDawood/dawood-claude-skills
/plugin install freelance-tools@dawood-skills
/plugin install google-forms-script-generator@dawood-skills
/plugin install user-docx@dawood-skills
/plugin install arabic-docx-pptx@dawood-skills
/plugin install find-oss-alternative@dawood-skills
/plugin install steal-the-code@dawood-skills
/plugin install wokwi-arduino-project@dawood-skills
```

## arabic-docx-pptx sync

`.github/workflows/sync-arabic-docx-pptx.yml` runs daily (and on demand from the Actions tab) and copies all skills from one source repo, [arabic-docx-pptx-skills](https://github.com/EngDawood/arabic-docx-pptx-skills) (main branch), into `plugins/arabic-docx-pptx/skills`.

When something changed it commits to the default branch and takes the version from the source's `plugin.json` (bump it there on every change, because installed plugins only update on a new version). `SOURCES.md` records the source commit. Do not edit the skills here; edit them in the source repo. Run locally with `.github/scripts/sync-arabic-docx-pptx.sh`.

## find-oss-alternative sync

`.github/workflows/sync-find-oss-alternative.yml` runs daily (and on demand from the Actions tab) and copies the skill from [lumpinif/find-oss-alternative](https://github.com/lumpinif/find-oss-alternative) into `skills/find-oss-alternative`, without the assets and docs folders (demo video and report page). Same mechanism as arabic-docx-pptx: commits to the default branch on change, bumps the patch version in `plugin.json`, and records the source version in `SOURCES.md`. Do not edit the skill here. Run locally with `.github/scripts/sync-find-oss-alternative.sh`.

## steal-the-code sync

Same mechanism as find-oss-alternative: `.github/workflows/sync-steal-the-code.yml` copies the skill daily from [lumpinif/steal-the-code](https://github.com/lumpinif/steal-the-code) into `skills/steal-the-code`. Do not edit it here. Run locally with `.github/scripts/sync-steal-the-code.sh`.

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
