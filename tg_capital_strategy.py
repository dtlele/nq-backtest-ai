import backtrader as bt
from datetime import time

class TGCapitalStrategy(bt.Strategy):
    params = (
        ('ema_fast', 9),
        ('ema_med', 21),
        ('ema_slow', 50),
        ('ema_trend', 200),
        ('sl_pips', 10),
        ('rr_ratio', 20),
        ('london_open_hour', 8), # GMT
        ('london_open_minute', 0),
        ('killzone_duration_hours', 3),
    )

    def __init__(self):
        self.ema1 = bt.indicators.EMA(self.data.close, period=self.p.ema_fast)
        self.ema2 = bt.indicators.EMA(self.data.close, period=self.p.ema_med)
        self.ema3 = bt.indicators.EMA(self.data.close, period=self.p.ema_slow)
        self.ema4 = bt.indicators.EMA(self.data.close, period=self.p.ema_trend)

        self.order = None
        self.buyprice = None
        self.buycomm = None

    def in_killzone(self, time_obj):
        # Controlla se siamo nella London Killzone (es. 08:00 - 11:00 GMT)
        start_time = time(self.p.london_open_hour, self.p.london_open_minute)
        end_time = time(self.p.london_open_hour + self.p.killzone_duration_hours, self.p.london_open_minute)
        return start_time <= time_obj <= end_time

    def is_doji_or_hammer(self):
        # Identifica una candela con lunga shadow inferiore e corpo piccolo (bullish rejection)
        body = abs(self.data.close[0] - self.data.open[0])
        lower_wick = min(self.data.close[0], self.data.open[0]) - self.data.low[0]
        range_tot = self.data.high[0] - self.data.low[0]
        
        if range_tot == 0:
            return False
            
        # Condizione: ombra inferiore almeno il 50% del range, corpo massimo 25% del range
        return (lower_wick / range_tot > 0.5) and (body / range_tot < 0.25)

    def next(self):
        if self.order:
            return

        # Solo trade se siamo in posizione flat
        if not self.position:
            # 1. EMAs Stacking (Momentum Bullish)
            emas_stacked_bullish = self.ema1[0] > self.ema2[0] > self.ema3[0] > self.ema4[0]
            
            # 2. Killzone Temporale
            current_time = self.data.datetime.time()
            if not self.in_killzone(current_time):
                return
                
            # 3. Candela di conferma (Doji/Hammer che ritraccia sulle EMA ma chiude sopra)
            if emas_stacked_bullish and self.is_doji_or_hammer():
                # Il prezzo tocca le EMA e viene respinto al rialzo
                if self.data.low[0] <= self.ema2[0] and self.data.close[0] > self.ema2[0]:
                    
                    self.buyprice = self.data.close[0]
                    # Calcolo Stop Loss e Take Profit
                    sl_price = self.buyprice - (self.p.sl_pips * 0.0001) # Per coppie FX standard
                    tp_price = self.buyprice + (self.p.sl_pips * self.p.rr_ratio * 0.0001)
                    
                    self.order = self.buy()
                    self.sell(exectype=bt.Order.Stop, price=sl_price)
                    self.sell(exectype=bt.Order.Limit, price=tp_price)
                    
        else:
            # Invalidation exit manuale (es. candela chiude sotto l'EMA o la shadow)
            if self.data.close[0] < self.ema3[0]:
                self.close()

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TGCapitalStrategy)
    # Aggiungi qui i dati e il capitale
    # cerebro.run()
