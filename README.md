# dawood-claude-skills

ماركت بليس بلوقنز مهاراتي. كل بلوقن في مجلد تحت `plugins/`.

English: [README.en.md](README.en.md)

## البلوقنز

| البلوقن | المهارات | ماذا يفعل |
|---|---|---|
| freelance-tools | project-analyzer, deliverable-check | تحليل مطلوب المشروع قبل التنفيذ، وفحص ملفات التسليم (docx وpptx وxlsx وpdf) قبل إرسالها وكتابة نسخة نظيفة. |
| google-forms-script-generator | google-forms-script-generator | تحويل أسئلة استبيان إلى سكربت Apps Script يبني Google Form. |
| user-docx | user-docx | إنشاء ملفات Word وتعديلها، مع التعليقات والتعديلات المتتبعة وتحويل Markdown إلى Word. |
| arabic-docx-pptx | doc-to-word-rtl, arabic-pptx | وورد وبوربوينت بالعربي من اليمين لليسار. تُنسخ مهاراته تلقائياً من ريبوهات المصدر (انظر أدناه). |

## التثبيت

```
/plugin marketplace add EngDawood/dawood-claude-skills
/plugin install freelance-tools@dawood-claude-skills
/plugin install google-forms-script-generator@dawood-claude-skills
/plugin install user-docx@dawood-claude-skills
/plugin install arabic-docx-pptx@dawood-claude-skills
```

## مزامنة arabic-docx-pptx

الملف `.github/workflows/sync-arabic-docx-pptx.yml` يعمل يومياً (ويدوياً من تبويب Actions) وينسخ المهارتين من:

- [claude-doc-to-docx-arabic](https://github.com/EngDawood/claude-doc-to-docx-arabic) إلى `skills/doc-to-word-rtl`
- [arabic-pptx-skill](https://github.com/EngDawood/arabic-pptx-skill) (الاسم الحالي للريبو claude-slide-to-pptx-arabic) إلى `skills/arabic-pptx`

إن تغيّر شيء يرفع commit على الفرع الرئيسي ويزيد رقم الإصدار (patch) في `plugin.json`، لأن تحديث البلوقن عند المستخدمين يحتاج رقماً جديداً. لا تعدّل المهارتين هنا، عدّلهما في ريبو المصدر. التشغيل محلياً: `.github/scripts/sync-arabic-docx-pptx.sh`.

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
