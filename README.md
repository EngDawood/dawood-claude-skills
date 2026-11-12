# dawood-claude-skills

مهاراتي اليومية في العمل الحر، مجمّعة في بلوقن واحد اسمه `freelance-tools`.

English: [README.en.md](README.en.md)

## المهارات

| المهارة | ماذا تفعل |
|---|---|
| project-analyzer | تحلل مطلوب أي مشروع جديد: المخرجات، خطة التنفيذ (من ينفذ كل جزء: Claude هنا، Claude Code، Claude Desktop، أنا، أو الطالب، وبأي أداة أو موصل)، الفخاخ المخفية الموجهة للذكاء الاصطناعي، المشاريع السابقة المشابهة، تقدير الوقت، ورد واتساب جاهز. تكتب `brief.md` عند الطلب لتقرأه مهارة [deliverable-check](https://github.com/EngDawood/deliverable-check) قبل التسليم. |
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

## الرخصة

MIT
