import os
import sys
import time
import pytz
import numpy as np
import pandas as pd
from datetime import datetime, time as datetime_time, timedelta
import MetaTrader5 as mt5

# Fuso orario di New York per i mercati USA (NQ Futures)
ET = pytz.timezone("America/New_York")

class MT5LiveBot:
    def __init__(self, symbol="MNQ*", account_balance=50000.0, broker_utc_offset_hours=2):
        """
        Inizializza il bot reale per MetaTrader 5 per NQ.
        
        :param symbol: Il simbolo dello strumento su MT5 (es. MNQU26, NQ, USTEC, NAS100)
        :param account_balance: Saldo iniziale stimato (usato come fallback se non riusciamo a leggere MT5)
        :param broker_utc_offset_hours: L'offset GMT/UTC del server del broker MT5 (di solito +2 o +3)
        """
        self.symbol = symbol
        self.account_balance = account_balance
        self.broker_utc_offset = timedelta(hours=broker_utc_offset_hours)
        
        # Rischio percentuale fisso sul saldo del conto per singolo setup
        self.risk_pcts = {
            "trend_long": 0.20,    # 0.20% del saldo del conto a rischio
            "absorb_long": 0.15,   # 0.15% del saldo del conto a rischio
            "trend_short": 0.25,   # 0.25% del saldo del conto a rischio
            "absorb_short": 0.15   # 0.15% del saldo del conto a rischio
        }
        
        # Stato della volatilità e parametri adattivi
        self.atr_5d = 0.0
        self.regime = "UNKNOWN"
        self.params = {}
        
        # Stato del mercato e della sessione (dalle 09:30 ET)
        self.session_started = False
        self.va_low = 0.0
        self.va_high = 0.0
        self.poc = 0.0
        self.overnight_va_low = 0.0
        self.overnight_va_high = 0.0
        self.session_cvd = 0
        self.mega_trades_levels = []  # Prezzi dei Mega Trades >= 300 contratti
        self.last_tick_time = 0      # Per tracciamento incrementale dei tick
        
        # Parametri SL/TP Ottimizzati per il 2025 (Bassa Volatilità, ATR < 200)
        self.low_vol_params = {
            "trend_long": {"direction": "long", "sl": 39.0, "tp": 120.0},
            "absorb_long": {"direction": "long", "sl": 49.0, "tp": 37.0},
            "trend_short": {"direction": "short", "sl": 46.0, "tp": 120.0},
            "absorb_short": {"direction": "short", "sl": 49.0, "tp": 114.0}
        }
        
        # Parametri SL/TP Ottimizzati per il 2026 (Alta Volatilità, ATR >= 200)
        self.high_vol_params = {
            "trend_long": {"direction": "long", "sl": 22.0, "tp": 113.0},
            "absorb_long": {"direction": "long", "sl": 50.0, "tp": 115.0},
            "trend_short": {"direction": "short", "sl": 48.0, "tp": 113.0},
            "absorb_short": {"direction": "short", "sl": 34.0, "tp": 35.0}
        }

    # --------------------------------------------------------------------------
    # 🔌 Inizializzazione & Utility di Tempo
    # --------------------------------------------------------------------------
    def start(self):
        """Avvia la connessione e calcola l'ATR pre-apertura."""
        if not mt5.initialize():
            print(f"[ERROR] Inizializzazione MT5 fallita: {mt5.last_error()}")
            return False
            
        print("[INFO] Connesso a MetaTrader 5 con successo.")
        
        # Seleziona il simbolo per verificare che esista
        selected = mt5.symbol_select(self.symbol, True)
        if not selected:
            print(f"[ERROR] Simbolo {self.symbol} non trovato o non selezionabile su MT5.")
            mt5.shutdown()
            return False
            
        # Calcola la volatilità pre-apertura (Regola 1)
        self.calculate_premarket_atr()
        # Calcola la Value Area Overnight all'avvio
        self.calculate_overnight_value_area()
        return True

    def get_et_time(self, server_timestamp):
        """Converte il timestamp del server MT5 in ora di New York (ET)."""
        # Converti il timestamp locale del server in ora UTC
        utc_dt = datetime.fromtimestamp(server_timestamp, pytz.utc) - self.broker_utc_offset
        # Converti UTC in ET
        return utc_dt.astimezone(ET)

    def calculate_overnight_value_area(self):
        """
        Calcola la Value Area della sessione Overnight (dalle 00:00 alle 09:30 ET di oggi)
        usando le barre M1 storiche di MT5.
        """
        print("[INFO] Calcolo della Value Area Overnight (00:00 - 09:30 ET)...")
        # Trova la data odierna a New York
        ny_today = datetime.now(ET).date()
        
        # 00:00 ET di oggi
        ny_start_et = ET.localize(datetime.combine(ny_today, datetime_time(0, 0)))
        # 09:30 ET di oggi (inizio RTH)
        ny_end_et = ET.localize(datetime.combine(ny_today, datetime_time(9, 30)))
        
        # Converti in ora server
        start_server = (ny_start_et.astimezone(pytz.utc) + self.broker_utc_offset).replace(tzinfo=None)
        end_server = (ny_end_et.astimezone(pytz.utc) + self.broker_utc_offset).replace(tzinfo=None)
        
        # Scarica barre M1
        rates = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M1, start_server, end_server)
        if rates is None or len(rates) == 0:
            print("[WARNING] Dati Overnight non disponibili. Il filtro VA si attiverà solo dopo le 10:00 ET.")
            return
            
        # Calcolo del Volume Profile Overnight
        tick_size = 0.25
        va_percentage = 0.70
        price_vol = {}
        
        for bar in rates:
            p_low = round(bar['low'] / tick_size) * tick_size
            p_high = round(bar['high'] / tick_size) * tick_size
            ticks = max(1, round((p_high - p_low) / tick_size) + 1)
            vol_per_tick = bar['tick_volume'] / ticks
            
            price = p_low
            while price <= p_high + 1e-9:
                key = round(price / tick_size) * tick_size
                price_vol[key] = price_vol.get(key, 0.0) + vol_per_tick
                price += tick_size
                
        if not price_vol:
            return
            
        sorted_prices = sorted(price_vol.keys())
        volumes = [price_vol[p] for p in sorted_prices]
        total_vol = sum(volumes)
        
        poc_idx = int(np.argmax(volumes))
        
        va_vol = volumes[poc_idx]
        lo_idx = hi_idx = poc_idx
        
        while va_vol / total_vol < va_percentage:
            add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
            add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
            
            if add_hi >= add_lo and hi_idx < len(volumes) - 1:
                hi_idx += 1
                va_vol += add_hi
            elif lo_idx > 0:
                lo_idx -= 1
                va_vol += add_lo
            else:
                break
                
        self.overnight_va_high = sorted_prices[hi_idx]
        self.overnight_va_low = sorted_prices[lo_idx]
        print(f"[INFO] Value Area Overnight calcolata: {self.overnight_va_low:.2f} - {self.overnight_va_high:.2f}")

    # --------------------------------------------------------------------------
    # 📊 Regola 1: Rilevatore di Regime di Volatilità (ATR storico 5 giorni)
    # --------------------------------------------------------------------------
    def calculate_premarket_atr(self):
        """
        Calcola l'ATR a 5 giorni di D1 pre-apertura per NQ.
        Regola: se ATR < 200 pt -> Parametri 2025; se ATR >= 200 pt -> Parametri 2026.
        """
        print("[INFO] Rilevamento regime di volatilità pre-apertura...")
        
        # Recupera le ultime 5 barre D1 complete (escludendo la candela corrente di oggi)
        rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_D1, 1, 5)
        if rates is None or len(rates) < 5:
            print("[WARNING] Dati giornalieri storici insufficienti. Caricamento parametri predefiniti 2026 (HIGH).")
            self.params = self.high_vol_params
            self.regime = "HIGH (Default)"
            return
            
        df = pd.DataFrame(rates)
        df['range'] = df['high'] - df['low']
        self.atr_5d = df['range'].mean()
        
        print(f"[INFO] ATR storico a 5 giorni calcolato: {self.atr_5d:.2f} punti.")
        
        if self.atr_5d < 200.0:
            self.params = self.low_vol_params
            self.regime = "LOW_VOLATILITY (Parametri 2025)"
            print(">>> REGIME SELEZIONATO: Bassa Volatilità (< 200 pt). Caricati parametri SL/TP del 2025.")
        else:
            self.params = self.high_vol_params
            self.regime = "HIGH_VOLATILITY (Parametri 2026)"
            print(">>> REGIME SELEZIONATO: Alta Volatilità (>= 200 pt). Caricati parametri SL/TP del 2026.")

    # --------------------------------------------------------------------------
    # 🏛️ Regola 2: Calcolo della Value Area & Inibizione SHORT inside Value Area
    # --------------------------------------------------------------------------
    def update_value_area(self):
        """
        Scarica le barre M1 dall'apertura RTH (09:30 ET) e ricalcola
        il Volume Profile di sessione, aggiornando VAL (va_low) e VAH (va_high).
        """
        now = datetime.now()
        # Ora di inizio sessione odierna (09:30 ET) convertita in ora locale del server broker
        # 1. Determiniamo la data odierna a New York
        ny_today = datetime.now(ET).date()
        ny_open_et = ET.localize(datetime.combine(ny_today, time(9, 30)))
        
        # Convertiamo l'apertura delle 9:30 ET in UTC e poi in server time
        open_utc = ny_open_et.astimezone(pytz.utc)
        open_server = open_utc + self.broker_utc_offset
        open_server_naive = open_server.replace(tzinfo=None)
        
        # Se non siamo ancora nell'orario RTH (prima delle 09:30 ET), il calcolo è saltato
        if datetime.now(ET) < ny_open_et:
            # Siamo in pre-market
            self.va_low, self.va_high, self.poc = 0.0, 0.0, 0.0
            return

        # Scarichiamo tutte le barre M1 da 09:30 ad adesso
        rates = mt5.copy_rates_from(self.symbol, mt5.TIMEFRAME_M1, open_server_naive, datetime.now())
        if rates is None or len(rates) == 0:
            return
            
        # Calcolo del Volume Profile
        tick_size = 0.25
        va_percentage = 0.70
        price_vol = {}
        
        for bar in rates:
            p_low = round(bar['low'] / tick_size) * tick_size
            p_high = round(bar['high'] / tick_size) * tick_size
            ticks = max(1, round((p_high - p_low) / tick_size) + 1)
            vol_per_tick = bar['tick_volume'] / ticks  # Su MT5 tick_volume = volume scambiato per CFD/Futures
            
            price = p_low
            while price <= p_high + 1e-9:
                key = round(price / tick_size) * tick_size
                price_vol[key] = price_vol.get(key, 0.0) + vol_per_tick
                price += tick_size
                
        if not price_vol:
            return
            
        sorted_prices = sorted(price_vol.keys())
        volumes = [price_vol[p] for p in sorted_prices]
        total_vol = sum(volumes)
        
        poc_idx = int(np.argmax(volumes))
        self.poc = sorted_prices[poc_idx]
        
        # Espansione da POC per catturare il 70% del volume
        va_vol = volumes[poc_idx]
        lo_idx = hi_idx = poc_idx
        
        while va_vol / total_vol < va_percentage:
            add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
            add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
            
            if add_hi >= add_lo and hi_idx < len(volumes) - 1:
                hi_idx += 1
                va_vol += add_hi
            elif lo_idx > 0:
                lo_idx -= 1
                va_vol += add_lo
            else:
                break
                
        self.va_high = sorted_prices[hi_idx]
        self.va_low = sorted_prices[lo_idx]

    def is_inside_value_area(self, price):
        """Restituisce True se il prezzo attuale si trova all'interno della Value Area di sessione."""
        if self.va_low == 0.0 or self.va_high == 0.0:
            return False
        return self.va_low < price < self.va_high

    # --------------------------------------------------------------------------
    # 📉 Regola 3 & 4: Monitoraggio Tick, CVD Climax e Mega Trades
    # --------------------------------------------------------------------------
    def sync_ticks_and_flows(self):
        """
        Sincronizza i tick di sessione a partire dalle 09:30 ET per calcolare:
        - Il CVD (Cumulative Volume Delta) di sessione
        - I livelli di prezzo dei Mega Trades (ordini >= 300 contratti)
        """
        ny_today = datetime.now(ET).date()
        ny_open_et = ET.localize(datetime.combine(ny_today, time(9, 30)))
        
        if datetime.now(ET) < ny_open_et:
            return  # Non calcolare prima delle 09:30 ET
            
        open_utc = ny_open_et.astimezone(pytz.utc)
        open_server = open_utc + self.broker_utc_offset
        open_server_naive = open_server.replace(tzinfo=None)
        
        # Scarica i tick dall'apertura o dall'ultimo tick elaborato
        start_time = max(open_server_naive, datetime.fromtimestamp(self.last_tick_time))
        ticks = mt5.copy_ticks_from(self.symbol, start_time, 10000, mt5.COPY_TICKS_ALL)
        
        if ticks is None or len(ticks) == 0:
            return
            
        # Filtra solo i tick successivi a self.last_tick_time
        ticks_filtered = [t for t in ticks if t['time'] > self.last_tick_time]
        if not ticks_filtered:
            return
            
        for t in ticks_filtered:
            price = t['last']
            volume = t['volume']
            flags = t['flags']
            
            # Identificazione del delta volumetrico del tick (Buy vs Sell volume)
            # flag 56 = TICK_FLAG_BUY (eseguito su Ask), flag 88 = TICK_FLAG_SELL (eseguito su Bid)
            is_buy = (flags & mt5.TICK_FLAG_BUY) == mt5.TICK_FLAG_BUY
            is_sell = (flags & mt5.TICK_FLAG_SELL) == mt5.TICK_FLAG_SELL
            
            if is_buy:
                self.session_cvd += volume
            elif is_sell:
                self.session_cvd -= volume
                
            # Regola 4: Rilevamento Mega Trades >= 300 contratti
            if volume >= 300:
                self.mega_trades_levels.append(price)
                print(f"[INSTITUTIONAL] Mega Trade rilevato: {volume} contratti a {price:.2f} (Time: {self.get_et_time(t['time'])} ET).")
                
        # Aggiorna il timestamp dell'ultimo tick processato
        self.last_tick_time = int(ticks_filtered[-1]['time'])

    def calculate_position_size(self, setup_name, price, sl_points):
        """
        Calcola dinamicamente la size (in lotti per CFD o contratti per Futures) da negoziare basandosi su:
        1. Il rischio percentuale assegnato a quel setup.
        2. Lo Stop Loss in punti.
        3. Le specifiche del simbolo fornite in tempo reale dal broker di CFD (MT5).
        4. Lo size scaling volumetrico (se è un assorbimento vicino a un Mega Level, raddoppia il rischio).
        """
        # Ottieni le informazioni del simbolo e del conto da MT5
        symbol_info = mt5.symbol_info(self.symbol)
        account_info = mt5.account_info()
        
        balance = account_info.balance if account_info is not None else self.account_balance
        
        # Recupera il rischio base
        risk_pct = self.risk_pcts.get(setup_name, 0.15)
        
        # Regola 4: Se è un setup ad assorbimento, controlla la prossimità a Mega Levels
        if "absorb" in setup_name and self.mega_trades_levels:
            min_dist = min(abs(price - lvl) for lvl in self.mega_trades_levels)
            if min_dist <= 15.0:
                # Raddoppia il rischio per sfruttare l'alto edge dell'assorbimento istituzionale
                risk_pct = risk_pct * 2.0
                print(f"[SIZE SCALING] Prezzo vicino a Mega Level (dist: {min_dist:.2f} pt). Rischio raddoppiato a {risk_pct:.2f}%.")
            else:
                # Se siamo lontani dai Mega Trades, dimezza il rischio per cautela
                risk_pct = risk_pct * 0.5
                print(f"[SIZE SCALING] Prezzo lontano dai Mega Levels (dist: {min_dist:.2f} pt). Rischio ridotto a {risk_pct:.2f}%.")
                
        # Calcolo ammontare a rischio in USD
        risk_amount_usd = balance * (risk_pct / 100.0)
        
        # Rileva dinamicamente il valore per punto del broker (CFD vs Futures)
        if symbol_info is not None:
            # Formula generica ed esatta per MT5 (CFD o Futures)
            # trade_tick_value: valore monetario di 1 tick per 1 lotto
            # trade_tick_size: dimensione in punti di 1 tick
            point_value = symbol_info.trade_tick_value / symbol_info.trade_tick_size
            min_volume = symbol_info.volume_min
            max_volume = symbol_info.volume_max
            volume_step = symbol_info.volume_step
        else:
            # Fallback predefinito per MNQ se MT5 non risponde
            point_value = 2.0
            min_volume = 1.0
            max_volume = 100.0
            volume_step = 1.0

        if sl_points <= 0:
            return min_volume
            
        # Calcolo della size grezza (lotti o contratti)
        raw_size = risk_amount_usd / (sl_points * point_value)
        
        # Applica l'arrotondamento e i limiti del broker (fondamentale per i CFD con lotti decimali)
        # Esempio: se volume_step = 0.01 (CFD), arrotonda a 2 cifre decimali
        decimal_places = int(round(-np.log10(volume_step))) if volume_step > 0 else 0
        final_size = max(min_volume, min(max_volume, round(raw_size, decimal_places)))
        
        # Forza la size a rispettare la granularità dello step (es. multiplo di 0.01 o 0.10)
        final_size = round(final_size / volume_step) * volume_step
        
        # Calcolo rischio effettivo per logging
        actual_risk_usd = final_size * sl_points * point_value
        actual_risk_pct = (actual_risk_usd / balance) * 100.0
        
        print(f"[RISK MANAGER CFD] Saldo: ${balance:,.2f} | Rischio target: {risk_pct:.2f}% (${risk_amount_usd:.2f}) | SL: {sl_points} pt | Point Value/Lot: ${point_value:.2f} | Size Eseguita: {final_size:.2f} lotti (Rischio effettivo: {actual_risk_pct:.2f}% - ${actual_risk_usd:.2f})")
        return final_size

    # --------------------------------------------------------------------------
    # ⚙️ Motore Decisionale e Filtri di Esecuzione
    # --------------------------------------------------------------------------
    def validate_and_execute(self, setup_name, signal_direction, entry_price):
        """
        Valuta i filtri quantitativi definitivi prima di inoltrare l'ordine.
        
        :param setup_name: Il nome del setup ('trend_long', 'absorb_long', 'trend_short', 'absorb_short')
        :param signal_direction: Direzione del segnale ('long' o 'short')
        :param entry_price: Prezzo di ingresso proposto
        :return: True se l'ordine viene inoltrato, False se viene filtrato/bloccato.
        """
        if not self.params:
            print("[ERROR] Impossibile eseguire: Parametri del regime di volatilità non inizializzati.")
            return False
            
        # Sincronizza i dati e ricalcola i filtri prima di verificare
        self.update_value_area()
        self.sync_ticks_and_flows()
        
        print(f"\n⚡ [VALUTAZIONE SEGNALE LIVE] Setup: {setup_name.upper()} | Direzione: {signal_direction.upper()}")
        print(f"   Prezzo attuale: {entry_price:.2f} | Session CVD: {self.session_cvd} | VA: {self.va_low:.2f} - {self.va_high:.2f}")
        
        # 1. Filtro CVD Climax (Regola 3)
        # Se il CVD assoluto è >= 1200 contratti, blocca le entrate per rischio esaurimento/climax.
        if abs(self.session_cvd) >= 1200:
            print(f"❌ [RIGETTATO] Filtro CVD Climax attivo: abs(session_cvd) = {abs(self.session_cvd)} >= 1200 contratti.")
            return False
            
        # 2. Inibizione SHORT inside Value Area (Regola 2)
        # Se il segnale è SHORT (sia trend che absorption) e il prezzo è compreso tra VAL e VAH, blocca l'operazione.
        if signal_direction == "short" and self.is_inside_value_area(entry_price):
            print(f"❌ [RIGETTATO] Filtro Value Area attivo: Gli SHORT dentro la Value Area ({self.va_low:.2f} - {self.va_high:.2f}) sono inibiti.")
            return False
            
        # Carica i parametri SL/TP del regime corrente
        setup_config = self.params.get(setup_name)
        if not setup_config:
            print(f"[ERROR] Configurazione non trovata per il setup: {setup_name}")
            return False
            
        sl_points = setup_config["sl"]
        tp_points = setup_config["tp"]
        
        # 3. Calcolo dinamico della Size in base al rischio percentuale (Regola 4 integrata)
        contracts = self.calculate_position_size(setup_name, entry_price, sl_points)
            
        # 4. Invio dell'ordine bracket su MT5
        print(f"✅ [APPROVATO] Tutti i filtri superati. Invio ordine bracket in corso...")
        self.send_bracket_order(signal_direction, entry_price, sl_points, tp_points, contracts)
        return True

    def send_bracket_order(self, direction, price, sl_pts, tp_pts, contracts):
        """Invia un ordine con SL e TP protettivi a MT5 (OCO Bracket)."""
        if direction == "long":
            order_type = mt5.ORDER_TYPE_BUY
            sl_price = price - sl_pts
            tp_price = price + tp_pts
        else:
            order_type = mt5.ORDER_TYPE_SELL
            sl_price = price + sl_pts
            tp_price = price - tp_pts
            
        # Costruzione della richiesta d'ordine
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(contracts),
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": 10,
            "magic": 1012026,
            "comment": f"Antigravity {self.regime[:4]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[ERROR] Invio ordine fallito. Codice: {result.retcode} | {result.comment}")
        else:
            print(f"🚀 [ORDINE INVIATO] Successo! Ticket: {result.order} | Symbol: {self.symbol} | Size: {contracts} | Tipo: {direction.upper()} | Ingresso: {price:.2f} | SL: {sl_price:.2f} | TP: {tp_price:.2f}")

    def loop(self):
        """Loop di monitoraggio in tempo reale del mercato per aggiornare filtri e flussi."""
        print(f"[INFO] Avvio del loop in tempo reale per {self.symbol}...")
        try:
            while True:
                # Controlla la connessione
                if not mt5.terminal_info():
                    print("[WARNING] Connessione a MT5 persa. Riconnessione in corso...")
                    mt5.initialize()
                    
                # Aggiorna la Value Area e il CVD/Mega Trades
                self.update_value_area()
                self.sync_ticks_and_flows()
                
                # Output di debug periodico
                print(f"[LIVE STATUS] Prezzo: {mt5.symbol_info_tick(self.symbol).last:.2f} | CVD: {self.session_cvd} | VAL: {self.va_low:.2f} | VAH: {self.va_high:.2f} | Mega Trades Rilevati: {len(self.mega_trades_levels)}", end="\r")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] Bot arrestato manualmente.")
        finally:
            self.shutdown()

    def shutdown(self):
        """Chiude la sessione MT5."""
        mt5.shutdown()
        print("[INFO] Connessione MT5 chiusa.")

if __name__ == "__main__":
    # Test del bot
    bot = MT5LiveBot(symbol="MNQM26", broker_utc_offset_hours=3) # Sostituire con il simbolo NQ/MNQ attivo del broker
    if bot.start():
        # Esegui il loop di monitoraggio dei dati in tempo reale
        bot.loop()
