// يقرأ data/snapshot.json ويعرض اللقطة كاملة. لا يوجد أي خادم خلفي.
// Reads the static snapshot and renders it. No backend.

const I18N = {
  ar: {
    title: "كرة الأحداث",
    tagline: "منصة بحثية مفتوحة المصدر لتحليل أحداث مباريات كرة القدم وتوقعها",
    freshness: (m) => `لقطة ثابتة — آخر تحديث: ${m.generated_at_utc} · بيانات حتى ${m.to} · ${m.matches} مباراة`,
    disclaimer: `<strong>تنبيه:</strong> هذه المنصة بحثية تعليمية. تعرض احتمالات إحصائية لأحداث المباريات (أهداف، بطاقات، ركنيات) وتقيس دقتها علنًا. لا تعرض أسعار مراهنات، ولا توصيات مراهنة، ولا أي إرشاد مالي. لا توجد توقعات مؤكدة في الرياضة؛ كل نسبة معروضة هنا احتمال قابل للخطأ، وقسم «قياس الدقة» يوثّق أخطاء النموذج بوضوح.`,
    hFixtures: "المباريات القادمة",
    hintFixtures: "توقعات النموذج للمباريات المجدولة. أي توقع موثق قبل الانطلاق يُوسم بذلك صراحة مع وقت اللقطة، وأي تقدير وُلّد بعد موعد الانطلاق يُوسم «عرض توضيحي استرجاعي» ولا يدخل تقييم الدقة إطلاقًا.",
    hEvents: "الأحداث المُعرَّفة",
    hintEvents: "ستة أحداث قابلة للتحقق، مُعرَّفة تعريفًا تشغيليًا دقيقًا في الشيفرة المصدرية.",
    hMetrics: "قياس الدقة",
    hintMetrics: "تجربة زمنية: تدريب على أول ٧١ مباراة، تقييم على آخر ٣٨ مباراة لم تدخل التدريب. خط الأساس: توقع كل حدث بمتوسط تكراره حتى تلك اللحظة فقط، دون أي عوامل.",
    hRepro: "إعادة الإنتاج",
    hintRepro: `لا تنشر المنصة صفوفًا بمستوى المباراة الواحدة، لأن ذلك يعادل إعادة نشر بيانات المصدر الخام ولم نعثر على ترخيص صريح بإعادة نشرها. لتوليد تفاصيل كل مباراة محليًا: نزّل المستودع وشغّل <code>python3 src/build_db.py && python3 src/export_site.py</code> وستحصل على قاعدة البيانات كاملة على جهازك من المصدر الأصلي مباشرة.`,
    hLimits: "المصدر والحدود",
    verdict: "الخلاصة الحالية بصراحة: على عينة الاختبار (38 مباراة) كان النموذج أسوأ من خط الأساس البسيط في 4 من 5 أحداث، وأفضل بهامش ضئيل في حدث شبه ثابت (وجود بطاقة صفراء). هذا لا يثبت أن العوامل عديمة الفائدة مطلقًا؛ يثبت أن النموذج الحالي على هذه العينة لا يضيف شيئًا موثوقًا. المنصة تعرض ذلك علنًا بدل إخفائه.",
    footer: `شيفرة مفتوحة المصدر بترخيص MIT — <a href="https://github.com/kora-events-research/kora-events">المستودع على GitHub</a>. مشروع بحثي مستقل لا يتبع أي جهة رياضية أو تجارية.`,
    badgeTested: "مدروس توقعيًا",
    badgeDesc: "وصفي فقط — لم يدخل التوقع بعد",
    cardSub: (ev) => `حدث في ${ev.count} من ${ev.of} مباراة في العينة الحالية`,
    tbl: ["الحدث", "عدد مباريات الاختبار", "تحقق فعليًا", "Brier خط الأساس", "Brier النموذج", "الفرق"],
    better: "أفضل", worse: "أسوأ",
    noFixtures: "لا توجد مباريات قادمة في ملف الجدولة لدى المصدر بعد تاريخ آخر تحديث. تظهر الجولة التالية هنا فور نشر المصدر لها وتشغيل التحديث.",
    referee: (f) => `الحكم: ${f.referee || "لم يُعلن"} (${f.ref_prior_matches} مباريات سابقة في العينة)`,
    flagLowTeam: "بيانات قليلة عن فريق",
    flagLowRef: "بيانات قليلة عن الحكم",
    flagCareful: "تعامل مع التوقع بحذر إضافي",
    retro: (f) => `⚠ عرض توضيحي استرجاعي: وُلّد هذا التقدير بعد موعد انطلاق المباراة المعلن (${f.kickoff_london || "غير معروف"})، فهو ليس توقعًا مسبقًا موثقًا ولن يدخل تقييم دقة المنصة. التوقعات الموثقة قبل الانطلاق تبدأ من الجولة القادمة.`,
    saved: (f, m) => `توقع محفوظ قبل الانطلاق (${f.kickoff_london}) ضمن لقطة ${m.generated_at_utc}؛ سيُقيَّم بالنتيجة الفعلية في التحديث التالي.`,
    current: (m) => `تقدير النموذج الحالي ضمن لقطة ${m.generated_at_utc}.`,
    eqBase: "= خط الأساس",
    ptsVsBase: "نقطة عن خط الأساس",
    limits: [
      `البيانات: ملف موسمي من <a href="https://football-data.co.uk/">Football-Data.co.uk</a> (تجميع رجعي للنتائج). لا نعيد نشر ملف البيانات الخام؛ الشيفرة تنزّله من مصدره مباشرة.`,
      "المنصة لقطة ثابتة تُحدَّث دوريًا (وليست بثًا حيًا). تاريخ آخر تحديث معروض أعلى الصفحة دائمًا.",
      "العينة صغيرة (109 مباريات، موسم واحد، دوري واحد)، والنتائج قابلة للتغير مع تراكم البيانات.",
      "هذا بحث مفتوح للفهم والتجربة، وليس نظام تنبؤ مكتملًا أو مضمونًا.",
    ],
    notesEn: null, // ملاحظات المصدر تبقى عربية من اللقطة
    toggle: "English",
    dir: "rtl",
  },
  en: {
    title: "Kora Events",
    tagline: "Open-source research platform for football match-event analytics",
    freshness: (m) => `Fixed snapshot — last updated: ${m.generated_at_utc} · data through ${m.to} · ${m.matches} matches`,
    disclaimer: `<strong>Notice:</strong> this is a research and education platform. It shows statistical probabilities for match events (goals, cards, corners) and measures its accuracy openly. No betting odds, no betting advice, no financial guidance of any kind. There are no certain predictions in sport; every figure here is a fallible probability, and the accuracy section documents the model's errors plainly.`,
    hFixtures: "Upcoming fixtures",
    hintFixtures: "Model estimates for scheduled matches. A genuine pre-kickoff forecast is labeled as such with its snapshot time; anything generated after the listed kickoff is labeled a retrospective demo and never enters accuracy evaluation.",
    hEvents: "Defined events",
    hintEvents: "Six checkable events, each with a precise operational definition in the source code.",
    hMetrics: "Accuracy measurement",
    hintMetrics: "Time-ordered experiment: trained on the first 71 matches, evaluated on the final 38 that never entered training. Baseline: predict each event by its running average up to that moment, with no factors at all.",
    hRepro: "Reproduce locally",
    hintRepro: `The platform does not publish match-level rows, because that would effectively republish the source's raw data and we found no explicit redistribution license. To generate full per-match detail locally: download the repo and run <code>python3 src/build_db.py && python3 src/export_site.py</code>; the database is built on your machine directly from the original source.`,
    hLimits: "Sources and limits",
    verdict: "Honest bottom line: on the test split (38 matches) the model was worse than the simple baseline in 4 of 5 events, and marginally better on the near-constant yellow-card event. This does not prove the factors are useless; it proves the current model on this sample adds nothing reliable. The platform shows that openly instead of hiding it.",
    footer: `Open-source under the MIT license — <a href="https://github.com/kora-events-research/kora-events">GitHub repository</a>. An independent research project, not affiliated with any sporting or commercial body.`,
    badgeTested: "Evaluated",
    badgeDesc: "Descriptive only — not yet predicted",
    cardSub: (ev) => `Occurred in ${ev.count} of ${ev.of} matches in the current sample`,
    tbl: ["Event", "Test matches", "Occurred", "Brier baseline", "Brier model", "Delta"],
    better: "better", worse: "worse",
    noFixtures: "No upcoming fixtures in the source's schedule file beyond the last update date. The next round appears here once the source publishes it and the refresh runs.",
    referee: (f) => `Referee: ${f.referee || "not announced"} (${f.ref_prior_matches} prior matches in sample)`,
    flagLowTeam: "little team data",
    flagLowRef: "little referee data",
    flagCareful: "treat this estimate with extra care",
    retro: (f) => `⚠ Retrospective demo: this estimate was generated after the listed kickoff (${f.kickoff_london || "unknown"}), so it is not a documented pre-match forecast and does not enter the platform's accuracy evaluation. Genuine pre-kickoff forecasts start with the next round.`,
    saved: (f, m) => `Pre-kickoff forecast (${f.kickoff_london}) saved in snapshot ${m.generated_at_utc}; it will be evaluated against the actual result on the next refresh.`,
    current: (m) => `Current model estimate within snapshot ${m.generated_at_utc}.`,
    eqBase: "= baseline",
    ptsVsBase: "pts vs baseline",
    limits: [
      `Data: a season CSV from <a href="https://football-data.co.uk/">Football-Data.co.uk</a> (a retrospective results compilation). The raw file is not redistributed; the scripts download it from its source.`,
      "The platform is a periodically refreshed fixed snapshot, not a live feed. The last-update stamp is always shown at the top.",
      "Small sample (109 matches, one season, one league); results may shift as data accumulates.",
      "This is open research for understanding and experimentation, not a complete or guaranteed prediction system.",
    ],
    notesEn: [
      "A fixed snapshot timestamped at generation, not a live feed.",
      "Card counts are as recorded by Football-Data and differ from the official count in some matches.",
      "Upcoming-fixture estimates come from a model retrained on all 109 matches; held-out accuracy is documented in the accuracy section.",
    ],
    toggle: "عربي",
    dir: "ltr",
  },
};

