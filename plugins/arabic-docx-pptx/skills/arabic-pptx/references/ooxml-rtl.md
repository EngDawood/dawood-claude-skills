# OOXML for right-to-left text

The RTL pass (step 4 of the skill) and the XML it writes.

## RTL pass

Open the .pptx as a zip and parse these parts with lxml (namespace
`a` = `http://schemas.openxmlformats.org/drawingml/2006/main`):
`ppt/slides/*.xml`, and unless the template must stay untouched,
`ppt/slideLayouts/*.xml`, `ppt/slideMasters/*.xml` and `ppt/presentation.xml`.
Write every other part back byte for byte.

- **Arabic text**: letters in U+0600–06FF, 0750–077F, 08A0–08FF, FB50–FDFF,
  FE70–FEFF. The deck is Arabic when its slides have at least as many Arabic
  paragraphs as Latin-only ones.
- **Each `a:p`** that has Arabic text (or has no Latin text, in an Arabic deck):
  `a:pPr` (created as the first child when missing) gets `rtl="1"`; with Arabic
  text and no `algn`, it gets `algn="r"` unless the paragraph sits in a shape
  with a `ph` placeholder (alignment comes from the layout); `algn="l"` becomes
  `algn="r"`.
- **Each `a:r` and `a:fld`** with Arabic text: `a:rPr` (first child) gets
  `lang="ar-SA"`; when it has an `a:latin` with a real face (not `+mn-lt`
  style theme refs), `a:cs` gets the same `typeface`, placed after `a:ea` or
  else after `a:latin`.
- **`a:bodyPr`** whose shape holds Arabic text: `rtlCol="1"`.
- **`a:tbl`** with Arabic text: `a:tblPr` (first child) gets `rtl="1"`, unless
  the columns were reversed by hand.
- **Masters and defaults**: in an Arabic deck, every `a:lvl1pPr`…`a:lvl9pPr`
  gets `rtl="1"`; `algn="l"` becomes `"r"`; with no `algn`, masters and
  `presentation.xml` get `algn="r"`.

**Warnings** (fix in the generator source, then regenerate): an Arabic
paragraph that starts with punctuation (`. ، ؛ : ! ؟ …`) before its first
letter; bidi control characters (U+200E, 200F, 202A–202E, 2066–2069) in the
text; presentation-form letters (U+FB50–FDFF, FE70–FEFF).

**Re-check**: run the same rules read-only on the written file and count every
place a rule would still change something. Done at 0 issues and 0 warnings.

## Paragraph

```xml
<a:p>
  <a:pPr algn="r" rtl="1"/>
  <a:r>
    <a:rPr lang="ar-SA" sz="1800" dirty="0">
      <a:latin typeface="Sakkal Majalla"/>
      <a:cs typeface="Sakkal Majalla"/>
    </a:rPr>
    <a:t>1.2 أهداف التدريب.</a:t>
  </a:r>
</a:p>
```

- `rtl="1"` on `<a:pPr>` is the direction. `algn="r"` is only the alignment;
  centered text keeps `algn="ctr"` and still needs `rtl="1"`.
- `<a:pPr>` is the first child of `<a:p>`; `<a:rPr>` is the first child of `<a:r>`.
- `lang="ar-SA"` selects Arabic shaping and proofing.
- `<a:cs>` is the face used for Arabic letters. It follows `<a:latin>` and
  `<a:ea>` inside `<a:rPr>`. Without it Arabic falls back to the theme's
  complex-script font.
- Under `rtl="1"`, `marL` and `indent` measure from the right (start) edge, so
  a bullet paragraph keeps `marL="342900" indent="-342900"` unchanged.

## Bullets and numbering

Native markers follow the paragraph direction automatically:

```xml
<a:pPr marL="342900" indent="-342900" algn="r" rtl="1">
  <a:buFont typeface="Arial"/><a:buChar char="•"/>
</a:pPr>
```

`<a:buAutoNum type="arabicPeriod"/>` gives 1. 2. 3.; `arabic2Minus` gives
Arabic-Indic digits. Multi-level numbers such as 1.2 are typed as text at the
start of the paragraph, in the same run or paragraph as the heading.

## Text body, table, master

- `<a:bodyPr rtlCol="1">` orders multi-column text boxes right to left.
- `<a:tblPr rtl="1">` puts the first column on the right. Cells stay in logical
  order in the XML.
- In `ppt/slideMasters/*.xml` (`<p:titleStyle>`, `<p:bodyStyle>`,
  `<p:otherStyle>`) and `<p:defaultTextStyle>` in `ppt/presentation.xml`, each
  `<a:lvlNpPr>` gets `algn="r" rtl="1"`, so new text typed in PowerPoint is
  right-to-left without per-paragraph attributes.

## Charts

A column chart reads right to left when the category axis is reversed:
`<c:catAx><c:scaling><c:orientation val="maxMin"/></c:scaling>`; the value axis
then draws on the right. Apply it when the categories are a sequence the
audience reads in order (years, quarters, steps).

## When a fault survives the RTL pass

| Symptom | Cause | Fix |
|---|---|---|
| Period at the start of one sentence | The string was typed with the period first | Retype in logical order |
| Characters or words reversed | Text was pre-reversed or reshaped for a non-bidi renderer | Regenerate from the plain Unicode string |
| Disconnected letters | Letter spacing set, or presentation-form characters (U+FE70 to U+FEFF) | Set spacing to 0; use plain Arabic letters (U+0600 block) |
| Number on the wrong side in one line only | Number and title sit in separate text boxes | Place the number box to the right of the title box, or merge into one paragraph |
| Boxes instead of letters | Font has no Arabic glyphs | Set a font from the Typography list on `<a:latin>` and `<a:cs>` |
