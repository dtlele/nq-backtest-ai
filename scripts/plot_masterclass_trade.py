import os
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta
import pytz
import sys

sys.path.insert(0, 'C:/Users/Mauro/Documents/nq-backtest')
from src.data_loader import load_day
from src.range_builder import build_range_bars
from src.volume_profile import build_profile_from_bars

def main():
    date_str = "20251218"
    file_path = f"C:/Users/Mauro/Documents/databento-data/glbx-mdp3-{date_str}.trades.csv"
    print("Caricamento dati...")
    df = load_day(file_path)
    
    print("Costruzione Range Bars (10 punti)...")
    bars = build_range_bars(df, 10.0, big_trade_threshold=30)
    
    NY_TZ = pytz.timezone("America/New_York")
    
    # Extract bars between 09:30 and 12:30 NY time
    plot_bars = []
    for b in bars:
        dt = b.timestamp.astimezone(NY_TZ)
        if (dt.hour > 9 or (dt.hour == 9 and dt.minute >= 30)) and dt.hour < 13:
            plot_bars.append(b)
            
    if not plot_bars:
        print("Nessuna barra trovata nell'orario RTH per il grafico.")
        return

    # Calculate LVN zones from 09:30 to 11:58
    comp_bars = [b for b in plot_bars if b.timestamp.astimezone(NY_TZ).strftime('%H:%M:%S') <= "11:58:18"]
    lvn_zones = []
    if comp_bars:
        vp = build_profile_from_bars(comp_bars)
        if vp:
            lvn_zones = vp.lvn_levels
            
    print(f"Zone LVN trovate: {lvn_zones}")

    # Prepare Plotly Data
    times = [b.timestamp.astimezone(NY_TZ).strftime('%H:%M:%S') for b in plot_bars]
    opens = [b.open for b in plot_bars]
    highs = [b.high for b in plot_bars]
    lows = [b.low for b in plot_bars]
    closes = [b.close for b in plot_bars]

    fig = go.Figure(data=[go.Candlestick(x=times,
                    open=opens,
                    high=highs,
                    low=lows,
                    close=closes,
                    name='Range Bars')])

    # Add LVN Zones as horizontal lines
    for lvn in lvn_zones:
        fig.add_hline(y=lvn, line_width=1, line_dash="dash", line_color="purple", opacity=0.5, annotation_text="LVN")

    # Mark the specific trade at 11:58
    trade_idx = -1
    for i, t in enumerate(times):
        if t.startswith("11:58"):
            trade_idx = i
            break
            
    if trade_idx != -1:
        fig.add_annotation(
            x=times[trade_idx],
            y=highs[trade_idx] + 5,
            xref="x",
            yref="y",
            text="Masterclass SHORT Trade!",
            showarrow=True,
            font=dict(
                family="Courier New, monospace",
                size=16,
                color="#ffffff"
            ),
            align="center",
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#ff0000",
            ax=20,
            ay=-40,
            bordercolor="#c7c7c7",
            borderwidth=2,
            borderpad=4,
            bgcolor="#ff7f0e",
            opacity=0.8
        )
        
    # Update layout
    fig.update_layout(
        title='NQ Range Bars - 18 Dicembre 2025 - Masterclass Trade',
        yaxis_title='Price',
        xaxis_title='Time',
        template='plotly_dark',
        height=800
    )
    
    out_html = "C:/Users/Mauro/Documents/nq-backtest/output/masterclass_trade_dec18.html"
    fig.write_html(out_html)
    print(f"Grafico interattivo salvato in: {out_html}")
    
if __name__ == "__main__":
    main()