const EVENT_LABEL_EN = {
  goal_any: "At least one goal in the match",
  btts: "Both teams score",
  over25: "Three or more goals in the match",
  yellow_any: "At least one yellow card (per this source)",
  red_any: "At least one red card (per this source)",
  corners_high: "Many corners (10 or more)",
};

let LANG = localStorage.getItem("kora-lang") || "ar";
let SNAP = null;

// لا يُعرض 100% أو 0% أبدًا: كل تقدير نموذج منتهٍ وقابل للخطأ.
const PCT = (p) => {
  if (p == null) return "—";
  const v = p * 100;
  if (v >= 99.95) return ">99.9%";
  if (v <= 0.05) return "<0.1%";
  return v.toFixed(1) + "%";
};

function applyLang() {
  const T = I18N[LANG];
  document.documentElement.lang = LANG;
  document.documentElement.dir = T.dir;
  document.title = LANG === "ar"
    ? "كرة الأحداث — منصة بحثية مفتوحة لتحليل مباريات كرة القدم"
    : "Kora Events — open-source football match-event research";
  document.getElementById("lang-toggle").textContent = T.toggle;
  document.getElementById("t-title").textContent = T.title;
  document.getElementById("t-tagline").textContent = T.tagline;
  document.getElementById("t-disclaimer").innerHTML = T.disclaimer;
  document.getElementById("t-h-fixtures").textContent = T.hFixtures;
  document.getElementById("t-hint-fixtures").textContent = T.hintFixtures;
  document.getElementById("t-h-events").textContent = T.hEvents;
  document.getElementById("t-hint-events").textContent = T.hintEvents;
  document.getElementById("t-h-metrics").textContent = T.hMetrics;
  document.getElementById("t-hint-metrics").textContent = T.hintMetrics;
  document.getElementById("t-h-repro").textContent = T.hRepro;
  document.getElementById("t-hint-repro").innerHTML = T.hintRepro;
  document.getElementById("t-h-limits").textContent = T.hLimits;
  document.getElementById("verdict").textContent = T.verdict;
  document.getElementById("t-footer").innerHTML = T.footer;
  if (SNAP) render(SNAP);
}

