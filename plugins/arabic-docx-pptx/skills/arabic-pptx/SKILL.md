---
name: arabic-pptx
description: >
  Builds and repairs Arabic right-to-left PowerPoint decks so direction,
  punctuation, numbering and tables render correctly. Use when the user asks
  for a presentation in Arabic ("عرض بوربوينت بالعربي", "برزنتيشن", "عرض تقديمي"),
  reports an Arabic .pptx whose sentence-final period or multi-level number
  (1.2) shows on the wrong side, or wants shapes, diagrams or SmartArt in an
  Arabic deck.
---

# Arabic PPTX

Generators (pptxgenjs, python-pptx, html2pptx) emit Arabic text as
`algn="r" rtl="0" lang="en-US"`: right-aligned, but still a left-to-right
paragraph. Under an LTR paragraph the bidi algorithm sends every neutral
character to the wrong side: the final period lands at the start of the
sentence, and "1.2 العنوان" shows the title before its number. The cure has two
halves, and both are required:

- **Logical order**: every string is typed in reading order, first word first,
  final punctuation last.
- **RTL paragraph**: every Arabic paragraph carries `rtl="1"`, so the renderer
  places neutrals correctly on its own.

## Steps

1. **Write the copy in logical order.** Type each string exactly as it is read
   aloud. A numbered heading is one paragraph, number first: `1.2 أهداف التدريب`.
   A sentence ends with its period as the last character. Keep the digits the
   user's source uses (Western 123 unless they wrote ١٢٣).
   Done when every string, read character by character, matches reading order.

2. **Lay the slide out mirrored.** Design right-to-left from the start, using
   the mirror table below.
   Done when every row of the mirror table holds for every slide.

3. **Generate the deck** with whichever tool the environment offers. Set RTL
   options where the tool has them (pptxgenjs: `rtlMode: true, align: 'right',
   lang: 'ar-SA'` on each text call); the next step is the guarantee either way.

4. **Run the fixer** on the generated file:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/arabic-pptx/scripts/rtl_fix.py" deck.pptx
   ```

   It sets `rtl="1"`, right alignment, `lang="ar-SA"`, the complex-script font
   and table direction on every Arabic paragraph, in slides, layouts and
   masters, then re-checks its own output. Resolve each `WARN` line by retyping
   that string in logical order in the generator source, then regenerate.
   Done when it prints `OK: 0 issues, 0 warnings`.

5. **Look at every slide.** Render (`soffice --headless --convert-to pdf`, then
   `pdftoppm -png -r 60`) and view each image. On each slide confirm: the period
   sits at the left end of its sentence, each number sits to the right of its
   heading, and the layout matches the mirror table.
   Done when every slide image has been viewed and passes all three.

To repair an existing Arabic deck, start at step 4. Add `--slides-only` when
the deck's master belongs to a template that must stay untouched, and
`--keep-table-order` when the table columns were already reversed by hand.
`--check` reports without writing.

## Mirror table

| Element | Arabic placement |
|---|---|
| Title, body text | Right edge, right-aligned |
| Bullets and numbers | Marker on the right of the text |
| Icon or number badge beside text | Right of the text |
| Text + visual split | Text right, visual left |
| Columns, cards, steps | First item rightmost, last leftmost |
| Process arrows, chevrons, timelines | Flow right to left, arrows point left |
| Table | First column rightmost (the fixer does this; write columns in logical order) |
| Slide number | Bottom-left |
| Logo | Top-left |
| Photos, charts' bar order, phone numbers, URLs, code | Unchanged |

## Typography

- **Font**: one the audience's machines have, with Arabic glyphs, set as both
  the Latin and complex-script face. Installed with Office: Sakkal Majalla,
  Dubai, Segoe UI, Tahoma, Arial. A web font (IBM Plex Sans Arabic, Cairo,
  Tajawal) is right only when the user confirms it is installed where the deck
  will be shown; PowerPoint files carry no fonts, and a fallback changes every
  line break.
- **Emphasis**: bold or color. Arabic has no italic or capitals.
- **Letter spacing**: 0. Tracking breaks the joins between letters.
- **Line height**: about 1.3x the font size; Arabic marks sit above and below
  the line.
- **Size**: Arabic reads smaller than Latin at the same point size; body 18pt
  or larger.

## Mixed Arabic and Latin

Keep `rtl="1"` on any paragraph that contains Arabic, including one that starts
or ends with an English term or a number; the renderer orders the pieces. A
paragraph that is entirely Latin (a URL, a code line) stays LTR. A range such
as `2024 - 2025` displays with 2024 on the right, which is the correct Arabic
reading order.

## References

- `references/ooxml-rtl.md`: the exact XML the fixer writes. Read when editing
  slide XML by hand, when Python is unavailable (for example inside the
  PowerPoint add-in), or when a renderer still shows a direction fault after
  the fixer reports OK.
- `references/shapes-and-diagrams.md`: read when the deck needs shapes, a
  process flow, a timeline, an org chart, or the user asks for SmartArt.
