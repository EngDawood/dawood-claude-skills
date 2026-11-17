# dawood-skills

ماركت بليس بلوقنز مهاراتي. كل بلوقن في مجلد تحت `plugins/`.

English: [README.en.md](README.en.md)

## البلوقنز

| البلوقن | المهارات | ماذا يفعل |
|---|---|---|
| freelance-tools | project-analyzer, deliverable-check | تحليل مطلوب المشروع قبل التنفيذ، وفحص ملفات التسليم (docx وpptx وxlsx وpdf) قبل إرسالها وكتابة نسخة نظيفة. |
| google-forms-script-generator | google-forms-script-generator | تحويل أسئلة استبيان إلى سكربت Apps Script يبني Google Form. |
| user-docx | user-docx | إنشاء ملفات Word وتعديلها، مع التعليقات والتعديلات المتتبعة وتحويل Markdown إلى Word. |
| arabic-docx-pptx | doc-to-word-rtl, arabic-pptx | وورد وبوربوينت بالعربي من اليمين لليسار. تُنسخ مهاراته تلقائياً من ريبوهات المصدر (انظر أدناه). |
| find-oss-alternative | find-oss-alternative | البحث عن بدائل مفتوحة المصدر لمنتج أو أداة أو ميزة قبل البناء من الصفر، مع توصية: استخدم / استعر / تجنّب / ابنِ جديداً. تُنسخ مهارته تلقائياً من ريبو المصدر. |
| steal-the-code | steal-the-code | الاسم القديم لـ find-oss-alternative (ريبو المصدر يعلن أنه لم يعد المرجع المحدَّث). تُنسخ مهارته تلقائياً. |

## التثبيت

```
/plugin marketplace add EngDawood/dawood-claude-skills
/plugin install freelance-tools@dawood-skills
/plugin install google-forms-script-generator@dawood-skills
/plugin install user-docx@dawood-skills
/plugin install arabic-docx-pptx@dawood-skills
/plugin install find-oss-alternative@dawood-skills
/plugin install steal-the-code@dawood-skills
```

## مزامنة arabic-docx-pptx

الملف `.github/workflows/sync-arabic-docx-pptx.yml` يعمل يومياً (ويدوياً من تبويب Actions) وينسخ المهارتين من:

- [claude-doc-to-docx-arabic](https://github.com/EngDawood/claude-doc-to-docx-arabic) إلى `skills/doc-to-word-rtl`
- [arabic-pptx-skill](https://github.com/EngDawood/arabic-pptx-skill) (الاسم الحالي للريبو claude-slide-to-pptx-arabic) إلى `skills/arabic-pptx`

إن تغيّر شيء يرفع commit على الفرع الرئيسي ويزيد رقم الإصدار (patch) في `plugin.json`، لأن تحديث البلوقن عند المستخدمين يحتاج رقماً جديداً. وإن لم يجد `version` في `plugin.json` أضافه (0.1.0). ويسجّل في `SOURCES.md` نسخة كل ريبو مصدر. لا تعدّل المهارتين هنا، عدّلهما في ريبو المصدر. التشغيل محلياً: `.github/scripts/sync-arabic-docx-pptx.sh`.

## مزامنة find-oss-alternative

الملف `.github/workflows/sync-find-oss-alternative.yml` يعمل يومياً (ويدوياً من تبويب Actions) وينسخ المهارة من [lumpinif/find-oss-alternative](https://github.com/lumpinif/find-oss-alternative) إلى `skills/find-oss-alternative`، دون مجلدي assets وdocs (فيديو العرض وصفحة التقرير). نفس آلية arabic-docx-pptx: commit على الفرع الرئيسي عند التغيير، ورفع رقم patch في `plugin.json`، وتسجيل النسخة في `SOURCES.md`. لا تعدّل المهارة هنا. التشغيل محلياً: `.github/scripts/sync-find-oss-alternative.sh`.

## مزامنة steal-the-code

نفس آلية find-oss-alternative بالضبط: `.github/workflows/sync-steal-the-code.yml` ينسخ المهارة يومياً من [lumpinif/steal-the-code](https://github.com/lumpinif/steal-the-code) إلى `skills/steal-the-code`. لا تعدّلها هنا. التشغيل محلياً: `.github/scripts/sync-steal-the-code.sh`.

## فاحص الفخاخ

```
python3 plugins/freelance-tools/skills/project-analyzer/scripts/scan_brief.py المطلوب.pdf
```

يرصد النص المخفي (أبيض، خط صغير جداً، نص Word المخفي، أشكال خارج الشريحة، النص البديل للصور، التعليقات) والعبارات الموجهة للذكاء الاصطناعي بالعربي والإنجليزي، ويستخرج كلمات الفخ. يدعم docx وpptx وpdf وhtml وmd وtxt، ويحتاج `pip install lxml pdfplumber`.

## اختبار deliverable-check

```
pip install lxml pypdf python-docx python-pptx openpyxl
python3 tests/run_tests.py
```

حالة PDF تحتاج LibreOffice.

## الرخصة

MIT
