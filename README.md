# dawood-claude-skills

مهاراتي اليومية في العمل الحر، مجمّعة في بلوقن واحد اسمه `freelance-tools`.

English: [README.en.md](README.en.md)

## المهارات

| المهارة | ماذا تفعل |
|---|---|
| project-analyzer | تحلل مطلوب أي مشروع جديد: المخرجات، خطة التنفيذ (من ينفذ كل جزء: Claude هنا، Claude Code، Claude Desktop، أنا، أو الطالب، وبأي أداة أو موصل)، الفخاخ المخفية الموجهة للذكاء الاصطناعي، المشاريع السابقة المشابهة، تقدير الوقت، ورد واتساب جاهز. تكتب `brief.md` عند الطلب لتقرأه مهارة [deliverable-check](#deliverable-check) قبل التسليم. |
| deliverable-check | يفحص ملفات التسليم (docx وpptx وxlsx وpdf) قبل إرسالها: يحذف التعليقات والتعديلات المتتبعة وملاحظات المتحدث والتذييل والبيانات الوصفية وحقول التعبئة، ويرصد الملاحظات الموجهة للكاتب أو الطالب وبقايا الشات بوت وعلامات الأدوات والاستشهادات غير المطلوبة وكلمات الفخ، ويقارن الملف بالمطلوب، ثم يكتب نسخة نظيفة. |
| google-forms-script-generator | تحوّل أسئلة استبيان إلى سكربت Apps Script يبني Google Form. |
| user-docx | إنشاء ملفات Word وتعديلها. |

## التثبيت

```
/plugin marketplace add EngDawood/dawood-claude-skills
/plugin install freelance-tools@dawood-claude-skills
```

## فاحص الفخاخ

```
python3 skills/project-analyzer/scripts/scan_brief.py المطلوب.pdf
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
