# Writing the markdown (direct route)

The scripts read plain markdown. Everything before the first real `##` is the cover page; the script lays it out (see the *Cover page* row of the house-style table in SKILL.md).

- **Cover**, top to bottom, one item per line:
  1. institution lines (المملكة العربية السعودية / وزارة التعليم / الجامعة / الكلية);
  2. `# Title`;
  3. fields as `**الطالبة:** الاسم` lines (a two-column `| البند | البيان |` table also works: it prints as the same lines);
  4. a closing date or year line.
  A field the user has not given is a `[اسم المقرر]`-style placeholder. Cover lines are content only: the script adds no label, and a `## صفحة الغلاف` heading from a Claude Doc is dropped.
- **Body**: `##` for sections (they fill the contents page), `###` for subsections, numbered `1.1` when the client numbers headings.
- **Tables**: pipe tables, a caption line above (`جدول (1): …`), a `المصدر: …` line under one that has a source.
- **Equations** `$$…$$`; **page break** `---`; **pictures** `![alt](/abs/path.png)`; **references** under `## المراجع`, one entry per paragraph.
- **English** (`md_to_docx_en.py`): same shapes, no cover or contents page; title-page lines under `# Title` print as ordinary paragraphs.
