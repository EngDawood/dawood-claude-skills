# Writing the markdown (direct route)

The builder reads plain markdown. Everything before the first real `##` is the cover page; the builder lays it out (cover recipe in `docx-recipes.md`).

- **Cover**, top to bottom, one item per line:
  1. institution lines (المملكة العربية السعودية / وزارة التعليم / الجامعة / الكلية);
  2. `# Title`;
  3. fields as `**الطالبة:** الاسم` lines (a two-column `| البند | البيان |` table also works: it prints as the same lines);
  4. a closing date or year line.
  A field the user has not given keeps its label and an empty value (`**اسم المقرر:**`). Cover lines are content only: the builder adds no label, and a `## صفحة الغلاف` heading from a Claude Doc is dropped.
- **Body**: `##` for sections (they fill the contents page), `###` for subsections, numbered `1.1` when the client numbers headings.
- **Tables**: pipe tables, a caption line above (`جدول (1): …`), a `المصدر: …` line under one that has a source.
- **Equations** `$$…$$`; **page break** `---`; **pictures** `![alt](/abs/path.png)`; **references** under `## المراجع`, one entry per paragraph.
