import pandas as pd

configs = ['A','B','C','D']
results = {}

for c in configs:
    try:
        tdf = pd.read_csv(f'output/whale_v8_config_{c}.csv')
    except FileNotFoundError:
        results[c] = None
        continue
    total = len(tdf)
    wins  = (tdf['net_pnl'] > 0).sum()
    wr    = wins / total * 100 if total > 0 else 0
    gw    = tdf[tdf['net_pnl'] > 0]['net_pnl'].sum()
    gl    = abs(tdf[tdf['net_pnl'] < 0]['net_pnl'].sum())
    pf    = gw / gl if gl > 0 else float('inf')
    tdf['eq'] = tdf['net_pnl'].cumsum()
    tdf['pk'] = tdf['eq'].cummax()
    maxdd = (tdf['pk'] - tdf['eq']).max()
    tp = (tdf['exit_reason'] == 'TP').sum()
    sl = (tdf['exit_reason'] == 'SL').sum()
    te = (tdf['exit_reason'] == 'TIME_EXIT').sum()
    results[c] = dict(total=total, wr=wr, pf=pf, net=tdf['net_pnl'].sum(), maxdd=maxdd, tp=tp, sl=sl, te=te)

print("=" * 70)
print("  WHALE v8 - CONFRONTO CONFIGURAZIONI (tick-by-tick)")
print("=" * 70)
print(f"{'Config':<6} {'Trade':>6} {'/gg':>5} {'WR%':>7} {'PF':>7} {'NetPnL':>10} {'MaxDD':>8}")
print("-" * 70)

labels = {
    'A': 'A: 70-190 wick>=1',
    'B': 'B: 50-200 wick>=0.5',
    'C': 'C: 40-250 wick>=0.5',
    'D': 'D: 50-200 no wick',
}

for c, r in results.items():
    if r is None:
        print(f"  {c} ({labels[c]}): NON ANCORA PRONTA")
    else:
        freq = r['total'] / 441
        print(f"  {c}  {r['total']:>6}  {freq:>5.1f}  {r['wr']:>6.1f}%  {r['pf']:>7.2f}  ${r['net']:>9,.0f}  ${r['maxdd']:>7,.0f}")
        print(f"     ({labels[c]}) -- TP:{r['tp']} SL:{r['sl']} TIME:{r['te']}")

print("=" * 70)
print("Target: ~1 trade/gg con WR > 70%")
