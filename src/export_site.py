#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_site.py - توليد data/snapshot.json الذي يغذي الموقع الثابت.

ينتج لقطة واحدة مختومة بوقت التوليد تشمل: تعريفات الأحداث وتكرارها،
نتائج التجربة الزمنية، توقعات كل مباراة سابقة (نموذج وخط أساس)،
وتوقعات المباريات القادمة من ملف fixtures لدى المصدر مع أعلام كفاية البيانات.

التشغيل: python3 src/export_site.py
"""
import csv
import io
import json
import pathlib
import sqlite3
import urllib.request
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from features import build_features
from experiment import EVENTS, FEATURE_COLS, TRAIN_FRACTION, fit_logreg, predict_logreg, brier, logloss

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "football_research.db"
FIXTURES_URL = "https://football-data.co.uk/fixtures.csv"

EVENT_LABELS = {k: v["label"] for k, v in EVENTS.items()}


def train_model(df, y, upto=None):
    X = df[FEATURE_COLS].astype(float)
    means = X.mean()
    Xf = X.fillna(means).to_numpy()
    mu, sd = Xf.mean(axis=0), Xf.std(axis=0) + 1e-9
    w = fit_logreg((Xf - mu) / sd, y)
    return w, means, mu, sd


def predict_with(w, means, mu, sd, Xdf):
    X = Xdf[FEATURE_COLS].astype(float).fillna(means).to_numpy()
    return predict_logreg(w, (X - mu) / sd)


def main():
    df = build_features(DB).sort_values(["match_datetime", "match_id"]).reset_index(drop=True)
    n = len(df)
    split_idx = int(round(n * TRAIN_FRACTION))

    con = sqlite3.connect(DB)
    meta_row = con.execute("SELECT MIN(match_date), MAX(match_date), COUNT(*) FROM matches").fetchone()
    team_rows = con.execute("SELECT * FROM team_match ORDER BY match_datetime, match_id").fetchall()
    team_cols = [d[0] for d in con.execute("SELECT * FROM team_match LIMIT 1").description]
    con.close()

    y_all = {e: df.apply(spec["fn"], axis=1).to_numpy(dtype=float) for e, spec in EVENTS.items()}

    # خط الأساس: متوسط موسّع من المباريات السابقة فقط.
    def baseline_probs(y):
        out, running, count = [], 0.0, 0
        for i in range(n):
            out.append(min(max(running / count if count else 0.5, 0.02), 0.98))
            running += y[i]
            count += 1
        return np.array(out)

    base = {e: baseline_probs(y) for e, y in y_all.items()}

    # نماذج التجربة (تدريب على الجزء الأول) ونماذج المنصة (تدريب على كل المباريات).
    exp_models, full_models = {}, {}
    for e in EVENTS:
        w, means, mu, sd = train_model(df.iloc[:split_idx], y_all[e][:split_idx])
        exp_models[e] = (w, means, mu, sd)
        w2, means2, mu2, sd2 = train_model(df, y_all[e])
        full_models[e] = (w2, means2, mu2, sd2)

    # مقاييس التجربة على جزء الاختبار.
    metrics = []
    for e, spec in EVENTS.items():
        w, means, mu, sd = exp_models[e]
        pm = predict_with(w, means, mu, sd, df.iloc[split_idx:])
        pb = base[e][split_idx:]
        yt = y_all[e][split_idx:]
        metrics.append({
            "event": e, "label": spec["label"], "n": int(len(yt)),
            "positives": int(yt.sum()), "base_rate": round(float(yt.mean()), 3),
            "brier_baseline": round(brier(pb, yt), 4), "brier_model": round(brier(pm, yt), 4),
            "acc_baseline": round(float(np.mean((pb >= 0.5) == yt)), 3),
            "acc_model": round(float(np.mean((pm >= 0.5) == yt)), 3),
        })

    # تكرار الأحداث في العينة.
    freq = {e: {"label": EVENT_LABELS[e], "count": int(y.sum()), "of": n,
                "pct": round(100 * float(y.mean()), 1)} for e, y in y_all.items()}
    # حدث وصفي سادس لم يدخل تجربة التوقع بعد (موثق في قاموس الأحداث).
    ch = int((df["total_corners"] >= 10).sum())
    freq["corners_high"] = {"label": "ركنيات كثيرة (10 أو أكثر)", "count": ch, "of": n,
                            "pct": round(100 * ch / n, 1), "descriptive": True}

    # ملاحظة ترخيصية: لا ننشر صفوفًا بمستوى المباراة في اللقطة العامة؛ ذلك كان يعادل
    # إعادة نشر بيانات المصدر الخام. تفاصيل كل مباراة تُنتَج محليًا بتشغيل السكربتات.
    matches = []

    # المباريات القادمة من ملف fixtures لدى المصدر.
    fixtures = []
    try:
        with urllib.request.urlopen(FIXTURES_URL, timeout=30) as resp:
            text = resp.read().decode("utf-8-sig")
        frows = [r for r in csv.DictReader(io.StringIO(text)) if r.get("Div") == "E0"]
        last_dt = df["match_datetime"].max()
        for fr in frows:
            d = fr.get("Date", "").strip()
            if not d:
                continue
            day, month, year = d.split("/")
            dt = f"{year}-{month}-{day} {(fr.get('Time') or '00:00').strip()}"
            if dt <= last_dt:
                continue
            home, away = fr.get("HomeTeam", "").strip(), fr.get("AwayTeam", "").strip()
            ref = (fr.get("Referee") or "").strip()

            # حالة كل فريق الآن: متوسطات آخر 5 مباريات من جدول team_match مباشرة.
            trs = [dict(zip(team_cols, r)) for r in team_rows]

            def state(team):
                played = [r for r in trs if r["team"] == team]
                last = played[-5:]

                def avg(col, rows):
                    vals = [r[col] for r in rows if r[col] is not None]
                    return sum(vals) / len(vals) if vals else None

                return {"played": len(played), "gf5": avg("goals_for", last),
                        "ga5": avg("goals_against", last), "y5": avg("yellows", last),
                        "xg5": avg("xg_for", last), "ppg": avg("points", played)}

            hs, as_ = state(home), state(away)
            ref_hist = df[df["referee"] == ref]
            low_team = hs["played"] < 3 or as_["played"] < 3
            low_ref = len(ref_hist) < 3
            Xf = pd.DataFrame([{
                "h_gf5": hs["gf5"], "h_ga5": hs["ga5"], "a_gf5": as_["gf5"],
                "a_ga5": as_["ga5"], "h_y5": hs["y5"], "a_y5": as_["y5"],
                "h_xg5": hs["xg5"], "a_xg5": as_["xg5"],
                "ref_y_avg": float(ref_hist["total_yellows"].mean()) if len(ref_hist) else None,
                "h_ppg": hs["ppg"], "a_ppg": as_["ppg"],
            }])
            probs = {}
            for e in EVENTS:
                w, means, mu, sd = full_models[e]
                p = predict_with(w, means, mu, sd, Xf)[0]
                probs[e] = {"model": round(float(p), 3),
                            "baseline": freq[e]["pct"] / 100.0}
            fixtures.append({
                "date": f"{year}-{month}-{day}", "time": (fr.get("Time") or "").strip(),
                "home": home, "away": away, "referee": ref or None,
                "ref_prior_matches": int(len(ref_hist)),
                "low_team_data": bool(low_team), "low_ref_data": bool(low_ref),
                "probs": probs,
            })
    except Exception as exc:  # عدم توفر fixtures لا يوقف اللقطة
        fixtures = []
        print(f"تعذر جلب fixtures: {exc}")

    snap = {
        "meta": {
            "league": "الدوري الإنجليزي الممتاز", "league_code": "E0", "season": "2026/27",
            "matches": n, "from": meta_row[0], "to": meta_row[1],
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "source": "https://football-data.co.uk/mmz4281/2627/E0.csv",
            "fixtures_source": FIXTURES_URL,
            "train": int(split_idx), "test": int(n - split_idx),
            "notes": [
                "لقطة ثابتة بوقت التوليد، وليست بثًا مباشرًا ولا تحديثًا لحظيًا.",
                "أرقام البطاقات خاصة بمصدر Football-Data وتختلف عن العد الرسمي في بعض المباريات.",
                "توقعات المباريات القادمة من نموذج أُعيد تدريبه على كل المباريات الـ109؛ قياس الدقة المنفصل موثق في قسم التجربة.",
            ],
        },
        "events": freq,
        "experiment": metrics,
        "fixtures": fixtures,
    }
    out = ROOT / "data" / "snapshot.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    print(f"snapshot.json: مباريات {len(matches)}، قادمة {len(fixtures)}، أحداث {len(EVENTS)}")


if __name__ == "__main__":
    main()
