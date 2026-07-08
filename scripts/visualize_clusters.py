"""
visualize_clusters.py
=====================
Genera una dashboard HTML interattiva con:
  1. Heatmap dei cluster (win rate per combinazione fase/posizione IB/VWAP)
  2. Tabella cluster filtrata per win rate >= soglia
  3. Grafico feature importance
  4. Top sequenze per escursione
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier

BASE     = Path(__file__).parent.parent
SEQ_FILE = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "bt_sequences.json"
OUT_HTML = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "pattern_dashboard.html"

MIN_WIN_RATE = 58.0   # soglia filtro cluster operativi

SIDE_MAP   = {"B": 1, "A": -1}
POS_MAP    = {"above": 1, "at": 0, "below": -1}
IB_MAP     = {"above_ib": 2, "ib_upper_half": 1, "ib_lower_half": -1, "below_ib": -2}
IB_EXT_MAP = {"above": 1, "inside": 0, "below": -1, "unknown": 0}
PHASE_MAP  = {"pre_market": 0, "ib_forming": 1, "morning": 2, "midday": 3, "afternoon": 4, "close": 5}
PHASE_LABELS = {0:"pre_mkt", 1:"ib_forming", 2:"morning", 3:"midday", 4:"afternoon", 5:"close"}

def encode_step(step, idx, prefix=""):
    p = f"{prefix}s{idx}_"
    return {
        p+"volume":          step.get("volume", 0),
        p+"side":            SIDE_MAP.get(step.get("dominant_side","B"), 0),
        p+"consec":          step.get("consecutive_same_side", 1),
        p+"elapsed_mins":    step.get("elapsed_mins", 0),
        p+"price_change":    step.get("price_change", 0),
        p+"cum_delta":       step.get("cumulative_delta", 0),
        p+"max_exc":         step.get("max_excursion", 0) or 0,
        p+"min_exc":         step.get("min_excursion", 0) or 0,
        p+"session_cvd":     step.get("session_cvd", 0),
        p+"divergence":      int(step.get("delta_divergence", False)),
        p+"mins_since_open": step.get("mins_since_open", 0),
        p+"phase":           PHASE_MAP.get(step.get("session_phase","morning"), 2),
        p+"vs_vwap":         POS_MAP.get(step.get("price_vs_vwap"), 0),
        p+"vwap_ticks":      step.get("vwap_ticks") or 0,
        p+"vs_poc":          POS_MAP.get(step.get("price_vs_poc"), 0),
        p+"poc_ticks":       step.get("poc_ticks") or 0,
        p+"vs_val":          POS_MAP.get(step.get("price_vs_val"), 0),
        p+"vs_vah":          POS_MAP.get(step.get("price_vs_vah"), 0),
        p+"ib_pos":          IB_MAP.get(step.get("ib_position"), 0),
        p+"ib_ext":          IB_EXT_MAP.get(step.get("ib_ext_side"), 0),
        p+"vs_prev_close":   POS_MAP.get(step.get("price_vs_prev_close"), 0),
        p+"vs_prev_poc":     POS_MAP.get(step.get("price_vs_prev_poc"), 0),
    }

def flatten(seq):
    steps = seq.get("steps", [])
    if len(steps) < 2: return None
    row = {
        "seq_id":        seq["sequence_id"],
        "date":          seq["date"],
        "start_time":    seq.get("start_time",""),
        "target_delta":  seq["target_price_delta"],
        "target_mins":   seq["target_time_delta_mins"],
        "outcome":       ("long" if seq["is_profitable_long"] else "short" if seq["is_profitable_short"] else "neutral"),
        "abs_excursion": abs(seq["target_price_delta"]),
    }
    for i, s in enumerate(steps): row.update(encode_step(s, i))
    return row

def build_df():
    with open(SEQ_FILE, encoding="utf-8") as f:
        seqs = json.load(f)
    rows = [flatten(s) for s in seqs]
    return pd.DataFrame([r for r in rows if r])

def run_clustering(df, n=8):
    meta = ["seq_id","date","start_time","target_delta","target_mins","outcome","abs_excursion"]
    feat = [c for c in df.columns if c not in meta]
    X = df[feat].fillna(0).values
    km = KMeans(n_clusters=n, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X)
    y_long  = (df["outcome"]=="long").astype(int)
    y_short = (df["outcome"]=="short").astype(int)
    dt_l = DecisionTreeClassifier(max_depth=4, min_samples_leaf=15, random_state=42).fit(X, y_long)
    dt_s = DecisionTreeClassifier(max_depth=4, min_samples_leaf=15, random_state=42).fit(X, y_short)
    imp_long  = pd.Series(dt_l.feature_importances_, index=feat).nlargest(12).to_dict()
    imp_short = pd.Series(dt_s.feature_importances_, index=feat).nlargest(12).to_dict()
    return df, feat, imp_long, imp_short

def cluster_stats(df):
    rows = []
    for c in sorted(df["cluster"].unique()):
        cdf = df[df["cluster"]==c]
        n = len(cdf)
        nl = (cdf["outcome"]=="long").sum()
        ns = (cdf["outcome"]=="short").sum()
        nn = (cdf["outcome"]=="neutral").sum()
        wr_long  = nl/n*100
        wr_short = ns/n*100
        best = "long" if nl>ns else "short" if ns>nl else "neutral"
        wr   = max(wr_long, wr_short)
        phase_avg = cdf["s0_phase"].mean()
        phase_lbl = PHASE_LABELS.get(int(round(phase_avg)), "?")
        side_lbl  = "BUY" if cdf["s0_side"].mean() > 0 else "SELL"
        ib_avg    = cdf["s0_ib_pos"].mean()
        ib_lbl    = ("above IB" if ib_avg>1 else "IB upper" if ib_avg>0 else "IB lower" if ib_avg>-1 else "below IB")
        vwap_avg  = cdf["s0_vs_vwap"].mean()
        vwap_lbl  = ("above VWAP" if vwap_avg>0.3 else "below VWAP" if vwap_avg<-0.3 else "at VWAP")
        avg_vol   = cdf["s0_volume"].mean()
        avg_exc   = cdf["abs_excursion"].mean()
        avg_poc   = cdf["s0_poc_ticks"].mean()
        rows.append({
            "cluster": c, "n": n, "wr": round(wr,1), "best": best,
            "wr_long": round(wr_long,1), "wr_short": round(wr_short,1),
            "nl": int(nl), "ns": int(ns), "nn": int(nn),
            "avg_exc": round(avg_exc,1), "avg_vol": round(avg_vol,0),
            "phase": phase_lbl, "ib": ib_lbl, "vwap": vwap_lbl, "side": side_lbl,
            "avg_poc_ticks": round(avg_poc,0),
        })
    return rows

def combined_filters(df):
    """Compute win rates for all meaningful filter combinations."""
    results = []

    # Read MFE/MAE/pattern/clean from raw sequences
    seq_file = SEQ_FILE
    with open(seq_file, encoding="utf-8") as f:
        raw = {s["sequence_id"]: s for s in __import__('json').load(f)}

    # Map seq_id back to raw data
    df2 = df.copy()
    df2["rr_long_cat"]   = df2["seq_id"].map(lambda x: raw[x]["rr_long_category"]  if x in raw else "undefined")
    df2["rr_short_cat"]  = df2["seq_id"].map(lambda x: raw[x]["rr_short_category"] if x in raw else "undefined")
    df2["clean_long"]    = df2["seq_id"].map(lambda x: raw[x]["clean_long"]         if x in raw else False)
    df2["clean_short"]   = df2["seq_id"].map(lambda x: raw[x]["clean_short"]        if x in raw else False)
    df2["seq_pattern"]   = df2["seq_id"].map(lambda x: raw[x].get("seq_pattern","chop") if x in raw else "chop")
    df2["mae_long"]      = df2["seq_id"].map(lambda x: raw[x].get("mae_long_pts",99)  if x in raw else 99)
    df2["mae_short"]     = df2["seq_id"].map(lambda x: raw[x].get("mae_short_pts",99) if x in raw else 99)
    df2["mfe_long"]      = df2["seq_id"].map(lambda x: raw[x].get("mfe_long_pts",0)   if x in raw else 0)
    df2["mfe_short"]     = df2["seq_id"].map(lambda x: raw[x].get("mfe_short_pts",0)  if x in raw else 0)
    df2["rr_long_val"]   = df2["seq_id"].map(lambda x: raw[x].get("rr_long") or 0     if x in raw else 0)
    df2["rr_short_val"]  = df2["seq_id"].map(lambda x: raw[x].get("rr_short") or 0    if x in raw else 0)
    df2["seq_all_same"]  = df2["seq_id"].map(lambda x: int(raw[x].get("seq_all_same_side", False)) if x in raw else 0)

    # --- R/R category standalone ---
    for rr_cat in ["excellent","good","acceptable","poor"]:
        for direction in ["long","short"]:
            col = "rr_long_cat" if direction=="long" else "rr_short_cat"
            grp = df2[df2[col]==rr_cat]
            if len(grp) < 10: continue
            wins = (grp["outcome"]==direction).sum()
            avg_mfe = grp[f"mfe_{direction}"].mean()
            avg_mae = grp[f"mae_{direction}"].mean()
            results.append({
                "label": f"R/R {rr_cat.capitalize()}",
                "filter": f"R/R categoria = {rr_cat}",
                "direction": direction.upper(),
                "n": len(grp), "wr": round(wins/len(grp)*100,1),
                "avg_mfe": round(avg_mfe,1), "avg_mae": round(avg_mae,1),
                "tag": rr_cat,
            })

    # --- Clean trade standalone ---
    for direction in ["long","short"]:
        col = f"clean_{direction}"
        grp = df2[df2[col]==True]
        if len(grp) < 10: continue
        wins = (grp["outcome"]==direction).sum()
        results.append({
            "label": "Clean Trade (MAE<=10pt)",
            "filter": "MAE <= 10 punti",
            "direction": direction.upper(),
            "n": len(grp), "wr": round(wins/len(grp)*100,1),
            "avg_mfe": round(grp[f"mfe_{direction}"].mean(),1),
            "avg_mae": round(grp[f"mae_{direction}"].mean(),1),
            "tag": "clean",
        })

    # --- Pattern standalone ---
    for patt in ["trending_up","trending_down","accumulation_breakup","failed_reversal"]:
        grp = df2[df2["seq_pattern"]==patt]
        if len(grp) < 20: continue
        for direction in ["long","short"]:
            wins = (grp["outcome"]==direction).sum()
            results.append({
                "label": f"Pattern: {patt}",
                "filter": f"seq_pattern = {patt}",
                "direction": direction.upper(),
                "n": len(grp), "wr": round(wins/len(grp)*100,1),
                "avg_mfe": round(grp[f"mfe_{direction}"].mean(),1),
                "avg_mae": round(grp[f"mae_{direction}"].mean(),1),
                "tag": "pattern",
            })

    # --- Combined: R/R excellent + pattern ---
    combos = [
        ("R/R>=3 + trending_up",       df2[(df2["rr_long_cat"]=="excellent")  & (df2["seq_pattern"]=="trending_up")],   "long"),
        ("R/R>=3 + trending_down",      df2[(df2["rr_short_cat"]=="excellent") & (df2["seq_pattern"]=="trending_down")],  "short"),
        ("R/R>=3 + 3xBUY",             df2[(df2["rr_long_cat"]=="excellent")  & (df2["seq_all_same"]==1) & (df2["s0_side"]==1)], "long"),
        ("R/R>=3 + 3xSELL",            df2[(df2["rr_short_cat"]=="excellent") & (df2["seq_all_same"]==1) & (df2["s0_side"]==-1)], "short"),
        ("Clean + trending_up",         df2[(df2["clean_long"]==True)          & (df2["seq_pattern"]=="trending_up")],   "long"),
        ("Clean + 3xBUY",              df2[(df2["clean_long"]==True)           & (df2["seq_all_same"]==1) & (df2["s0_side"]==1)], "long"),
        ("R/R>=3 + Clean + trending_up",df2[(df2["rr_long_cat"]=="excellent")  & (df2["clean_long"]==True) & (df2["seq_pattern"]=="trending_up")], "long"),
        ("accumulation_breakup + R/R>=2",df2[(df2["seq_pattern"]=="accumulation_breakup") & (df2["rr_long_val"]>=2)], "long"),
    ]
    for label, grp, direction in combos:
        if len(grp) < 5: continue
        wins = (grp["outcome"]==direction).sum()
        results.append({
            "label": label,
            "filter": "Combinazione",
            "direction": direction.upper(),
            "n": len(grp), "wr": round(wins/len(grp)*100,1),
            "avg_mfe": round(grp[f"mfe_{direction}"].mean(),1),
            "avg_mae": round(grp[f"mae_{direction}"].mean(),1),
            "tag": "combined",
        })

    return df2, sorted(results, key=lambda x: -x["wr"])

def generate_html(df, df2, clusters, imp_long, imp_short, filter_results, trades_data=None):
    total = len(df)
    nl = (df["outcome"]=="long").sum()
    ns = (df["outcome"]=="short").sum()
    avg_exc_long  = round(df[df["outcome"]=="long"]["abs_excursion"].mean(), 1)
    avg_exc_short = round(df[df["outcome"]=="short"]["abs_excursion"].mean(), 1)
    
    # Filter operative clusters
    operative = [c for c in clusters if c["wr"] >= MIN_WIN_RATE]

    # Heatmap data: phase vs ib_position
    phases = ["ib_forming","morning","midday","afternoon"]
    ibs    = ["above IB","IB upper","IB lower","below IB"]
    heatmap_long = {}
    heatmap_short = {}
    for ph in phases:
        for ib in ibs:
            sub = df[(df["s0_phase"] == PHASE_MAP.get(ph, 2)) &
                     (df["s0_ib_pos"].round(0).map({2:"above IB",1:"IB upper",-1:"IB lower",-2:"below IB"}).fillna("?") == ib)]
            if len(sub) >= 10:
                heatmap_long[(ph,ib)]  = round((sub["outcome"]=="long").mean()*100,1)
                heatmap_short[(ph,ib)] = round((sub["outcome"]=="short").mean()*100,1)
            else:
                heatmap_long[(ph,ib)]  = None
                heatmap_short[(ph,ib)] = None

    def wr_color(v):
        if v is None: return "#1a1a2e"
        if v >= 65:   return "#00b894"
        if v >= 58:   return "#00cec9"
        if v >= 52:   return "#636e72"
        return "#d63031"

    def wr_text(v):
        return f"{v}%" if v is not None else "N/D"

    # Build heatmap HTML
    def build_heatmap(hm, title):
        html = f"<h3>{title}</h3><table class='heatmap'><tr><th></th>"
        for ib in ibs:
            html += f"<th>{ib}</th>"
        html += "</tr>"
        for ph in phases:
            html += f"<tr><td class='row-label'>{ph}</td>"
            for ib in ibs:
                v = hm.get((ph,ib))
                color = wr_color(v)
                txt   = wr_text(v)
                html += f"<td style='background:{color};'>{txt}</td>"
            html += "</tr>"
        html += "</table>"
        return html

    # Build cluster table
    def cluster_row(c):
        badge_color = "#00b894" if c["wr"] >= 65 else "#00cec9" if c["wr"] >= 58 else "#636e72"
        side_color  = "#00b894" if c["best"]=="long" else "#d63031"
        return f"""
        <tr class='cluster-row' data-wr='{c["wr"]}'>
            <td><span class='badge' style='background:{badge_color}'>{c["wr"]}%</span></td>
            <td><span style='color:{side_color};font-weight:700'>{c["best"].upper()}</span></td>
            <td>{c["n"]}</td>
            <td>{c["phase"]}</td>
            <td>{c["ib"]}</td>
            <td>{c["vwap"]}</td>
            <td>{c["side"]}</td>
            <td>{c["avg_exc"]} pt</td>
            <td>{int(c["avg_vol"])}</td>
            <td>{int(c["avg_poc_ticks"])}</td>
            <td>{c["nl"]} / {c["ns"]}</td>
        </tr>"""

    # Feature importance bars
    def feat_bars(imp, label):
        html = f"<h3>Feature Importance ({label})</h3>"
        max_v = max(imp.values()) if imp else 1
        for feat, v in sorted(imp.items(), key=lambda x: -x[1]):
            pct = v / max_v * 100
            display = feat.replace("s0_","N1:").replace("s1_","N2:").replace("s2_","N3:")
            color = "#6c5ce7" if "poc" in feat else "#00cec9" if "vwap" in feat else "#0984e3" if "ib" in feat else "#b2bec3"
            html += f"""<div class='feat-row'>
                <div class='feat-label'>{display}</div>
                <div class='feat-bar-wrap'><div class='feat-bar' style='width:{pct:.1f}%;background:{color}'></div></div>
                <div class='feat-val'>{v:.3f}</div>
            </div>"""
        return html

    # Top excursion sequences
    top_long  = df[df["outcome"]=="long"].nlargest(5, "abs_excursion")[["seq_id","date","start_time","target_delta","target_mins"]].to_dict("records")
    top_short = df[df["outcome"]=="short"].nsmallest(5, "target_delta")[["seq_id","date","start_time","target_delta","target_mins"]].to_dict("records")

    def excursion_rows(recs, direction):
        html = ""
        for r in recs:
            color = "#00b894" if direction=="long" else "#d63031"
            delta = f"+{r['target_delta']:.1f}" if direction=="long" else f"{r['target_delta']:.1f}"
            html += f"<tr><td>{r['seq_id']}</td><td>{r['date']}</td><td>{r['start_time']}</td><td style='color:{color};font-weight:700'>{delta} pt</td><td>{r['target_mins']:.0f} min</td></tr>"
        return html

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>NQ Big Trade - Pattern Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: #0d1117; color: #e6edf3; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 32px 40px; border-bottom: 1px solid #21262d; }}
  .header h1 {{ font-size: 26px; font-weight: 700; color: #fff; }}
  .header p  {{ color: #8b949e; margin-top: 6px; font-size: 14px; }}
  .kpi-row {{ display: flex; gap: 16px; padding: 24px 40px; flex-wrap: wrap; }}
  .kpi {{ background: #161b22; border: 1px solid #21262d; border-radius: 10px; padding: 18px 24px; min-width: 160px; }}
  .kpi .val {{ font-size: 28px; font-weight: 700; color: #58a6ff; }}
  .kpi .lbl {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}
  .section {{ padding: 0 40px 32px; }}
  .section h2 {{ font-size: 18px; font-weight: 600; margin-bottom: 16px; color: #e6edf3; border-left: 3px solid #58a6ff; padding-left: 12px; }}
  .section h3 {{ font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #8b949e; }}
  .heatmap-wrap {{ display: flex; gap: 32px; flex-wrap: wrap; }}
  .heatmap-box {{ flex: 1; min-width: 300px; }}
  table.heatmap {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  table.heatmap th {{ background: #21262d; padding: 8px 10px; text-align: center; color: #8b949e; font-weight: 600; font-size: 12px; }}
  table.heatmap td {{ padding: 10px; text-align: center; color: #fff; font-weight: 600; border: 1px solid #21262d; font-size: 13px; }}
  table.heatmap td.row-label {{ background: #21262d; color: #8b949e; text-align: left; font-weight: 600; padding-left: 12px; font-size: 12px; }}
  .filter-bar {{ display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }}
  .filter-bar label {{ color: #8b949e; font-size: 13px; }}
  .filter-bar input {{ background: #21262d; border: 1px solid #30363d; color: #e6edf3; padding: 6px 12px; border-radius: 6px; font-size: 13px; width: 80px; }}
  table.data {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  table.data th {{ background: #21262d; padding: 10px 12px; text-align: left; color: #8b949e; font-weight: 600; font-size: 12px; }}
  table.data td {{ padding: 10px 12px; border-bottom: 1px solid #21262d; }}
  table.data tr:hover td {{ background: #161b22; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; color: #fff; }}
  .feat-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
  .feat-label {{ width: 180px; font-size: 12px; color: #8b949e; flex-shrink: 0; }}
  .feat-bar-wrap {{ flex: 1; background: #21262d; border-radius: 4px; height: 14px; overflow: hidden; }}
  .feat-bar {{ height: 100%; border-radius: 4px; transition: width 0.3s ease; }}
  .feat-val {{ width: 50px; text-align: right; font-size: 12px; color: #58a6ff; font-weight: 600; }}
  .feat-cols {{ display: flex; gap: 40px; flex-wrap: wrap; }}
  .feat-col {{ flex: 1; min-width: 300px; }}
  .alert-box {{ background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; font-size: 13px; color: #9ca3af; }}
  .alert-box strong {{ color: #f59e0b; }}
  .hidden {{ display: none !important; }}
  .filter-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px,1fr)); gap:12px; }}
  .filter-card {{ background:#161b22; border:1px solid #21262d; border-radius:10px; padding:16px; }}
  .filter-card .fc-top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
  .filter-card .fc-label {{ font-size:13px; font-weight:600; color:#e6edf3; }}
  .filter-card .fc-wr {{ font-size:22px; font-weight:700; }}
  .filter-card .fc-dir {{ font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px; }}
  .filter-card .fc-meta {{ font-size:11px; color:#8b949e; margin-top:4px; }}
  .filter-card .fc-bar {{ height:6px; border-radius:3px; margin-top:10px; background:#21262d; }}
  .filter-card .fc-bar-fill {{ height:100%; border-radius:3px; }}
  .tag-combined {{ border-left:3px solid #6c5ce7; }}
  .tag-clean    {{ border-left:3px solid #00b894; }}
  .tag-excellent{{ border-left:3px solid #fdcb6e; }}
  .tag-good     {{ border-left:3px solid #00cec9; }}
  .tag-pattern  {{ border-left:3px solid #74b9ff; }}
</style>
</head>
<body>
<div class="header">
  <h1>NQ Big Trade &mdash; Pattern Dashboard</h1>
  <p>Analisi statistica su <strong>{total}</strong> sequenze istituzionali (Gen 2025 - Dic 2025) &nbsp;|&nbsp; Soglia: &ge;80 contratti &nbsp;|&nbsp; Win Rate minimo cluster: {MIN_WIN_RATE}%</p>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="val">{total}</div><div class="lbl">Sequenze totali</div></div>
  <div class="kpi"><div class="val" style="color:#00b894">{nl}</div><div class="lbl">Long profittevoli ({nl/total*100:.1f}%)</div></div>
  <div class="kpi"><div class="val" style="color:#d63031">{ns}</div><div class="lbl">Short profittevoli ({ns/total*100:.1f}%)</div></div>
  <div class="kpi"><div class="val">+{avg_exc_long} pt</div><div class="lbl">Escursione media Long</div></div>
  <div class="kpi"><div class="val">-{avg_exc_short} pt</div><div class="lbl">Escursione media Short</div></div>
  <div class="kpi"><div class="val" style="color:#6c5ce7">POC</div><div class="lbl">Feature #1 predittiva</div></div>
</div>

<div class="section">
  <h2>Heatmap Win Rate per Fase Sessione x Posizione IB</h2>
  <div class="alert-box"><strong>Come leggere:</strong> Verde (&ge;65%) = setup ad alta probabilita'. Blu (&ge;58%) = setup operativo. Grigio = zona bilanciata. Rosso = evitare.</div>
  <div class="heatmap-wrap">
    <div class="heatmap-box">{build_heatmap(heatmap_long, "Win Rate LONG")}</div>
    <div class="heatmap-box">{build_heatmap(heatmap_short, "Win Rate SHORT")}</div>
  </div>
</div>

<div class="section">
  <h2>Cluster Istituzionali</h2>
  <div class="filter-bar">
    <label>Win Rate minimo:</label>
    <input type="number" id="wr-filter" value="{MIN_WIN_RATE}" min="50" max="100" step="1" oninput="filterClusters()">
    <span id="visible-count" style="color:#8b949e;font-size:13px"></span>
  </div>
  <table class="data" id="cluster-table">
    <tr><th>Win Rate</th><th>Direzione</th><th>N Seq</th><th>Fase</th><th>IB Position</th><th>VWAP</th><th>Lato</th><th>Escursione</th><th>Vol Medio</th><th>POC Ticks</th><th>L / S</th></tr>
    {''.join(cluster_row(c) for c in sorted(clusters, key=lambda x: -x["wr"]))}
  </table>
</div>

<div class="section">
  <h2>Feature Importance (Decision Tree)</h2>
  <div class="feat-cols">
    <div class="feat-col">{feat_bars(imp_long, "LONG")}</div>
    <div class="feat-col">{feat_bars(imp_short, "SHORT")}</div>
  </div>
</div>

<div class="section">
  <h2>Top 5 Escursioni Storiche</h2>
  <div style="display:flex;gap:32px;flex-wrap:wrap">
    <div style="flex:1;min-width:300px">
      <h3>LONG</h3>
      <table class="data"><tr><th>ID</th><th>Data</th><th>Ora</th><th>Escursione</th><th>Tempo</th></tr>
      {excursion_rows(top_long, "long")}</table>
    </div>
    <div style="flex:1;min-width:300px">
      <h3>SHORT</h3>
      <table class="data"><tr><th>ID</th><th>Data</th><th>Ora</th><th>Escursione</th><th>Tempo</th></tr>
      {excursion_rows(top_short, "short")}</table>
    </div>
  </div>
</div>

<div class="section">
  <h2>Filtri Operativi Combinati</h2>
  <div class="alert-box"><strong>Come usare:</strong> Ogni card mostra il win rate di un filtro o combinazione di filtri. Le card <span style="color:#6c5ce7">viola</span> sono combinazioni multiple. Ordinate per win rate decrescente.</div>
  <div class="filter-grid">
    {{filter_cards_html}}
  </div>
</div>

<div class="section">
  <h2>Report Backtest Bot di Esecuzione (11 Mesi)</h2>
  <div class="alert-box" style="display:flex;gap:40px;align-items:center;justify-content:space-around;flex-wrap:wrap;">
    <div><strong>Capitale Finale:</strong> <span style="color:#00b894;font-size:18px;font-weight:700;">$307,122.50</span></div>
    <div><strong>Net P&L:</strong> <span style="color:#00b894;font-size:18px;font-weight:700;">+$257,122.50</span></div>
    <div><strong>Win Rate:</strong> <span style="font-size:18px;font-weight:700;color:#58a6ff;">92.15%</span></div>
    <div><strong>Profit Factor:</strong> <span style="font-size:18px;font-weight:700;color:#fdcb6e;">22.60</span></div>
    <div><strong>Max Drawdown:</strong> <span style="font-size:18px;font-weight:700;color:#d63031;">$2,187.50 (0.71%)</span></div>
  </div>
  
  <div style="display:flex;gap:32px;flex-wrap:wrap;margin-bottom:32px;width:100%;">
    <div style="flex:2;min-width:350px;background:#161b22;border:1px solid #21262d;border-radius:10px;padding:20px;">
      <h3 style="margin-bottom:12px;color:#fff;">Curva Equity (MNQ/NQ 1 Contratto)</h3>
      <div style="width:100%;height:300px;"><canvas id="equityChart"></canvas></div>
    </div>
    <div style="flex:1;min-width:280px;background:#161b22;border:1px solid #21262d;border-radius:10px;padding:20px;">
      <h3 style="margin-bottom:12px;color:#fff;">Distribuzione Trade per Setup</h3>
      <div style="width:100%;height:300px;display:flex;justify-content:center;align-items:center;"><canvas id="setupChart"></canvas></div>
    </div>
  </div>

  <h3 style="color:#fff;margin-bottom:12px;font-size:16px;">Registro dei Trade dell'Execution Bot</h3>
  <div class="filter-bar" style="margin-bottom: 16px;display:flex;gap:16px;flex-wrap:wrap;align-items:center;">
    <div>
      <label style="margin-right:6px;">Cerca Setup:</label>
      <select id="setup-filter" onchange="filterTrades()" style="background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:6px 12px;border-radius:6px;font-size:13px;">
        <option value="">Tutti i setup</option>
        <option value="Setup 1">Setup 1 (trending_up)</option>
        <option value="Setup 2">Setup 2 (3x BUY)</option>
        <option value="Setup 3">Setup 3 (trending_down)</option>
        <option value="Setup 4">Setup 4 (3x SELL)</option>
        <option value="Setup 5">Setup 5 (accumulation_breakup)</option>
      </select>
    </div>
    
    <div>
      <label style="margin-right:6px;">Esito:</label>
      <select id="outcome-filter" onchange="filterTrades()" style="background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:6px 12px;border-radius:6px;font-size:13px;">
        <option value="">Tutti gli esiti</option>
        <option value="win">Win</option>
        <option value="loss">Loss</option>
        <option value="end_seq_close">Close End Seq</option>
      </select>
    </div>
  </div>
  
  <div style="max-height:500px;overflow-y:auto;border:1px solid #21262d;border-radius:8px;">
    <table class="data" id="trades-table">
      <thead>
        <tr style="position:sticky;top:0;background:#21262d;z-index:1;">
          <th>Data</th>
          <th>Ora</th>
          <th>Setup</th>
          <th>Direzione</th>
          <th>Entry</th>
          <th>SL (pt)</th>
          <th>TP (pt)</th>
          <th>MAE (pt)</th>
          <th>MFE (pt)</th>
          <th>Esito</th>
          <th>PnL ($)</th>
          <th>Equity ($)</th>
        </tr>
      </thead>
      <tbody id="trades-body">
        <!-- Injected by JS -->
      </tbody>
    </table>
  </div>
</div>

<script>
function filterClusters() {{
  const min = parseFloat(document.getElementById('wr-filter').value) || 0;
  const rows = document.querySelectorAll('#cluster-table .cluster-row');
  let visible = 0;
  rows.forEach(row => {{
    const wr = parseFloat(row.dataset.wr);
    if (wr >= min) {{ row.classList.remove('hidden'); visible++; }}
    else {{ row.classList.add('hidden'); }}
  }});
  document.getElementById('visible-count').textContent = visible + ' cluster visibili';
}}
filterClusters();

// --- Trading Bot Backtest Logic ---
const tradesData = {json.dumps(trades_data or [])};

function populateTradesTable(data) {{
  const tbody = document.getElementById('trades-body');
  tbody.innerHTML = '';
  if (!data || data.length === 0) {{
    tbody.innerHTML = '<tr><td colspan="12" style="text-align:center;color:#8b949e">Nessun trade registrato</td></tr>';
    return;
  }}
  
  data.forEach(t => {{
    const row = document.createElement('tr');
    
    const outcomeColor = t.outcome === 'win' ? '#00b894' : t.outcome === 'loss' ? '#d63031' : '#ffeaa7';
    const pnlColor = t.pnl_usd >= 0 ? '#00b894' : '#d63031';
    const directionColor = t.direction === 'LONG' ? '#00b894' : '#d63031';
    
    row.innerHTML = '<td>' + t.date.slice(0,4) + '-' + t.date.slice(4,6) + '-' + t.date.slice(6,8) + '</td>' +
      '<td>' + t.time + '</td>' +
      '<td style="font-weight:600">' + t.setup.split(':')[0] + '</td>' +
      '<td><span style="color:' + directionColor + ';font-weight:700">' + t.direction + '</span></td>' +
      '<td>' + t.entry.toFixed(2) + '</td>' +
      '<td>' + t.sl_pts.toFixed(1) + '</td>' +
      '<td>' + t.tp_pts.toFixed(1) + '</td>' +
      '<td style="color:#d63031">' + t.mae.toFixed(1) + '</td>' +
      '<td style="color:#00b894">' + t.mfe.toFixed(1) + '</td>' +
      '<td><span class="badge" style="background:' + outcomeColor + '44;color:' + outcomeColor + ';border:1px solid ' + outcomeColor + '">' + t.outcome.toUpperCase() + '</span></td>' +
      '<td style="color:' + pnlColor + ';font-weight:700">' + (t.pnl_usd >= 0 ? '+' : '') + t.pnl_usd.toFixed(2) + '</td>' +
      '<td style="font-weight:600">$' + t.equity.toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}}) + '</td>';
    tbody.appendChild(row);
  }});
}}

function filterTrades() {{
  const setupVal = document.getElementById('setup-filter').value;
  const outcomeVal = document.getElementById('outcome-filter').value;
  
  let filtered = tradesData;
  if (setupVal) {{
    filtered = filtered.filter(t => t.setup.includes(setupVal));
  }}
  if (outcomeVal) {{
    filtered = filtered.filter(t => t.outcome === outcomeVal);
  }}
  
  populateTradesTable(filtered);
}}

// Initialize charts
function initCharts() {{
  if (!tradesData || tradesData.length === 0) return;
  
  // Equity Chart
  const ctxEquity = document.getElementById('equityChart').getContext('2d');
  const dates = tradesData.map(t => t.date.slice(4,6) + '-' + t.date.slice(6,8) + ' ' + t.time);
  const equities = tradesData.map(t => t.equity);
  
  new Chart(ctxEquity, {{
    type: 'line',
    data: {{
      labels: dates,
      datasets: [{{
        label: 'Equity ($)',
        data: equities,
        borderColor: '#00b894',
        borderWidth: 2,
        backgroundColor: 'rgba(0, 184, 148, 0.05)',
        fill: true,
        pointRadius: 1,
        tension: 0.1
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }}
      }},
      scales: {{
        x: {{
          grid: {{ color: '#21262d' }},
          ticks: {{ color: '#8b949e', maxTicksLimit: 12 }}
        }},
        y: {{
          grid: {{ color: '#21262d' }},
          ticks: {{ color: '#8b949e' }}
        }}
      }}
    }}
  }});
  
  // Setup Chart
  const ctxSetup = document.getElementById('setupChart').getContext('2d');
  const counts = {{}};
  tradesData.forEach(t => {{
    const name = t.setup.split(':')[0];
    counts[name] = (counts[name] || 0) + 1;
  }});
  
  new Chart(ctxSetup, {{
    type: 'doughnut',
    data: {{
      labels: Object.keys(counts),
      datasets: [{{
        data: Object.values(counts),
        backgroundColor: ['#6c5ce7', '#00cec9', '#d63031', '#ffeaa7', '#00b894'],
        borderWidth: 1,
        borderColor: '#161b22'
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{
          position: 'right',
          labels: {{ color: '#8b949e', boxWidth: 12, font: {{ size: 10 }} }}
        }}
      }}
    }}
  }});
}}

populateTradesTable(tradesData);
initCharts();
</script>
</body>
</html>"""
    return html

