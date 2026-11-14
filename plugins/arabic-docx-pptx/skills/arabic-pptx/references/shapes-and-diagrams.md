# Shapes, diagrams and SmartArt in an Arabic deck

## Native shapes

Build diagrams from native shapes (rectangle, roundRect, ellipse, chevron,
homePlate, leftArrow, connectors), with the label inside the shape's own text
body. They stay editable in PowerPoint and their text obeys the same
`rtl="1"` rule as any paragraph; `rtl_fix.py` covers them.

- pptxgenjs: `slide.addShape(pptx.ShapeType.roundRect, {...})`, or
  `slide.addText(label, { shape: pptx.ShapeType.roundRect, rtlMode: true, ... })`
  to carry the label in the shape.
- python-pptx: `slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, ...)`, then
  write to `shape.text_frame`.
- PowerPoint add-in: `shapes.addGeometricShape(type, {left, top, width, height})`.

## Direction of flow

| Diagram | Arabic form |
|---|---|
| Process, steps | Step 1 rightmost; arrows point left (`leftArrow`, or `chevron`/`homePlate` with `flipH="1"`) |
| Timeline | Earliest date on the right |
| Org chart, pyramid, hierarchy | Top to bottom as usual; siblings ordered right to left |
| Cycle | Counter-clockwise, starting at the top |
| 2x2 matrix | Value axis labels on the right; the "high-high" cell top-left |
| Before / after | Before on the right, after on the left |

Size equal-weight shapes equally, space them evenly, and group each diagram so
it moves as one object.

## SmartArt

Generators cannot write real SmartArt objects; a SmartArt needs five linked
parts that only PowerPoint produces reliably. Two routes:

1. **Default**: build the same diagram from native shapes as above. Tell the
   user it is a shape-built diagram, editable shape by shape.
2. **When the user needs a true SmartArt** (to restyle it from the SmartArt
   gallery): put the items on the slide as a plain bulleted list, one item per
   paragraph, sub-items one level in, with `rtl="1"`. Then tell the user the two
   clicks: select the text box, Home > Convert to SmartArt (الصفحة الرئيسية >
   تحويل إلى SmartArt), pick a layout; if the order runs left to right, press
   SmartArt Design > Right to Left (تصميم SmartArt > من اليمين إلى اليسار).
