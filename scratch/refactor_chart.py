import os

path = "dashboard/src/components/TradingChart.jsx"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_use_effect = False
skip_mode = False

system_overlays_code = """
  // -----------------------------------------------------
  // System Overlays useEffect (updates dynamically)
  // -----------------------------------------------------
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !data || !data.m1_ny) return;

    const candles = data.m1_ny;
    const formattedCandles = candles.map(c => ({ timestamp: c.time * 1000, low: c.low, high: c.high }));

    // Remove old system overlays
    const overlays = chart.getOverlays();
    overlays.forEach(o => {
      if (o.id && o.id.startsWith('system_')) {
        chart.removeOverlay({ id: o.id });
      }
    });

    // Create static Initial Balance Levels (IBH, IBL)
    if (data?.ib?.high && candles.length) {
      chart.createOverlay({
        id: 'system_ibh',
        name: 'straightLine',
        points: [{ value: data.ib.high }],
        styles: { line: { color: 'rgba(255, 165, 0, 0.3)', size: 1, style: 'dashed', dashPattern: [4, 4] } },
        lock: true
      });
    }
    if (data?.ib?.low && candles.length) {
      chart.createOverlay({
        id: 'system_ibl',
        name: 'straightLine',
        points: [{ value: data.ib.low }],
        styles: { line: { color: 'rgba(255, 165, 0, 0.3)', size: 1, style: 'dashed', dashPattern: [4, 4] } },
        lock: true
      });
    }

    // Create Trade segments (closed trades)
    if (trades.length && candles.length) {
      trades.forEach(t => {
        const entryTimeMs = new Date(t.entry_time).getTime();
        let exitTimeMs = new Date(t.exit_time).getTime();
        if (exitTimeMs <= entryTimeMs) exitTimeMs = entryTimeMs + 60000;
        const directionLong = t.direction === 'long';
        chart.createOverlay({
          id: `system_trade_${t.entry_time}`,
          name: directionLong ? 'longPosition' : 'shortPosition',
          points: [
            { timestamp: entryTimeMs, value: t.entry },
            { timestamp: exitTimeMs, value: t.stop },
            { timestamp: exitTimeMs, value: t.target }
          ],
          styles: { quantity: 1 },
          lock: true
        });
      });
    }

    // Create Proposal markers
    if (proposals.length && candles.length) {
      const topProposals = [...proposals].sort((a, b) => b.confidence - a.confidence).slice(0, 50);
      topProposals.forEach(p => {
        if (!p.entry) return;
        const isLong = p.direction === 'long';
        const wasExecuted = p.decision === 'trade' || p.decision === null;
        chart.createOverlay({
          id: `system_proposal_${p.bar_time_utc || p.entry}`,
          name: 'straightLine',
          points: [{ value: p.entry }],
          styles: {
            line: {
              color: isLong ? `rgba(72,187,120,${wasExecuted ? 0.8 : 0.25})` : `rgba(252,129,129,${wasExecuted ? 0.8 : 0.25})`,
              size: wasExecuted ? 2 : 1,
              style: 'dashed',
              dashPattern: [3, 5]
            }
          },
          lock: true
        });
      });
    }

    // Create OPEN TRADE overlay
    if (openTrade && openTrade.entry_time && candles.length) {
      const tradeDate = openTrade.entry_time.split('T')[0];
      if (tradeDate === date) {
        const entryTimeMs = new Date(openTrade.entry_time).getTime();
        const lastCandleTime = formattedCandles[formattedCandles.length - 1].timestamp;
        const exitTimeMs = Math.max(entryTimeMs + 60000, lastCandleTime + 120000);
        chart.createOverlay({
          id: `system_opentrade_${openTrade.entry_time}`,
          name: openTrade.direction === 'long' ? 'longPosition' : 'shortPosition',
          points: [
            { timestamp: entryTimeMs, value: openTrade.entry },
            { timestamp: exitTimeMs, value: openTrade.stop },
            { timestamp: exitTimeMs, value: openTrade.target }
          ],
          styles: { quantity: 1 },
          lock: true
        });
      }
    }

    // Create LIVE ANALYSIS Marker
    if (latestReasoning && latestReasoning.bar_time_et && latestReasoning.date === date && candles.length) {
      const targetCandle = formattedCandles.find(c => {
        const etString = new Date(c.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', timeZone: 'America/New_York' });
        return etString === latestReasoning.bar_time_et;
      });
      const markerTime = targetCandle ? targetCandle.timestamp : formattedCandles[formattedCandles.length - 1].timestamp;
      chart.createOverlay({
        id: 'system_liveanalysis',
        name: 'liveAnalysisMarker',
        points: [{ timestamp: markerTime, value: 0 }],
        lock: true
      });
    }

    // Create Big Trades markers
    if (data?.big_trades?.length && candles.length) {
      const sorted = [...data.big_trades].sort((a, b) => b.size - a.size).slice(0, 20);
      const MIN_SIZE = sorted.length > 0 ? sorted[sorted.length - 1].size : 30;
      const btMap = {};
      data.big_trades.filter(bt => bt.size >= MIN_SIZE).forEach(bt => {
        const key = `${bt.time}_${bt.side}`;
        if (!btMap[key]) btMap[key] = { time: bt.time, side: bt.side, totalSize: 0 };
        btMap[key].totalSize += bt.size;
      });
      Object.values(btMap).forEach(bt => {
        const timestampMs = bt.time * 1000;
        const matchCandle = formattedCandles.find(c => Math.abs(c.timestamp - timestampMs) < 30000);
        let value = data.vp?.poc || 15000;
        if (matchCandle) value = bt.side === 'A' ? matchCandle.low : matchCandle.high;
        chart.createOverlay({
          id: `system_bigtrade_${bt.time}_${bt.side}`,
          name: 'bigTradeMarker',
          points: [{ timestamp: timestampMs, value }],
          styles: { side: bt.side, size: bt.totalSize },
          lock: true
        });
      });
    }

  }, [trades, proposals, openTrade, latestReasoning, data, date]);
"""

i = 0
while i < len(lines):
    line = lines[i]
    if "// Create static Initial Balance Levels (IBH, IBL)" in line:
        skip_mode = True
    
    if skip_mode and "// Load user drawings from LocalStorage" in line:
        skip_mode = False
    
    if not skip_mode:
        new_lines.append(line)
        if "const prevJumpRef = useRef(jumpTimestamp)" in line:
            # Insert the new useEffect just before the auto-scroll useEffect
            new_lines.insert(-1, system_overlays_code)
    i += 1

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