function evLabel(id, ev) {
  return LANG === "en" && EVENT_LABEL_EN[id] ? EVENT_LABEL_EN[id] : ev.label;
}

function render(s) {
  const m = s.meta;
  const T = I18N[LANG];
  document.getElementById("freshness").textContent = T.freshness(m);

  const notes = (LANG === "en" && T.notesEn) ? T.notesEn : m.notes;
  document.getElementById("limits-list").innerHTML =
    [...notes, ...T.limits].map((n) => `<li>${n}</li>`).join("");

  const fx = document.getElementById("fixtures");
  if (!s.fixtures.length) {
    fx.innerHTML = `<div class="notice small">${T.noFixtures}</div>`;
  } else {
    fx.innerHTML = s.fixtures
      .map((f) => {
        const flags = [];
        if (f.low_team_data) flags.push(T.flagLowTeam);
        if (f.low_ref_data) flags.push(T.flagLowRef);
        const rows = Object.entries(f.probs)
          .map(([e, p]) => {
            const diff = Math.round((p.model - p.baseline) * 100);
            const diffTxt = diff === 0 ? T.eqBase : (diff > 0 ? "+" : "") + diff + " " + T.ptsVsBase;
            return `<div class="probrow">
              <span class="lbl">${evLabel(e, s.events[e])}</span>
              <span class="bar"><span style="width:${Math.round(p.model * 100)}%"></span></span>
              <span class="num">${PCT(p.model)}</span>
              <span class="sub">${diffTxt}</span>
            </div>`;
          })
          .join("");
        const tail = f.kickoff_passed === true
          ? `<div class="flags">${T.retro(f)}</div>`
          : f.kickoff_passed === false
            ? `<div class="sub">${T.saved(f, m)}</div>`
            : `<div class="sub">${T.current(m)}</div>`;
        return `<div class="fixture-card">
          <div class="teams">${f.home} — ${f.away}</div>
          <div class="when">${f.date} · ${f.time} · ${T.referee(f)}</div>
          ${flags.length ? `<div class="flags">⚠ ${flags.join(" · ")} — ${T.flagCareful}</div>` : ""}
          ${rows}
          ${tail}
        </div>`;
      })
      .join("");
  }

  document.getElementById("events").innerHTML = Object.entries(s.events)
    .map(([id, ev]) => {
      const badge = ev.descriptive
        ? `<span class="badge desc">${T.badgeDesc}</span>`
        : `<span class="badge tested">${T.badgeTested}</span>`;
      return `<div class="card">${badge}<h3>${evLabel(id, ev)}</h3>
        <div class="pct">${ev.pct}%</div>
        <div class="sub">${T.cardSub(ev)}</div></div>`;
    })
    .join("");

  document.getElementById("metrics").innerHTML = `<div class="scroll-x"><table>
    <tr>${T.tbl.map((h) => `<th>${h}</th>`).join("")}</tr>
    ${s.experiment
      .map((r) => {
        const d = r.brier_model - r.brier_baseline;
        const cls = d <= 0 ? "better" : "worse";
        const txt = d <= 0 ? T.better : T.worse;
        return `<tr><td>${evLabel(r.event, r)}</td><td>${r.n}</td><td>${r.positives}</td>
          <td>${r.brier_baseline}</td><td>${r.brier_model}</td>
          <td class="${cls}">${txt}</td></tr>`;
      })
      .join("")}</table></div>`;
}

document.getElementById("lang-toggle").addEventListener("click", () => {
  LANG = LANG === "ar" ? "en" : "ar";
  localStorage.setItem("kora-lang", LANG);
  applyLang();
});

applyLang();
fetch("data/snapshot.json", { cache: "no-store" })
  .then((r) => r.json())
  .then((s) => { SNAP = s; render(s); })
  .catch(() => {
    document.getElementById("freshness").textContent =
      LANG === "ar" ? "تعذر تحميل بيانات اللقطة (data/snapshot.json)"
                    : "Could not load snapshot data (data/snapshot.json)";
  });
