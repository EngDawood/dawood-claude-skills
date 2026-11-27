# dawood-skills

ماركت بليس بلوقنز مهاراتي. كل بلوقن في مجلد تحت `plugins/`.

English: [README.en.md](README.en.md)

## البلوقنز

| البلوقن | المهارات | ماذا يفعل |
|---|---|---|
| freelance-tools | project-analyzer, deliverable-check | تحليل مطلوب المشروع قبل التنفيذ، وفحص ملفات التسليم (docx وpptx وxlsx وpdf) قبل إرسالها وكتابة نسخة نظيفة. |
| google-forms-script-generator | google-forms-script-generator | تحويل أسئلة استبيان إلى سكربت Apps Script يبني Google Form. |
| user-docx | user-docx | إنشاء ملفات Word وتعديلها، مع التعليقات والتعديلات المتتبعة وتحويل Markdown إلى Word. |
| arabic-docx-pptx | arabic-docx, english-docx, arabic-pptx | وورد عربي وإنجليزي وبوربوينت عربي. تُنسخ مهاراته تلقائياً من ريبو المصدر (انظر أدناه). |
| find-oss-alternative | find-oss-alternative | البحث عن بدائل مفتوحة المصدر لمنتج أو أداة أو ميزة قبل البناء من الصفر، مع توصية: استخدم / استعر / تجنّب / ابنِ جديداً. تُنسخ مهارته تلقائياً من ريبو المصدر. |
| steal-the-code | steal-the-code | الاسم القديم لـ find-oss-alternative (ريبو المصدر يعلن أنه لم يعد المرجع المحدَّث). تُنسخ مهارته تلقائياً. |
| wokwi-arduino-project | wokwi-arduino-project | بناء محاكاة Wokwi وكود Arduino ودليل توصيل العتاد الحقيقي من جدول منافذ واحد، فتتطابق الثلاثة دائماً. |

## التثبيت

```
/plugin marketplace add EngDawood/dawood-claude-skills
/plugin install freelance-tools@dawood-skills
/plugin install google-forms-script-generator@dawood-skills
/plugin install user-docx@dawood-skills
/plugin install arabic-docx-pptx@dawood-skills
/plugin install find-oss-alternative@dawood-skills
/plugin install steal-the-code@dawood-skills
/plugin install wokwi-arduino-project@dawood-skills
```

## مزامنة arabic-docx-pptx

الملف `.github/workflows/sync-arabic-docx-pptx.yml` يعمل يومياً (ويدوياً من تبويب Actions) وينسخ كل المهارات من ريبو واحد: [arabic-docx-pptx-skills](https://github.com/EngDawood/arabic-docx-pptx-skills) (فرع main) إلى `plugins/arabic-docx-pptx/skills`.

إن تغيّر شيء يرفع commit على الفرع الرئيسي ويأخذ رقم الإصدار من `plugin.json` في ريبو المصدر (ارفعه هناك عند كل تغيير، لأن تحديث البلوقن عند المستخدمين يحتاج رقماً جديداً). ويسجّل في `SOURCES.md` نسخة المصدر. لا تعدّل المهارات هنا، عدّلها في ريبو المصدر. التشغيل محلياً: `.github/scripts/sync-arabic-docx-pptx.sh`.

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