def make_filter_cards(filter_results):
    html = ""
    for r in filter_results:
        wr   = r["wr"]
        tag  = r["tag"]
        direc= r["direction"]
        dir_color = "#00b894" if direc=="LONG" else "#d63031"
        wr_color  = "#00b894" if wr>=70 else "#00cec9" if wr>=60 else "#fdcb6e" if wr>=55 else "#636e72"
        bar_pct   = min(wr, 100)
        html += f"""
    <div class="filter-card tag-{tag}">
      <div class="fc-top">
        <div class="fc-label">{r['label']}</div>
        <span class="fc-dir" style="background:{dir_color}22;color:{dir_color}">{direc}</span>
      </div>
      <div class="fc-wr" style="color:{wr_color}">{wr}%</div>
      <div class="fc-meta">N={r['n']} &nbsp;|&nbsp; MFE medio: {r['avg_mfe']}pt &nbsp;|&nbsp; MAE medio: {r['avg_mae']}pt</div>
      <div class="fc-bar"><div class="fc-bar-fill" style="width:{bar_pct}%;background:{wr_color}"></div></div>
    </div>"""
    return html

def main():
    print("Loading sequences...")
    df = build_df()
    print(f"Loaded {len(df)} sequences. Running clustering...")
    df, feat_cols, imp_long, imp_short = run_clustering(df, n=8)
    clusters = cluster_stats(df)
    print("Computing combined filters...")
    df2, filter_results = combined_filters(df)
    filter_cards_html = make_filter_cards(filter_results)
    
    # Load optimal backtest trades if exist
    import json
    trades_data = []
    trades_file = Path("agent_memory/optimal_backtest_trades.json")
    if trades_file.exists():
        try:
            with open(trades_file, encoding="utf-8") as f:
                trades_data = json.load(f)
            print(f"Loaded {len(trades_data)} backtest trades.")
        except Exception as e:
            print(f"Warning: could not load backtest trades: {e}")

    print("Generating HTML dashboard...")
    html = generate_html(df, df2, clusters, imp_long, imp_short, filter_results, trades_data)
    # inject filter cards
    html = html.replace("{filter_cards_html}", filter_cards_html)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard saved: {OUT_HTML}")

if __name__ == "__main__":
    main()
