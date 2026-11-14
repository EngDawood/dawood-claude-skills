# OOXML for right-to-left text

What `scripts/rtl_fix.py` writes, for applying by hand.

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

## When a fault survives the fixer

| Symptom | Cause | Fix |
|---|---|---|
| Period at the start of one sentence | The string was typed with the period first | Retype in logical order |
| Characters or words reversed | Text was pre-reversed or reshaped for a non-bidi renderer | Regenerate from the plain Unicode string |
| Disconnected letters | Letter spacing set, or presentation-form characters (U+FE70 to U+FEFF) | Set spacing to 0; use plain Arabic letters (U+0600 block) |
| Number on the wrong side in one line only | Number and title sit in separate text boxes | Place the number box to the right of the title box, or merge into one paragraph |
| Boxes instead of letters | Font has no Arabic glyphs | Set a font from the Typography list on `<a:latin>` and `<a:cs>` |
