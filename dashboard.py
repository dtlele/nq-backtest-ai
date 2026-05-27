"""
NQ Backtest Dashboard — Dash + Plotly
Run: python dashboard.py  →  http://localhost:8050
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

# ── Load data ──────────────────────────────────────────────────────────────────
LOG_FILE    = Path(__file__).parent / "agent_memory" / "reasoning_log.jsonl"
TRADES_FILE = Path(__file__).parent / "agent_memory" / "trades_log.jsonl"

def load_candidates() -> pd.DataFrame:
    rows = []
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ["fabio_confidence", "andrea_confidence", "bar_volume", "bar_delta", "ib_range"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df["decision"]     = df["decision"].fillna("pending")
    df["fabio_setup"]  = df["fabio_setup"].fillna("none")
    df["proximity_to"] = df["proximity_to"].fillna("unknown")
    df["day_type"]     = df["day_type"].fillna("unknown")
    return df

def load_trades() -> pd.DataFrame:
    rows = []
    if TRADES_FILE.exists():
        with open(TRADES_FILE, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ["pnl_usd", "pnl_ticks", "r_ratio"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df_c  = load_candidates()
df_t  = load_trades()

n_cand    = len(df_c)
n_days    = df_c["date"].nunique() if not df_c.empty else 0
n_trades  = len(df_t)
total_pnl = float(df_t["pnl_usd"].sum()) if not df_t.empty else 0.0
avg_conf  = float(df_c["fabio_confidence"].mean()) if not df_c.empty else 0.0
win_rate  = float((df_t["pnl_usd"] > 0).mean() * 100) if not df_t.empty else 0.0

# ── Colours ────────────────────────────────────────────────────────────────────
BG    = "#0f172a"
CARD  = "#1e293b"
BORD  = "#334155"
TEXT  = "#e2e8f0"
MUTED = "#94a3b8"
GREEN = "#22c55e"
RED   = "#ef4444"
BLUE  = "#60a5fa"
PURP  = "#a78bfa"
YEL   = "#facc15"
ORAN  = "#f97316"

LO = dict(paper_bgcolor=CARD, plot_bgcolor=CARD,
          font=dict(color=TEXT, family="monospace", size=12),
          margin=dict(l=28, r=16, t=36, b=24))

# ── Figures ────────────────────────────────────────────────────────────────────
def kpi_fig(value, label, color, prefix="", suffix="", fmt=".0f"):
    fig = go.Figure(go.Indicator(
        mode="number", value=value,
        number={"prefix": prefix, "suffix": suffix,
                "valueformat": fmt,
                "font": {"size": 44, "color": color, "family": "monospace"}},
        title={"text": label, "font": {"size": 11, "color": MUTED}},
        domain={"x": [0, 1], "y": [0.15, 1]},
    ))
    fig.update_layout(**LO, height=130)
    return fig

def fig_confidence_gauge():
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_conf,
        gauge={"axis": {"range": [0, 100], "tickcolor": MUTED, "tickfont": {"color": MUTED}},
               "bar": {"color": BLUE},
               "bgcolor": BG,
               "steps": [{"range": [0, 40], "color": "#1e293b"},
                         {"range": [40, 65], "color": "#1e3a5f"},
                         {"range": [65, 100], "color": "#14532d"}],
               "threshold": {"line": {"color": YEL, "width": 3},
                             "thickness": 0.85, "value": 65}},
        number={"font": {"size": 28, "color": BLUE}},
        title={"text": "Avg Fabio Confidence", "font": {"size": 11, "color": MUTED}},
    ))
    fig.update_layout(**LO, height=200)
    return fig

def fig_candidates_per_day():
    if df_c.empty:
        return _empty("Candidates Per Day")
    day = df_c.groupby(["date","decision"]).size().reset_index(name="count")
    fig = px.bar(day, x="date", y="count", color="decision",
                 color_discrete_map={"no_trade": RED, "trade": GREEN, "pending": YEL},
                 title="Candidates Per Day",
                 labels={"date": "", "count": "N", "decision": ""})
    fig.update_layout(**LO, xaxis_tickangle=-30,
                      legend=dict(orientation="h", y=1.1, font=dict(size=11)))
    return fig

def fig_pnl_curve():
    if df_t.empty:
        fig = _empty("Cumulative P&L")
        fig.add_annotation(text="No closed trades yet", x=0.5, y=0.5,
                           showarrow=False, font=dict(color=MUTED, size=14))
        return fig
    df = df_t.copy()
    df["cum"] = df["pnl_usd"].cumsum()
    df["n"]   = range(1, len(df)+1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["n"], y=df["cum"], mode="lines+markers",
                             line=dict(color=GREEN, width=2),
                             marker=dict(color=GREEN, size=7),
                             fill="tozeroy", fillcolor="rgba(34,197,94,0.08)"))
    fig.add_hline(y=0, line_dash="dash", line_color=MUTED)
    fig.update_layout(**LO, title="Cumulative P&L ($)",
                      xaxis_title="Trade #", yaxis_title="$")
    return fig

def fig_day_type():
    if df_c.empty:
        return _empty("Day Type")
    dt = df_c.drop_duplicates("date")["day_type"].value_counts().reset_index()
    dt.columns = ["Day Type", "Count"]
    cm = {"balance": MUTED, "trend_up": GREEN, "trend_down": RED, "unknown": "#475569"}
    fig = px.pie(dt, names="Day Type", values="Count",
                 color="Day Type", color_discrete_map=cm,
                 title="Day Type Distribution", hole=0.5)
    fig.update_traces(textinfo="label+percent", textfont_color=TEXT)
    fig.update_layout(**LO)
    return fig

def fig_proximity():
    if df_c.empty:
        return _empty("Proximity")
    counts = df_c["proximity_to"].value_counts().reset_index()
    counts.columns = ["Level", "Count"]
    cm = {"poc": PURP, "va_high": BLUE, "va_low": GREEN,
          "ib_high": ORAN, "ib_low": "#fb923c",
          "hvn": YEL, "lvn": RED, "unknown": MUTED}
    fig = px.bar(counts, x="Level", y="Count", color="Level",
                 color_discrete_map=cm,
                 title="Proximity to VP Level",
                 labels={"Level": "", "Count": "N"})
    fig.update_layout(**LO, showlegend=False)
    return fig

def fig_confidence_hist():
    if df_c.empty:
        return _empty("Confidence Distribution")
    fig = px.histogram(df_c, x="fabio_confidence", nbins=20,
                       color="decision",
                       color_discrete_map={"no_trade": RED, "trade": GREEN, "pending": YEL},
                       title="Fabio Confidence Distribution",
                       labels={"fabio_confidence": "Confidence", "count": "N"})
    fig.add_vline(x=65, line_dash="dash", line_color=YEL,
                  annotation_text="Threshold (65)",
                  annotation_font_color=YEL, annotation_position="top right")
    fig.update_layout(**LO, legend=dict(orientation="h", y=1.1, font=dict(size=11)))
    return fig

def fig_setup_types():
    if df_c.empty:
        return _empty("Setup Types")
    counts = df_c["fabio_setup"].value_counts().reset_index()
    counts.columns = ["Setup", "Count"]
    cm = {"squeeze": PURP, "ivb_breakout": BLUE, "second_drive": GREEN, "none": MUTED}
    fig = px.bar(counts, x="Setup", y="Count", color="Setup",
                 color_discrete_map=cm, title="Setup Types (Fabio)",
                 labels={"Setup": "", "Count": "N"})
    fig.update_layout(**LO, showlegend=False)
    return fig

def fig_delta_scatter():
    if df_c.empty:
        return _empty("Delta vs Confidence")
    fig = px.scatter(df_c, x="fabio_confidence", y="bar_delta",
                     color="proximity_to", size="bar_volume", size_max=22,
                     hover_data=["date", "bar_time_et", "fabio_setup", "decision"],
                     title="Delta vs Confidence  (size = volume)",
                     labels={"fabio_confidence": "Confidence", "bar_delta": "Delta"})
    fig.add_vline(x=65, line_dash="dash", line_color=YEL)
    fig.add_hline(y=0, line_dash="dot", line_color=MUTED)
    fig.update_layout(**LO)
    return fig

def fig_ib_range():
    if df_c.empty:
        return _empty("IB Range")
    d = df_c.drop_duplicates("date")[["date","ib_range"]].sort_values("date")
    fig = px.bar(d, x="date", y="ib_range",
                 color="ib_range", color_continuous_scale="Blues",
                 title="IB Range by Day (pts)",
                 labels={"date": "", "ib_range": "IB Range"})
    fig.update_layout(**LO, coloraxis_showscale=False, xaxis_tickangle=-30)
    return fig

def _empty(title):
    fig = go.Figure()
    fig.update_layout(**LO, title=title)
    return fig

# ── Table ──────────────────────────────────────────────────────────────────────
TABLE_COLS = ["date","bar_time_et","day_type","proximity_to",
              "fabio_confidence","fabio_setup","fabio_direction",
              "decision","bar_volume","bar_delta"]
table_df = df_c[TABLE_COLS].copy() if not df_c.empty and all(c in df_c.columns for c in TABLE_COLS) else pd.DataFrame(columns=TABLE_COLS)
table_df.columns = ["Date","Time (ET)","Day","Near Lvl","Conf","Setup","Dir","Decision","Vol","Δ"]

CSTYLE = [{"if": {"row_index": "odd"}, "backgroundColor": "#162032"},
          {"if": {"filter_query": '{Decision} = "trade"'}, "backgroundColor": "#14532d", "color": GREEN},
          {"if": {"filter_query": '{Decision} = "no_trade"'}, "color": MUTED},
          {"if": {"column_id": "Conf", "filter_query": "{Conf} > 64"}, "color": GREEN, "fontWeight": "bold"},
          {"if": {"column_id": "Δ", "filter_query": "{Δ} < 0"}, "color": RED},
          {"if": {"column_id": "Δ", "filter_query": "{Δ} > 0"}, "color": GREEN}]

# ── Card helper ────────────────────────────────────────────────────────────────
def card(content):
    return html.Div(content, style={
        "backgroundColor": CARD, "borderRadius": "10px",
        "border": f"1px solid {BORD}", "padding": "8px",
    })

def graph_card(fig, h=None):
    style = {"height": f"{h}px"} if h else {}
    return card(dcc.Graph(figure=fig, config={"displayModeBar": False}, style=style))

# ── Layout ─────────────────────────────────────────────────────────────────────
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

app.layout = html.Div(style={"backgroundColor": BG, "minHeight": "100vh",
                              "fontFamily": "monospace", "color": TEXT, "padding": "16px"}, children=[

    # Header
    html.Div([
        html.H2("⚡ NQ Futures Backtest", style={"color": BLUE, "margin": "0 0 4px 0"}),
        html.Span("Multi-Agent System  ·  Fabio + Andrea  ·  M5 Candle Analysis",
                  style={"color": MUTED, "fontSize": "12px"}),
    ], style={"marginBottom": "16px"}),

    # ── KPI Row ──────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(graph_card(kpi_fig(n_cand,   "CANDIDATES",  BLUE)),  width=2),
        dbc.Col(graph_card(kpi_fig(n_days,   "DAYS",        PURP)),  width=2),
        dbc.Col(graph_card(kpi_fig(n_trades, "TRADES",      GREEN)), width=2),
        dbc.Col(graph_card(kpi_fig(total_pnl,"P&L ($)",    GREEN if total_pnl>=0 else RED, "$", fmt=",.0f")), width=2),
        dbc.Col(graph_card(kpi_fig(win_rate, "WIN RATE",    GREEN, suffix="%", fmt=".1f")), width=2),
        dbc.Col(graph_card(kpi_fig(avg_conf, "AVG CONF",    BLUE,  fmt=".1f")), width=2),
    ], className="mb-3"),

    # ── Row 1 ─────────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(graph_card(fig_candidates_per_day(), 260), width=5),
        dbc.Col(graph_card(fig_pnl_curve(),          260), width=4),
        dbc.Col(graph_card(fig_day_type(),           260), width=3),
    ], className="mb-3"),

    # ── Row 2 ─────────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(graph_card(fig_proximity(),      240), width=4),
        dbc.Col(graph_card(fig_ib_range(),       240), width=4),
        dbc.Col(graph_card(fig_confidence_gauge(), 240), width=4),
    ], className="mb-3"),

    # ── Section header ────────────────────────────────────────────────────────
    html.Div("Signal Analysis", style={"color": PURP, "fontWeight": "bold",
             "fontSize": "13px", "marginBottom": "8px", "letterSpacing": "2px"}),

    # ── Row 3 ─────────────────────────────────────────────────────────────────
    dbc.Row([
        dbc.Col(graph_card(fig_confidence_hist(), 280), width=5),
        dbc.Col(graph_card(fig_setup_types(),     280), width=3),
        dbc.Col(graph_card(fig_delta_scatter(),   280), width=4),
    ], className="mb-3"),

    # ── Reasoning Display ─────────────────────────────────────────────────────
    html.Div("Reasoning Log", style={"color": PURP, "fontWeight": "bold",
             "fontSize": "13px", "marginBottom": "8px", "letterSpacing": "2px"}),
    card(html.Div(id="reasoning-output", style={"height": "200px", "overflowY": "auto"})),

    # ── Candidate Log Table ───────────────────────────────────────────────────
    html.Div("Candidate Log", style={"color": PURP, "fontWeight": "bold",
             "fontSize": "13px", "marginBottom": "8px", "letterSpacing": "2px"}),
    card(dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": BG, "color": BLUE,
                      "fontFamily": "monospace", "fontSize": "12px",
                      "fontWeight": "bold", "border": f"1px solid {BORD}"},
        style_cell={"backgroundColor": CARD, "color": TEXT,
                    "fontFamily": "monospace", "fontSize": "12px",
                    "border": f"1px solid {BORD}", "padding": "6px 10px",
                    "maxWidth": "180px", "overflow": "hidden",
                    "textOverflow": "ellipsis"},
        style_data_conditional=CSTYLE,
        page_size=20,
        sort_action="native",
        filter_action="native",
        tooltip_data=[{c: {"value": str(row[c]), "type": "markdown"}
                       for c in table_df.columns} for _, row in table_df.iterrows()],
        tooltip_duration=None,
    )),
    # Trades Log Table
    html.Div("Trades Log", style={"color": PURP, "fontWeight": "bold",
             "fontSize": "13px", "marginBottom": "8px", "letterSpacing": "2px"}),
    card(dash_table.DataTable(
        id="trades-table",
        data=df_t.to_dict("records"),
        columns=[{"name": c, "id": c} for c in df_t.columns],
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": BG, "color": BLUE,
                     "fontFamily": "monospace", "fontSize": "12px",
                     "fontWeight": "bold", "border": f"1px solid {BORD}"},
        style_cell={"backgroundColor": CARD, "color": TEXT,
                    "fontFamily": "monospace", "fontSize": "12px",
                    "border": f"1px solid {BORD}", "padding": "6px 10px",
                    "maxWidth": "180px", "overflow": "hidden",
                    "textOverflow": "ellipsis"},
        style_data_conditional=CSTYLE,
        page_size=20,
        sort_action="native",
        filter_action="native",
        tooltip_data=[{c: {"value": str(row[c]), "type": "markdown"}
                       for c in df_t.columns} for _, row in df_t.iterrows()],
        tooltip_duration=None,
        row_selectable="single",
        selected_rows=[],
    )),
    # Auto‑refresh interval (30 s)
    dcc.Interval(id="interval-component", interval=30*1000, n_intervals=0),
    ])

if __name__ == "__main__":
    print(f"\n  Dashboard ready -> http://localhost:8050\n")
    print(f"  Loaded: {n_cand} candidates  |  {n_days} days  |  {n_trades} trades")
    app.run(debug=False, port=8050, host="0.0.0.0")

# ── Callbacks ────────────────────────────────────────────────────────────────
@app.callback(
    Output("reasoning-output", "children"),
    Input("interval-component", "n_intervals"),
    Input("trades-table", "selected_rows"),
    State("trades-table", "data"),
)
def update_reasoning(interval, selected_rows, trades_data):
    """Refresh data and show reasoning for the selected trade.
    If no trade is selected, show the most recent reasoning entries.
    """
    # Reload latest data
    df_c = load_candidates()
    df_t = load_trades()
    if selected_rows:
        trade = trades_data[selected_rows[0]]
        date = trade.get("date")
        filtered = [r for r in df_c.to_dict(orient="records") if r.get("date") == date]
        content = html.Pre(json.dumps(filtered, indent=2))
    else:
        recent = df_c.tail(10).to_dict(orient="records")
        content = html.Pre(json.dumps(recent, indent=2))
    return content
