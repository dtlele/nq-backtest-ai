import asyncio
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars

# Imposta PydanticAI / LiteLLM in modo che usi OpenRouter
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
if "OPENROUTER_API_KEY" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
    
from src.agents.executor import execute_trade_decision, MarketState
    
async def run_v2_backtest(csv_path: str):
    print(f"=== INIZIO BACKTEST V2 SUL FILE {os.path.basename(csv_path)} ===")
    
    # 1. Carica i dati grezzi
    print("1. Caricamento dati...")
    trades_raw = load_day(csv_path)
    if not trades_raw:
        print("Errore: nessun dato caricato.")
        return
        
    # 2. Aggrega a 5 minuti per valutazioni veloci (per il test)
    print("2. Aggregazione in barre a 5 minuti...")
    bars_5m = aggregate_to_bars(trades_raw, freq='5min')
    
    # Filtro solo orari NY (09:30 - 16:00 ET) per semplicità
    import pytz
    ET = pytz.timezone('America/New_York')
    
    ny_bars = []
    for b in bars_5m:
        et_time = b.timestamp.astimezone(ET)
        if 9 <= et_time.hour <= 15 or (et_time.hour == 16 and et_time.minute == 0):
            ny_bars.append(b)
            
    if not ny_bars:
        print("Nessuna barra trovata nell'orario RTH NY.")
        return
        
    print(f"   Trovate {len(ny_bars)} barre RTH.")
    
    # Esecuzione Agente PydanticAI su TUTTE le barre della giornata
    print("\n3. Esecuzione Agente PydanticAI sull'intera sessione...")
    
    # Calcolo IB farlocco/semplificato per test
    ib_high = max([b.high for b in ny_bars[:6]]) if len(ny_bars) >= 6 else ny_bars[0].high
    ib_low = min([b.low for b in ny_bars[:6]]) if len(ny_bars) >= 6 else ny_bars[0].low
    
    for i, bar in enumerate(ny_bars):
        # Determiniamo un trend banale
        trend = "balance"
        if bar.close > ib_high: trend = "trend_up"
        if bar.close < ib_low: trend = "trend_down"
        
        # Creiamo lo stato formale (MarketState pydantic)
        state = MarketState(
            timestamp=bar.timestamp.astimezone(ET).strftime('%H:%M'),
            close_price=bar.close,
            delta=bar.delta,
            volume=bar.volume,
            ib_high=ib_high,
            ib_low=ib_low,
            vwap=sum(b.close for b in ny_bars[:i+1]) / (i+1), # VWAP finto per test
            market_structure=trend
        )
        
        print(f"\n--- Barra {i+1} : {state.timestamp} ---")
        try:
            decision = await execute_trade_decision(state)
            print(f"  [RESULT] Action: {decision.action} (Confidenza: {decision.confidence_score})")
            print(f"  [REASON] {decision.reasoning}")
            if decision.stop_loss:
                print(f"  [LEVELS] Stop Loss: {decision.stop_loss} | Take Profit: {decision.take_profit}")
        except Exception as e:
            print(f"  [ERRORE AGENTE] {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, default='20250430', help='YYYYMMDD date to test')
    args = parser.parse_args()
    
    target_file = f"C:\\Users\\Mauro\\Documents\\databento-data\\glbx-mdp3-20250430.mbp-1.csv"
    
    # Cerca il file reale nella cartella
    data_dir = "C:\\Users\\Mauro\\Documents\\databento-data"
    found_file = None
    if os.path.exists(data_dir):
        for f in os.listdir(data_dir):
            if args.date in f and f.endswith(".csv"):
                found_file = os.path.join(data_dir, f)
                break
                
    if found_file:
        asyncio.run(run_v2_backtest(found_file))
    else:
        print(f"File dati per {args.date} non trovato in {data_dir}.")
