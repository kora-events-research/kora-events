#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_site.py - توليد data/snapshot.json الذي يغذي الموقع الثابت.

ينتج لقطة واحدة مختومة بوقت التوليد تشمل: تعريفات الأحداث وتكرارها،
نتائج التجربة الزمنية، توقعات المباريات القادمة (من ملف fixtures لدى
Football-Data ومكملًا من جدولة ESPN العامة)، التكرارات المشتركة التجريبية
لمجموعات الأحداث (وصفية فقط)، وسجل التوقعات المحفوظة قبل الانطلاق مع
تقييمها بالنتائج الفعلية عند توفرها.

الحدود الترخيصية: لا ننشر صفوفًا بمستوى المباراة (بيانات Football-Data الخام)،
ولا أي بيانات أسعار/odds من ESPN إطلاقًا؛ نأخذ من ESPN حقائق الجدولة فقط
(الفريقان والتاريخ والوقت) مع الإسناد.

التشغيل: python3 src/export_site.py
"""
import csv
import io
import json
import pathlib
import sqlite3
import urllib.request
from datetime import datetime, timedelta, timezone
from itertools import combinations
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from features import build_features
from experiment import EVENTS, FEATURE_COLS, TRAIN_FRACTION, fit_logreg, predict_logreg, brier, logloss

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "football_research.db"
FIXTURES_URL = "https://football-data.co.uk/fixtures.csv"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates={}"
ESPN_DAYS_AHEAD = 10
FORECAST_LOG = ROOT / "data" / "forecast_log.json"

EVENT_LABELS = {k: v["label"] for k, v in EVENTS.items()}

# ربط أسماء الفرق بين ESPN وFootball-Data (تسمية فقط؛ الفرق نفسها).
ESPN_TEAM_MAP = {
    "AFC Bournemouth": "Bournemouth",
    "Brighton & Hove Albion": "Brighton",
    "Coventry City": "Coventry",
    "Hull City": "Hull",
    "Ipswich Town": "Ipswich",
    "Leeds United": "Leeds",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Tottenham Hotspur": "Tottenham",
}


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


def fetch_fd_fixtures():
    """صفوف جدولة Football-Data لدوري E0 (تحمل الحكم عادة)."""
    rows = []
    with urllib.request.urlopen(FIXTURES_URL, timeout=30) as resp:
        text = resp.read().decode("utf-8-sig")
    for fr in csv.DictReader(io.StringIO(text)):
        if fr.get("Div") != "E0":
            continue
        d = fr.get("Date", "").strip()
        if not d:
            continue
        day, month, year = d.split("/")
        rows.append({
            "date": f"{year}-{month}-{day}",
            "time": (fr.get("Time") or "").strip(),
            "home": fr.get("HomeTeam", "").strip(),
            "away": fr.get("AwayTeam", "").strip(),
            "referee": (fr.get("Referee") or "").strip() or None,
            "src": "football-data",
        })
    return rows


def fetch_espn_fixtures():
    """حقائق الجدولة فقط من لوحة ESPN العامة (فريقان + تاريخ + وقت).

    لا نقرأ ولا نخزن أي حقول odds/pickcenter إطلاقًا. الأحداث بحالة pre فقط.
    """
    rows = []
    today = datetime.now(timezone.utc).date()
    for i in range(ESPN_DAYS_AHEAD + 1):
        day = today + timedelta(days=i)
        url = ESPN_SCOREBOARD.format(day.strftime("%Y%m%d"))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "kora-events-research/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
        except Exception as exc:
            print(f"ESPN {day}: تعذر الجلب ({exc})")
            continue
        for ev in data.get("events", []):
            try:
                if ev.get("status", {}).get("type", {}).get("state") != "pre":
                    continue
                kick = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
                comp = ev["competitions"][0]
                home = away = None
                for c in comp["competitors"]:
                    name = c["team"]["displayName"]
                    name = ESPN_TEAM_MAP.get(name, name)
                    if c.get("homeAway") == "home":
                        home = name
                    else:
                        away = name
                if not home or not away:
                    continue
                london = kick.astimezone(ZoneInfo("Europe/London"))
                rows.append({
                    "date": london.strftime("%Y-%m-%d"),
                    "time": london.strftime("%H:%M"),
                    "home": home, "away": away,
                    "referee": None,  # ESPN لا يعلن الحكم مبكرًا عادة
                    "src": "espn",
                    "kickoff_utc": kick.astimezone(timezone.utc),
                })
            except Exception as exc:
                print(f"ESPN event skipped: {exc}")
    return rows


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

    exp_models, full_models = {}, {}
    for e in EVENTS:
        w, means, mu, sd = train_model(df.iloc[:split_idx], y_all[e][:split_idx])
        exp_models[e] = (w, means, mu, sd)
        w2, means2, mu2, sd2 = train_model(df, y_all[e])
        full_models[e] = (w2, means2, mu2, sd2)

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

    freq = {e: {"label": EVENT_LABELS[e], "count": int(y.sum()), "of": n,
                "pct": round(100 * float(y.mean()), 1)} for e, y in y_all.items()}
    ch = int((df["total_corners"] >= 10).sum())
    freq["corners_high"] = {"label": "ركنيات كثيرة (10 أو أكثر)", "count": ch, "of": n,
                            "pct": round(100 * ch / n, 1), "descriptive": True}

    # التكرارات المشتركة التجريبية لكل مجموعة جزئية من الأحداث المتوقعة (وصفية فقط —
    # ليست توقعًا نموذجيًا لمباراة بعينها). مجاميع على مستوى العينة، لا صفوف مباريات.
    pred_events = list(EVENTS.keys())
    joints = {}
    for r in range(1, len(pred_events) + 1):
        for combo in combinations(pred_events, r):
            mask = np.ones(n, dtype=bool)
            for e in combo:
                mask &= y_all[e] > 0.5
            key = "|".join(sorted(combo))
            joints[key] = {"count": int(mask.sum()), "of": n}

    # ---- جدولة المباريات القادمة: Football-Data أولًا ثم ESPN مكملًا ----
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

    raw_fixtures = []
    try:
        raw_fixtures = fetch_fd_fixtures()
    except Exception as exc:
        print(f"تعذر جلب fixtures لدى Football-Data: {exc}")
    fd_keys = {(r["date"], r["home"], r["away"]) for r in raw_fixtures}
    try:
        for r in fetch_espn_fixtures():
            if (r["date"], r["home"], r["away"]) not in fd_keys:
                raw_fixtures.append(r)
    except Exception as exc:
        print(f"تعذر جلب جدولة ESPN: {exc}")

    last_dt = df["match_datetime"].max()
    now_utc = datetime.now(timezone.utc)
    fixtures = []
    for fr in raw_fixtures:
        dt = f"{fr['date']} {fr.get('time') or '00:00'}"
        if dt <= last_dt:
            continue
        home, away, ref = fr["home"], fr["away"], fr.get("referee")
        kickoff_utc = fr.get("kickoff_utc")
        if kickoff_utc is None:
            if (fr.get("time") or "").strip():
                hh, mm = fr["time"].strip().split(":")[:2]
                y_, m_, d_ = fr["date"].split("-")
                kickoff_utc = datetime(int(y_), int(m_), int(d_), int(hh), int(mm),
                                       tzinfo=ZoneInfo("Europe/London")).astimezone(timezone.utc)
        kickoff_passed = (kickoff_utc <= now_utc) if kickoff_utc else None
        kick_london = kickoff_utc.astimezone(ZoneInfo("Europe/London")) if kickoff_utc else None
        hs, as_ = state(home), state(away)
        ref_hist = df[df["referee"] == ref] if ref else df.iloc[0:0]
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
            "date": fr["date"], "time": fr.get("time") or "",
            "home": home, "away": away, "referee": ref,
            "ref_prior_matches": int(len(ref_hist)),
            "low_team_data": bool(low_team), "low_ref_data": bool(low_ref),
            "kickoff_london": kick_london.strftime("%Y-%m-%d %H:%M %Z") if kick_london else None,
            "kickoff_utc": kickoff_utc.strftime("%Y-%m-%d %H:%M UTC") if kickoff_utc else None,
            "kickoff_passed": kickoff_passed,
            "src": fr["src"],
            "probs": probs,
        })

    fixtures.sort(key=lambda f: (f["date"], f["time"]))

    # ---- سجل التوقعات المحفوظة قبل الانطلاق + تقييمها بالنتائج الفعلية ----
    gen_utc = now_utc.strftime("%Y-%m-%d %H:%M UTC")
    log = {}
    if FORECAST_LOG.exists():
        try:
            log = json.loads(FORECAST_LOG.read_text(encoding="utf-8"))
        except Exception:
            log = {}
    for f in fixtures:
        if f["kickoff_passed"] is False and f["kickoff_utc"]:
            key = f"{f['date']}|{f['home']}|{f['away']}"
            if key not in log:
                # أول تسجيل للتوقع يبقى كما هو نهائيًا؛ لا يُستبدل ولا يُحدَّث في أي تشغيل لاحق.
                log[key] = {
                    "home": f["home"], "away": f["away"], "date": f["date"],
                    "kickoff_utc": f["kickoff_utc"], "forecast_at": gen_utc,
                    "model_train_matches": n,
                    "data_through": meta_row[1],
                    "probs": {e: p["model"] for e, p in f["probs"].items()},
                }
    FORECAST_LOG.parent.mkdir(exist_ok=True)
    FORECAST_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")

    results = []
    df_by_key = {}
    for i, row in df.iterrows():
        k = (str(row["match_datetime"])[:10], row["home_team"], row["away_team"])
        df_by_key[k] = i
    for key, entry in sorted(log.items()):
        idx = df_by_key.get((entry["date"], entry["home"], entry["away"]))
        if idx is None:
            continue  # لم تُلعب بعد أو لم تصل نتيجتها من المصدر بعد
        events = {}
        for e in EVENTS:
            events[e] = {"forecast": entry["probs"].get(e),
                         "actual": bool(y_all[e][idx] > 0.5)}
        mi = entry.get("model_train_matches")
        dt_ = entry.get("data_through")
        results.append({
            "home": entry["home"], "away": entry["away"], "date": entry["date"],
            "forecast_at": entry["forecast_at"],
            "model_info": (f"نموذج مدرب على {mi} مباراة حتى {dt_}" if mi else None),
            "events": events,
        })

    snap = {
        "meta": {
            "league": "الدوري الإنجليزي الممتاز", "league_code": "E0", "season": "2026/27",
            "matches": n, "from": meta_row[0], "to": meta_row[1],
            "generated_at_utc": gen_utc,
            "source": "https://football-data.co.uk/mmz4281/2627/E0.csv",
            "fixtures_source": FIXTURES_URL,
            "fixtures_source_espn": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
            "train": int(split_idx), "test": int(n - split_idx),
            "notes": [
                "لقطة ثابتة بوقت التوليد، وليست بثًا مباشرًا ولا تحديثًا لحظيًا.",
                "أرقام البطاقات خاصة بمصدر Football-Data وتختلف عن العد الرسمي في بعض المباريات.",
                "توقعات المباريات القادمة من نموذج أُعيد تدريبه على كل مباريات الموسم؛ قياس الدقة المنفصل موثق في قسم التجربة.",
                "حقائق الجدولة (الفريقان والتاريخ والوقت) من Football-Data ومكملة من لوحة ESPN العامة مع الإسناد؛ لا تُقرأ ولا تُعرض أي أسعار من أي مصدر.",
            ],
        },
        "events": freq,
        "experiment": metrics,
        "fixtures": fixtures,
        "joints": joints,
        "results": results,
    }
    out = ROOT / "data" / "snapshot.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    print(f"snapshot.json: قادمة {len(fixtures)}، مجموعات مشتركة {len(joints)}، "
          f"توقعات مسجلة {len(log)}، تقييمات فعلية {len(results)}")


if __name__ == "__main__":
    main()
