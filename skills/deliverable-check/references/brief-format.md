# brief.md format

project-analyzer writes this file when Dawood asks for it; deliverable-check reads it. The same template lives in `skills/project-analyzer/references/brief-format.md` in this repo, so change both together.

```markdown
# Brief: <project title>

- output_language: ar | en | mixed
- deliverables: <file types and counts, e.g. 1 pptx, 15 slides>
- length: <slides, words or pages, or unknown>
- required_sections: <list from the brief, in order>
- format: <style guide, RTL, template, font, cover page>
- in_text_citations: required | not required | unknown
- reference_list: required | not required | unknown
- reference_language: ar | en | any | unknown
- trap_words: <words or phrases planted by hidden instructions, or none>
- left_blank_for_student: <fields the student fills himself, e.g. name, ID, advisor>
- file_naming: <naming rule from the brief, e.g. StudentID_Name.docx, or none>
- extras_not_wanted: <anything the brief or Dawood ruled out>
```

## Reading rules

- `unknown` on a field skips the matching check and the report says so.
- `in_text_citations: unknown` keeps citations; ask Dawood once whether to strip them.
- `reference_language: unknown` follows `output_language`.
- `file_naming: none` means spaces or hyphens between words, no underscores. A rule replaces that default exactly.
- `trap_words` become `--find` arguments for every scan and clean.
- Fields in `left_blank_for_student` are expected to be blank labels in the final file.
