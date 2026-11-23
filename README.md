# كرة الأحداث — نموذج بحثي مفتوح لتحليل أحداث مباريات كرة القدم

**English summary below.**

منصة ويب بحثية مفتوحة المصدر تعرض احتمالات أحداث المباريات (أهداف، بطاقات، ركنيات)
وتقيس دقتها علنًا. **ليست خدمة مراهنات**: لا أسعار، لا توصيات مراهنة، لا إرشاد مالي.

## ما الذي تعرضه المنصة؟

- توقعات ستة أحداث مُعرَّفة تعريفًا تشغيليًا دقيقًا (خمسة تدخل تجربة التوقع، وسادس وصفي).
- قياس دقة زمني صارم: تدريب على المباريات الأولى وتقييم على مباريات لاحقة لم تدخل التدريب، مقابل خط أساس بسيط.
- توقعات المباريات القادمة محفوظة كما هي قبل الانطلاق، وتُقيَّم بالنتيجة الفعلية عند التحديث التالي.
- أعلام كفاية البيانات: تنبيه عندما تكون بيانات الفريق أو الحكم قليلة.

## التشغيل محليًا

المتطلبات: Python 3.10+ مع `pandas` و`numpy`.

```bash
python3 src/build_db.py      # ينزّل ملف المصدر ويبني قاعدة البيانات
python3 src/export_site.py   # يولّد data/snapshot.json الذي يغذي الموقع
```

الموقع نفسه صفحة ثابتة (`index.html`) تقرأ `data/snapshot.json` فقط.
لا يوجد خادم خلفي؛ التحديث يعني إعادة توليد اللقطة.

## البيانات والترخيص

- مصدر البيانات: ملف CSV موسمي من [Football-Data.co.uk](https://football-data.co.uk/mmz4281/2627/E0.csv)
  (الدوري الإنجليزي الممتاز، موسم 2026/27). ملف الجدولة: `https://football-data.co.uk/fixtures.csv`.
- **لا يعاد نشر ملف البيانات الخام في هذا المستودع.** الشيفرة تنزّله من مصدره الأصلي،
  والموقع يعرض إحصاءات مشتقة فقط مع الإسناد. لم نعثر على ترخيص صريح بإعادة النشر،
  لذا التزمنا بالحد الأدنى الآمن.
- الشيفرة نفسها بترخيص MIT (انظر `LICENSE`).
- **لا يُشحن المستودع بأي ملف بيانات خام أو قاعدة بيانات جاهزة.** كل المخرجات (بما فيها
  قاعدة SQLite) تُبنى محليًا على جهازك بتشغيل السكربتات أعلاه، التي تنزّل البيانات من
  مصدرها الأصلي. من أراد حزمة بحثية كاملة يعيد بناءها محليًا بهذه الطريقة القانونية فقط.
- التوقعات الموثقة قبل الانطلاق تُوسم بذلك صراحة مع مقارنة فعلية بين وقت الانطلاق المعلن
  (بتوقيت بريطانيا) ولحظة توليد اللقطة؛ أي تقدير وُلّد بعد الموعد يُوسم «عرض توضيحي
  استرجاعي» ولا يدخل تقييم الدقة. ولا تُعرض أي احتمالات مقرّبة إلى 100% أو 0%، فكل
  تقدير نموذج منتهٍ وقابل للخطأ.
- تنبيه معروف: عدّ البطاقات في هذا المصدر يختلف عن العد الرسمي في بعض المباريات
  (موثق في قاموس الأحداث `src/event_dictionary.py`).

## الحدود العلمية (باختصار)

- العينة صغيرة: موسم واحد، دوري واحد، 109 مباريات.
- النموذج الحالي **لم يتفوق** على خط الأساس في 4 من 5 أحداث على جزء الاختبار — منشور علنًا على المنصة.
- المصدر تجميع رجعي؛ زمن نشر كل حقل غير موثق، لذا التحكم الزمني «ترتيب زمن الانطلاق» وليس ضمانًا ضد التسرب.

## البنية

```
index.html, assets/        صفحة ثابتة تقرأ اللقطة
src/build_db.py            تنزيل المصدر وبناء SQLite
src/features.py            عوامل ما قبل المباراة فقط (ترتيب زمن الانطلاق)
src/experiment.py          الأحداث + تجربة التقييم الزمني
src/export_site.py         توليد data/snapshot.json
src/event_dictionary.py    قاموس الأحداث الستة وتعريفاتها التشغيلية
.github/workflows/         تحديث مجدول للقطة (مرتين أسبوعيًا، توافقًا مع إيقاع المصدر)
```

---

## English

Open-source research platform for football match-event analytics. It publishes
probabilities for match events (goals, cards, corners) with transparent,
time-ordered accuracy measurement against a simple baseline. **Not a betting
service**: no odds, no tips, no financial guidance.

- Data: season CSV from Football-Data.co.uk (EPL 2026/27), downloaded by the
  script from its original source; raw data is **not** redistributed here —
  only derived aggregates with attribution, because we found no explicit
  redistribution license.
- Static snapshot site: `index.html` reads `data/snapshot.json`; there is no
  backend. "Update" means regenerating the snapshot (scheduled GitHub Action).
- Code: MIT license.

```bash
python3 src/build_db.py && python3 src/export_site.py
```
