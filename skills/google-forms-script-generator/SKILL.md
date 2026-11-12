---
name: google-forms-script-generator
description: Convert a set of survey/questionnaire questions (in any language, any format, any source document) into a Google Apps Script (.gs) file that builds the equivalent Google Form. Use whenever the user wants questions turned into a Google Form script, mentions FormApp, .gs files, or asks to "convert this survey/questionnaire to a Google Form." This skill mirrors whatever structure, question types, numbering, and formatting the user's source material already has — it does not impose a fixed style, so use it any time regardless of how the input questions are written.
---

# Google Forms Script Generator

Turn a list of questions into working Google Apps Script (`FormApp`) code. The job is **translation, not editing** — the output should look like the user's own questions, just expressed as `.gs` code instead of prose.

## Core principle: mirror the source, don't impose a style

The single most important thing about this skill: it has no opinion on how questions "should" be written. Don't invent formatting rules (letter prefixes, numbering schemes, required-by-default, always-single-page, always 1–5 scales, etc.) and apply them to every form. Whatever the user's source document does, do that. Whatever it doesn't specify, leave unspecified/default rather than guessing a "best practice."

Concretely:
- If choices in the source aren't labeled `(a)`, `(b)`, don't add labels. If they already have `1)`, `-`, `•`, or nothing at all, keep it that way (Apps Script doesn't need any prefix for choices to work).
- If the source doesn't say a question is required, don't mark it required — leave Google Forms' own default. Only set `.setRequired(true/false)` when the source (or the user) actually says so.
- If the source has multiple pages/sections meant to break, use `addPageBreakItem()`. If it's meant to be one scrolling page, don't. Follow the source's structure — don't default to either.
- If the source uses a 1–7 scale, or 0–10, or custom labels, use exactly that. Don't normalize to 1–5.
- Preserve numbering exactly as given (or omit it, if the source doesn't number things) — don't renumber or insert numbers that weren't there.
- Preserve language and wording exactly. Never translate, paraphrase, or "clean up" question text.

When the source is genuinely ambiguous about something structural (e.g., you truly can't tell if a question allows one answer or several), ask a quick clarifying question rather than silently picking a convention. But most of the time the source is clear enough — err toward just converting what's there.

## Question type reference

Google Forms (via `FormApp`) supports more than multiple-choice/scale/paragraph. Use whichever type actually matches what the source is asking for:

| Source signals | Apps Script method |
|---|---|
| Pick exactly one option | `addMultipleChoiceItem()` |
| Pick one from a dropdown (source says "dropdown" or it's a long list of mutually exclusive options) | `addListItem()` |
| Pick one or more / "select all that apply" | `addCheckboxItem()` |
| Rating / agreement / frequency scale with numeric bounds | `addScaleItem()` |
| Grid of options, one answer per row | `addGridItem()` |
| Grid of options, multiple answers per row | `addCheckboxGridItem()` |
| Short free-text answer | `addTextItem()` |
| Long free-text / open-ended answer | `addParagraphTextItem()` |
| Date input | `addDateItem()` |
| Time input | `addTimeItem()` |
| File upload | `addFileUploadItem()` (requires a Workspace account — mention this if used) |
| Section divider / header text | `addSectionHeaderItem()` |
| Page break | `addPageBreakItem()` |
| Explanatory image | `addImageItem()` |

If the source doesn't explicitly name a type, infer it from the question's phrasing (e.g., "choose one," "check all that apply," "rate from X to Y," "explain in your own words") rather than defaulting to Multiple Choice for everything.

## Output structure

Every generated script needs this scaffolding — this part genuinely is fixed, because it's just what Apps Script requires to run and return something useful, not a stylistic choice:

```javascript
function createFormName() {
  var form = FormApp.create('Form Title');

  // form.setDescription(...) — only if the source has intro/description text
  // form.setConfirmationMessage(...) — only if the source has a closing/thank-you message

  // ...items go here, built from the source, in source order...

  var formUrl = form.getPublishedUrl();
  var formId = form.getId();
  var editUrl = form.getEditUrl();

  Logger.log('Form created successfully!');
  Logger.log('Form ID: ' + formId);
  Logger.log('Published URL: ' + formUrl);
  Logger.log('Edit URL: ' + editUrl);

  return { formUrl: formUrl, formId: formId, editUrl: editUrl };
}
```

- Name the function descriptively based on the survey's actual topic (e.g., `createCustomerFeedbackSurvey`, `createEventRegistrationForm`).
- Only call `setDescription` / `setConfirmationMessage` if the source actually has that content — don't invent intro/thank-you text.
- Build items in the same order they appear in the source.

## Workflow

1. **Read the source as-is.** Note: language(s) used, how choices are formatted, whether questions are numbered, which questions (if any) are marked required/optional, whether there are sections or pages, what scale ranges are used, any intro/closing text.
2. **Map each question to the closest matching item type** using the reference table above and the question's actual phrasing — not a fixed assumption.
3. **Generate the `.gs` code**, item by item, preserving wording, order, formatting, and language exactly. Only add structural elements (required flags, page breaks, prefixes) that the source itself specifies or the user explicitly asks for.
4. **If something is ambiguous** (can't tell single- vs multi-select, can't tell if a question is required, etc.), ask briefly instead of guessing — but don't ask about things the source already makes clear.
5. **Save and present**: write the `.gs` file to `/home/claude/`, copy to `/mnt/user-data/outputs/`, and present it. Don't generate a separate instructions/README file unless asked — the script is the deliverable.

## Example

### Source (as given by the user — no prefixes, mixed types, one page break, only one question marked optional)

```
Event Feedback Form

1. How did you hear about the event?
   - Social media
   - Friend/colleague
   - Company email
   - Other

2. Which sessions did you attend? (check all that apply)
   - Opening keynote
   - Workshop A
   - Workshop B
   - Networking lunch

--- next page ---

3. Rate the overall event, 0 (poor) to 10 (excellent)

4. Any suggestions for next time? (optional)
```

### Generated output

```javascript
function createEventFeedbackForm() {
  var form = FormApp.create('Event Feedback Form');

  // 1. How did you hear about the event?
  form.addMultipleChoiceItem()
    .setTitle('How did you hear about the event?')
    .setChoiceValues(['Social media', 'Friend/colleague', 'Company email', 'Other']);

  // 2. Which sessions did you attend? (check all that apply)
  form.addCheckboxItem()
    .setTitle('Which sessions did you attend?')
    .setChoiceValues(['Opening keynote', 'Workshop A', 'Workshop B', 'Networking lunch']);

  form.addPageBreakItem();

  // 3. Rate the overall event, 0-10
  form.addScaleItem()
    .setTitle('Rate the overall event')
    .setBounds(0, 10)
    .setLabels('Poor', 'Excellent');

  // 4. Suggestions (explicitly optional in source)
  form.addParagraphTextItem()
    .setTitle('Any suggestions for next time?')
    .setRequired(false);

  var formUrl = form.getPublishedUrl();
  var formId = form.getId();
  var editUrl = form.getEditUrl();

  Logger.log('Form created successfully!');
  Logger.log('Form ID: ' + formId);
  Logger.log('Published URL: ' + formUrl);
  Logger.log('Edit URL: ' + editUrl);

  return { formUrl: formUrl, formId: formId, editUrl: editUrl };
}
```

Notice what's absent compared to a "standard template": no `(a)/(b)/(c)` prefixes (source didn't have them), no blanket `.setRequired(true)` (source didn't say most were required), a page break exists because the source had one, the scale is 0–10 because that's what was asked for, and question 1 has no explicit required/optional call since the source didn't specify.

## If the user gives explicit instructions

If the user *does* ask for something specific — "add letter prefixes," "make everything required," "keep it to one page," "use a 1–5 scale for all ratings" — follow that instruction for that request. The point of this skill isn't to forbid those choices, it's to not apply them automatically when nobody asked for them.

## Common mistakes to avoid

1. **Adding formatting the source doesn't have** — prefixes, numbering, required flags, page breaks — "because that's how forms are usually done."
2. **Defaulting every rating question to a 1–5 scale** without checking what range the source actually specifies.
3. **Assuming Multiple Choice for everything** instead of checking whether the question is really a checkbox, dropdown, grid, or free-text question.
4. **Translating or rewording** question text, even slightly.
5. **Inventing intro/closing text** that isn't in the source.
6. **Creating extra files** (instructions, READMEs) the user didn't ask for.

## Technical notes

- Uses the `FormApp` service — runs in [script.google.com](https://script.google.com) or any Apps Script project.
- The user runs the generated function manually in the Apps Script editor and grants form-creation permissions on first run.
- `addFileUploadItem()` requires the form owner to have a Google Workspace account — flag this if the source calls for file uploads.
- Output URLs are written to the execution log (`Logger.log`) and also returned from the function for programmatic use.
- Arabic and other RTL/Unicode text work natively in Apps Script strings and render correctly in Google Forms — no transliteration, encoding, or special string handling needed. Just pass the text through as-is, same as any other language.
