# خريطة الأدوات: من ينفذ كل جزء

جدول مرجعي لما يقدر Claude ينتجه وما يحتاج داوود أو الطالب. هو نسخة محفوظة من خبرة سابقة وليس مصدر الحقيقة: أي برنامج غير موجود هنا، أو موجود بعلامة «تحقق»، ابحث عنه وقت التحليل بـ `SearchMcpRegistry` واسم البرنامج، وانظر الموصلات المتصلة فعلاً في الجلسة.

## أين يعمل Claude

| المكان | يقدر | لا يقدر |
|---|---|---|
| Claude (هذه المحادثة) | مساحة عمل سحابية Linux فيها Python وNode وLibreOffice، Artifacts (Docs وSlides وSheets وDesign)، مهارات docx وpptx وxlsx وpdf، الموصلات المتصلة (Google Drive وDocs وSheets وSlides وGmail وCanva وGitHub)، البحث | تشغيل برامج Windows، الوصول لملفات جهازك إلا عبر جسر الجهاز |
| Claude Code على اللابتوب | بناء وتشغيل كود حقيقي على Windows: Flutter وAndroid SDK وNode وقواعد بيانات محلية، الريبوهات | البرامج ذات الواجهة فقط |
| Claude Desktop (computer use) | تشغيل برامج سطح المكتب المثبتة على جهازك بالنقر والكتابة: MS Project وSPSS وPower BI وPacket Tracer | بطيء ويحتاج البرنامج مثبتاً ومفتوحاً وجهازك شغّالاً، فيصلح لخطوات قصيرة مثل التصدير والتقاط الشاشات |

## حسب البرنامج أو المخرج

| المخرج | Claude ينتج | موصل / MCP | عليك أنت |
|---|---|---|---|
| Word وPowerPoint وExcel وPDF | الملف كاملاً (مهارات docx وpptx وxlsx وpdf، أو Docs وSlides وSheets ثم تصدير) | لا يلزم | مراجعة الخط العربي في Office |
| Google Docs وSheets وSlides | الملف مباشرة في Drive | متصل | لا شيء |
| Google Forms | سكربت Apps Script (مهارة google-forms-script-generator) | لا يوجد للنماذج | تشغيل السكربت في script.google.com |
| MS Project (.mpp) | ملف MSPDI XML يفتحه MS Project، أو جدول Excel للاستيراد، وخطة المهام والمدد والاعتماديات | لا يوجد (تحقق) | فتح الـ XML في MS Project، حفظه mpp، لقطات Gantt؛ أو Claude Desktop يفعلها |
| Power BI (.pbix) | تنظيف البيانات، النموذج، مقاييس DAX، تصميم الصفحات مكتوباً، أو Dashboard artifact بديل | لا يوجد لبناء pbix (تحقق) | بناء الصفحات في Power BI Desktop وتصدير pbix وPDF |
| SPSS | التحليل نفسه بـ Python بجداول بصيغة SPSS، ملف sav عبر pyreadstat، وسكربت sps | لا يوجد | تشغيل SPSS إذا طُلبت مخرجات spv أو لقطات SPSS |
| MATLAB وSimulink | سكربتات m، وسكربت يبني نموذج Simulink بأوامر add_block | لا يوجد | تشغيل MATLAB وحفظ slx ولقطات المخرجات |
| Packet Tracer (.pkt) | جدول العناوين وأوامر الإعداد لكل جهاز خطوة بخطوة | لا يوجد | بناء الشبكة في Packet Tracer وحفظ pkt |
| Proteus وMultisim وTinkercad | قائمة القطع، التوصيلات، كود Arduino | لا يوجد | بناء الدائرة والمحاكاة واللقطات |
| Logisim (.circ) | الملف نفسه (XML) | لا يلزم | فتحه للتأكد واللقطات |
| AutoCAD وSolidWorks | رسم ثنائي الأبعاد DXF عبر ezdxf | لا يوجد | الرسم ثلاثي الأبعاد والصيغ الأصلية |
| مخططات (ERD وUML وflowchart) | draw.io XML (مهارة drawio أو موصل mcp_draw) أو Mermaid | متصل | لا شيء |
| تصميم UI وموكب | Design artifact أو Subframe | Subframe متصل؛ Figma (تحقق) | لا شيء |
| Canva | تصميم عبر الموصل | Canva متصل ويحتاج تسجيل دخول | تسجيل الدخول أول مرة |
| Flutter وAndroid (APK) | الكود كاملاً | لا يلزم | البناء على اللابتوب (Claude Code) لأن مساحة العمل السحابية بلا Android SDK |
| موقع ويب | صفحة HTML منشورة artifact، أو كود ريبو | GitHub متصل | النشر على استضافة العميل |
| MySQL وSQL | السكيما والاستعلامات وتشغيلها في مساحة العمل | لا يلزم | لقطات من MySQL Workbench إذا طُلبت |
| LaTeX وOverleaf | ملفات tex | لا يوجد لـ Overleaf | الرفع على Overleaf والتجميع النهائي |
| فيديو | فيديو كامل (مهارة video-making) وتعليق صوتي (ElevenLabs يحتاج تسجيل دخول) | ElevenLabs (تحقق) | التسجيل بصوتك إن طُلب |
| تسجيل شاشة لتطبيق حقيقي | سكربت التسجيل والخطوات | لا يوجد | التسجيل بحساب حقيقي |

## ما لا يقدر عليه Claude أبداً

يذهب لعمود «الطالب» في الخطة، ويُترك في الملف كعنوان فارغ:

- الاسم والرقم الجامعي واسم المشرف والتوقيع والختم.
- توزيع الاستبيان على أشخاص حقيقيين وجمع الردود، والمقابلات والملاحظة الميدانية.
- الرفع على Blackboard أو نظام الجامعة، وفحص Turnitin بحساب الطالب.
