// يقرأ data/snapshot.json ويعرض اللقطة كاملة. لا يوجد أي خادم خلفي.
fetch("data/snapshot.json", { cache: "no-store" })
  .then((r) => r.json())
  .then(render)
  .catch(() => {
    document.getElementById("freshness").textContent =
      "تعذر تحميل بيانات اللقطة (data/snapshot.json)";
  });

// لا يُعرض 100% أو 0% أبدًا: كل تقدير نموذج منتهٍ وقابل للخطأ، والتقريب لا يحوّله إلى يقين.
const PCT = (p) => {
  if (p == null) return "—";
  const v = p * 100;
  if (v >= 99.95) return ">99.9%";
  if (v <= 0.05) return "<0.1%";
  return v.toFixed(1) + "%";
};

function render(s) {
  const m = s.meta;
  document.getElementById("freshness").textContent =
    `لقطة ثابتة — آخر تحديث: ${m.generated_at_utc} · بيانات حتى ${m.to} · ${m.matches} مباراة`;

  document.getElementById("source-notes").innerHTML =
    m.notes.map((n) => `<li>${n}</li>`).join("");

  // المباريات القادمة
  const fx = document.getElementById("fixtures");
  if (!s.fixtures.length) {
    fx.innerHTML = `<div class="notice small">لا توجد مباريات قادمة في ملف الجدولة لدى المصدر بعد تاريخ آخر تحديث. تظهر الجولة التالية هنا فور نشر المصدر لها وتشغيل التحديث.</div>`;
  } else {
    fx.innerHTML = s.fixtures
      .map((f) => {
        const flags = [];
        if (f.low_team_data) flags.push("بيانات قليلة عن فريق");
        if (f.low_ref_data) flags.push("بيانات قليلة عن الحكم");
        const rows = Object.entries(f.probs)
          .map(([e, p]) => {
            const diff = Math.round((p.model - p.baseline) * 100);
            const diffTxt = diff === 0 ? "= خط الأساس" : (diff > 0 ? "+" : "") + diff + " نقطة عن خط الأساس";
            return `<div class="probrow">
              <span class="lbl">${s.events[e].label}</span>
              <span class="bar"><span style="width:${Math.round(p.model * 100)}%"></span></span>
              <span class="num">${PCT(p.model)}</span>
              <span class="sub">${diffTxt}</span>
            </div>`;
          })
          .join("");
        return `<div class="fixture-card">
          <div class="teams">${f.home} — ${f.away}</div>
          <div class="when">${f.date} · ${f.time} · الحكم: ${f.referee || "لم يُعلن"} (${f.ref_prior_matches} مباريات سابقة في العينة)</div>
          ${flags.length ? `<div class="flags">⚠ ${flags.join(" · ")} — تعامل مع التوقع بحذر إضافي</div>` : ""}
          ${rows}
          ${f.kickoff_passed === true
            ? `<div class="flags">⚠ عرض توضيحي استرجاعي: وُلّد هذا التقدير بعد موعد انطلاق المباراة المعلن (${f.kickoff_london || "غير معروف"})، فهو ليس توقعًا مسبقًا موثقًا ولن يدخل تقييم دقة المنصة. التوقعات الموثقة قبل الانطلاق تبدأ من الجولة القادمة.</div>`
            : f.kickoff_passed === false
              ? `<div class="sub">توقع محفوظ قبل الانطلاق (${f.kickoff_london}) ضمن لقطة ${m.generated_at_utc}؛ سيُقيَّم بالنتيجة الفعلية في التحديث التالي.</div>`
              : `<div class="sub">تقدير النموذج الحالي ضمن لقطة ${m.generated_at_utc}.</div>`}
        </div>`;
      })
      .join("");
  }

  // الأحداث
  document.getElementById("events").innerHTML = Object.entries(s.events)
    .map(([id, ev]) => {
      const badge = ev.descriptive
        ? `<span class="badge desc">وصفي فقط — لم يدخل التوقع بعد</span>`
        : `<span class="badge tested">مدروس توقعيًا</span>`;
      return `<div class="card">${badge}<h3>${ev.label}</h3>
        <div class="pct">${ev.pct}%</div>
        <div class="sub">حدث في ${ev.count} من ${ev.of} مباراة في العينة الحالية</div></div>`;
    })
    .join("");

  // قياس الدقة
  document.getElementById("metrics").innerHTML = `<div class="scroll-x"><table>
    <tr><th>الحدث</th><th>عدد مباريات الاختبار</th><th>تحقق فعليًا</th>
        <th>Brier خط الأساس</th><th>Brier النموذج</th><th>الفرق</th></tr>
    ${s.experiment
      .map((r) => {
        const d = r.brier_model - r.brier_baseline;
        const cls = d <= 0 ? "better" : "worse";
        const txt = d <= 0 ? "أفضل" : "أسوأ";
        return `<tr><td>${r.label}</td><td>${r.n}</td><td>${r.positives}</td>
          <td>${r.brier_baseline}</td><td>${r.brier_model}</td>
          <td class="${cls}">${txt}</td></tr>`;
      })
      .join("")}</table></div>`;
  document.getElementById("verdict").textContent =
    "الخلاصة الحالية بصراحة: على عينة الاختبار (38 مباراة) كان النموذج أسوأ من خط الأساس البسيط في 4 من 5 أحداث، وأفضل بهامش ضئيل في حدث شبه ثابت (وجود بطاقة صفراء). هذا لا يثبت أن العوامل عديمة الفائدة مطلقًا؛ يثبت أن النموذج الحالي على هذه العينة لا يضيف شيئًا موثوقًا. المنصة تعرض ذلك علنًا بدل إخفائه.";
}
