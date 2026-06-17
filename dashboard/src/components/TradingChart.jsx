import { useEffect, useRef, useState } from 'react'
import { init, dispose, registerIndicator } from 'klinecharts'
import './klinechartsCustomOverlays'
import DrawingToolbar from './DrawingToolbar'
import DrawingSettingsModal from './DrawingSettingsModal'
import BigTradesTape from './BigTradesTape'

// Register Custom Indicators Globally Once
try {
  registerIndicator({
    name: 'VWAP',
    shortName: 'VWAP',
    series: 'price',
    figures: [
      {
        key: 'vwap',
        title: 'VWAP: ',
        type: 'line',
        styles: () => ({ color: '#ff9f43', size: 1.5, style: 'dashed', dashedValue: [4, 4] })
      }
    ],
    calc: (dataList) => dataList.map(d => ({ vwap: d.vwap }))
  })
} catch (e) {
  console.log('VWAP indicator registration or already registered:', e.message)
}

try {
  registerIndicator({
    name: 'DevPOC',
    shortName: 'Dev POC',
    series: 'price',
    figures: [
      {
        key: 'poc',
        title: 'Dev POC: ',
        type: 'line',
        styles: () => ({ color: '#f1c40f', size: 2, style: 'solid' })
      }
    ],
    calc: (dataList) => dataList.map(d => ({ poc: d.poc }))
  })
} catch (e) {
  console.log('DevPOC indicator registration or already registered:', e.message)
}

try {
  registerIndicator({
    name: 'DevVA',
    shortName: 'Dev VA',
    series: 'price',
    figures: [
      {
        key: 'vah',
        title: 'VAH: ',
        type: 'line',
        styles: () => ({ color: '#3498db', size: 1.5, style: 'dashed', dashedValue: [4, 4] })
      },
      {
        key: 'val',
        title: 'VAL: ',
        type: 'line',
        styles: () => ({ color: '#e74c3c', size: 1.5, style: 'dashed', dashedValue: [4, 4] })
      }
    ],
    calc: (dataList) => dataList.map(d => ({ vah: d.vah, val: d.val }))
  })
} catch (e) {
  console.log('DevVA indicator registration or already registered:', e.message)
}

function fmtET(iso) {
  try {
    return new Date(iso).toLocaleTimeString('it-IT',
      { hour: '2-digit', minute: '2-digit', timeZone: 'America/New_York' })
  } catch { return '--:--' }
}

function useChartData(date) {
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isImporting, setIsImporting] = useState(false)

  useEffect(() => {
    let isCancelled = false
    let retryTimeout = null

    const fetchData = () => {
      setIsLoading(true)
      fetch(`/data/${date}.json?t=${Date.now()}`)
        .then(res => {
          if (!res.ok) throw new Error('Not found')
          return res.json()
        })
        .then(d => {
          if (isCancelled) return
          setData(d)
          setIsLoading(false)
          setIsImporting(false)
        })
        .catch(e => {
          if (isCancelled) return
          console.error("Dati non ancora disponibili per", date, "- Riprovo tra poco...")
          setData(null)
          setIsImporting(true)
          retryTimeout = setTimeout(fetchData, 3000) // Riprova ogni 3 secondi
        })
    }

    fetchData()

    return () => {
      isCancelled = true
      if (retryTimeout) clearTimeout(retryTimeout)
    }
  }, [date])

  return { data, isLoading, isImporting }
}

const saveUserDrawings = (chart, currentDate) => {
  if (!chart) return
  try {
    const drawings = chart.getOverlays().filter(o =>
      ['segment', 'customRectangle', 'longPosition', 'shortPosition', 'anchoredVolumeProfile'].includes(o.name) &&
      (!o.id || !o.id.startsWith('system_'))
    )
    const serialized = drawings.map(o => ({
      id: o.id,
      name: o.name,
      points: o.points,
      styles: o.styles,
      lock: !!o.lock
    }))
    localStorage.setItem(`kline_drawings_${currentDate}`, JSON.stringify(serialized))
  } catch (e) {
    console.error('Error saving drawings:', e)
  }
}

export default function TradingChart({ trades = [], proposals = [], date, activeTrade, activeReasoning, onTradeClick, openTrade, latestReasoning, jumpTimestamp, runFilter, autoScroll, onAutoScrollChange, timeZone, onToggleTimeZone }) {
  const containerRef = useRef(null)
  const chartRef     = useRef(null)
  const prevActiveTradeRef = useRef(null)
  const candlesRef = useRef([])
  const updateBarCallbackRef = useRef(null)

  const [activeTool, setActiveTool] = useState(null)
  const [selectedDrawing, setSelectedDrawing] = useState(null)
  const [chartReady, setChartReady] = useState(false)
  const [layers, setLayers] = useState({ vwap: true, vp: true, bigTrades: true, trades: true })
  const { data, isLoading, isImporting } = useChartData(date)

  // Initialize and render chart
  useEffect(() => {
    const el = containerRef.current
    if (!el || isLoading) return

    let chartInstance = null
    let resizeObserver = null

    const timer = setTimeout(() => {
      if (!el.clientWidth || !el.clientHeight) return

      // Fresh mount (guaranteed by key prop in App.jsx) — just init
      const chart = init(el)
      chartRef.current = chart
      chartInstance = chart

      chart.setStyles({
        grid: { horizontal: { show: true, color: '#2A2C39', size: 1, style: 'dashed', dashValue: [2, 2] }, vertical: { show: false } },
        candle: {
          type: 'candle_solid',
          bar: {
            upColor: '#26A69A', downColor: '#EF5350',
            upBorderColor: '#26A69A', downBorderColor: '#EF5350',
            upWickColor: '#26A69A', downWickColor: '#EF5350'
          },
          tooltip: {
            showRule: 'always',
            showType: 'rect',
            custom: (data) => {
              if (!data || !data.current) return []
              const d = data.current
              return [
                { title: 'Volume', value: d.volume ? d.volume.toString() : '0' },
                { title: 'Delta', value: d.delta !== undefined ? (d.delta > 0 ? '+' : '') + d.delta.toString() : '0' }
              ]
            }
          }
        },
        crosshair: {
          show: true,
          horizontal: {
            line: { color: 'rgba(255, 255, 255, 0.25)', style: 'dash', dashValue: [4, 4] }
          },
          vertical: {
            line: { color: 'rgba(255, 255, 255, 0.25)', style: 'dash', dashValue: [4, 4] }
          }
        }
      })

      chart.setSymbol({ ticker: 'NQ', pricePrecision: 2, volumePrecision: 0 })
      chart.setTimezone(timeZone)
      chart.setPeriod({ type: 'minute', span: 1 })
      chart.setDataLoader({
        getBars: ({ timestamp, callback }) => {
          if (!timestamp) {
            callback(candlesRef.current, false)
          } else {
            callback([], false)
          }
        },
        subscribeBar: ({ callback }) => {
          updateBarCallbackRef.current = callback;
        },
        unsubscribeBar: () => {
          updateBarCallbackRef.current = null;
        }
      })

      // Add price indicators on main pane
      chart.createIndicator('VWAP', { pane: { id: 'candle_pane' }, isStack: true })
      
      // Explicitly remove DevPOC and DevVA indicators if they were previously created/restored
      try {
        chart.removeIndicator({ name: 'DevPOC' })
        chart.removeIndicator({ name: 'DevVA' })
      } catch (e) {
        console.error('Error removing indicators:', e)
      }

      // Clear any existing overlays just in case
      try { chart.removeOverlay() } catch(e) {}

      // Load user drawings from LocalStorage
      const savedData = localStorage.getItem(`kline_drawings_${date}`)
      if (savedData) {
        try {
          const parsed = JSON.parse(savedData)
          parsed.forEach(o => {
            chart.createOverlay({
              id: o.id,
              name: o.name,
              points: o.points,
              styles: o.styles,
              lock: !!o.lock,
              onSelected: (e) => { setSelectedDrawing(e.overlay) },
              onDeselected: () => { setSelectedDrawing(null) }
            })
          })
        } catch (e) {
          console.error('Error importing drawings:', e)
        }
      }

      // Resize observer
      resizeObserver = new ResizeObserver(() => {
        if (chartInstance && el.clientWidth && el.clientHeight) {
          chartInstance.resize()
        }
      })
      resizeObserver.observe(el)
      
      setChartReady(true)
    }, 80)

    const handleUserInteraction = () => {
      onAutoScrollChange(false)
    }
    el.addEventListener('mousedown', handleUserInteraction)
    el.addEventListener('wheel', handleUserInteraction, { passive: true })
    el.addEventListener('touchstart', handleUserInteraction, { passive: true })

    return () => {
      clearTimeout(timer)
      if (resizeObserver) resizeObserver.disconnect()
      el.removeEventListener('mousedown', handleUserInteraction)
      el.removeEventListener('wheel', handleUserInteraction)
      el.removeEventListener('touchstart', handleUserInteraction)
      if (chartInstance) {
        dispose(el)
        chartRef.current = null
      }
    }
  }, [date, isLoading])


  // -----------------------------------------------------
  // System Overlays & Dynamic Candle Data useEffect
  // -----------------------------------------------------
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !chartReady || !data || !data.m1_ny) return;

    // 1. Determine maximum visible timestamp to prevent lookahead
    let maxTimeMs = Infinity;
    if (activeTrade) {
      const exitTime = activeTrade.exit_time || activeTrade.bar_time_utc || activeTrade.entry_time;
      if (exitTime) {
        maxTimeMs = new Date(exitTime).getTime() + 5 * 60000; // 5 min padding
      }
    } else if (activeReasoning) {
      const rTime = activeReasoning.bar_time_utc || activeReasoning.entry_time;
      if (rTime) {
        maxTimeMs = new Date(rTime).getTime();
      }
    } else if (latestReasoning && latestReasoning.date === date) {
      const rTime = latestReasoning.bar_time_utc;
      if (rTime) {
        maxTimeMs = new Date(rTime).getTime();
      }
    }

    const candles = data.m1_ny.filter(c => c.time * 1000 <= maxTimeMs);

    // 2. Map developing indicators dynamically bar-by-bar
    const vwapMap = {};
    if (data.vwap) {
      data.vwap.forEach(v => {
        vwapMap[v.time] = v.value;
      });
    }
    
    const devVaMap = {};
    if (data.dev_va) {
      data.dev_va.forEach(d => {
        devVaMap[d.time] = { poc: d.poc, vah: d.vah, val: d.val };
      });
    }

    const formattedCandles = candles.map(c => ({
      timestamp: c.time * 1000,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
      volume: c.volume || 0,
      vwap: vwapMap[c.time] || null,
      poc: devVaMap[c.time]?.poc || null,
      vah: devVaMap[c.time]?.vah || null,
      val: devVaMap[c.time]?.val || null
    }));

    // ONLY update data if candles actually changed (prevents scrolling to start on layer toggle)
    const oldLength = candlesRef.current.length;
    const newLength = formattedCandles.length;
    
    const oldLast = oldLength > 0 ? candlesRef.current[oldLength - 1] : null;
    const newLast = newLength > 0 ? formattedCandles[newLength - 1] : null;
    const isDataDifferent = oldLength !== newLength || 
                           (oldLast && newLast && oldLast.timestamp !== newLast.timestamp) || 
                           (oldLast && newLast && JSON.stringify(oldLast) !== JSON.stringify(newLast)) ||
                           !oldLast;

    if (isDataDifferent) {
      if (oldLength === 0 && newLength > 0) {
        candlesRef.current = formattedCandles;
        chart.resetData();
      } else if (newLength > 0) {
        if (newLength >= oldLength && oldLength > 0 && oldLast && formattedCandles[oldLength - 1].timestamp === oldLast.timestamp) {
          candlesRef.current = formattedCandles;
          // Append new candles without resetting zoom
          if (updateBarCallbackRef.current) {
            for (let i = oldLength - 1; i < newLength; i++) {
              if (i >= 0) updateBarCallbackRef.current(formattedCandles[i]);
            }
          }
        } else if (newLength === oldLength && oldLast && newLast && oldLast.timestamp === newLast.timestamp) {
          candlesRef.current = formattedCandles;
          // Update the last candle
          if (updateBarCallbackRef.current) updateBarCallbackRef.current(newLast);
        } else {
          // Fallback: completely replace data if things are disjoint
          candlesRef.current = formattedCandles;
          chart.resetData();
        }
      } else if (newLength === 0 && oldLength > 0) {
        candlesRef.current = [];
        chart.resetData();
      }
    } else {
      candlesRef.current = formattedCandles;
    }

    // 3. Remove old system overlays
    const overlays = chart.getOverlays();
    overlays.forEach(o => {
      if (o.id && o.id.startsWith('system_')) {
        chart.removeOverlay({ id: o.id });
      }
    });

    // 4. Create static Initial Balance Levels (IBH, IBL)
    if (layers.vp && data?.ib?.high && candles.length) {
      chart.createOverlay({
        id: 'system_ibh',
        name: 'labeledHLine',
        points: [{ timestamp: candles[0].time * 1000, value: data.ib.high }],
        styles: { lineColor: 'rgba(255, 165, 0, 0.7)', label: 'IB High', lineStyle: 'dashed', lineWidth: 1.5 },
        lock: true
      });
    }
    if (layers.vp && data?.ib?.low && candles.length) {
      chart.createOverlay({
        id: 'system_ibl',
        name: 'labeledHLine',
        points: [{ timestamp: candles[0].time * 1000, value: data.ib.low }],
        styles: { lineColor: 'rgba(255, 165, 0, 0.7)', label: 'IB Low', lineStyle: 'dashed', lineWidth: 1.5 },
        lock: true
      });
    }

    // 4b. Create static Yesterday's Value Area levels (VAH, VAL, POC)
    if (layers.vp && data?.prev_day_vp && candles.length) {
      const pvp = data.prev_day_vp;
      if (pvp.va_high) {
        chart.createOverlay({
          id: 'system_prev_vah',
          name: 'labeledHLine',
          points: [{ timestamp: candles[0].time * 1000, value: pvp.va_high }],
          styles: { lineColor: 'rgba(99, 179, 237, 0.65)', label: 'Prev VAH', lineStyle: 'dashed', lineWidth: 1 },
          lock: true
        });
      }
      if (pvp.va_low) {
        chart.createOverlay({
          id: 'system_prev_val',
          name: 'labeledHLine',
          points: [{ timestamp: candles[0].time * 1000, value: pvp.va_low }],
          styles: { lineColor: 'rgba(252, 129, 129, 0.65)', label: 'Prev VAL', lineStyle: 'dashed', lineWidth: 1 },
          lock: true
        });
      }
      if (pvp.poc) {
        chart.createOverlay({
          id: 'system_prev_poc',
          name: 'labeledHLine',
          points: [{ timestamp: candles[0].time * 1000, value: pvp.poc }],
          styles: { lineColor: 'rgba(241, 196, 15, 0.6)', label: 'Prev POC', lineStyle: 'solid', lineWidth: 1.5 },
          lock: true
        });
      }
    }

    // 4c. Create static Today's Overnight Value Area levels (VAH, VAL, POC)
    if (data?.vp && candles.length) {
      const ovp = data.vp;
      if (ovp.va_high) {
        chart.createOverlay({
          id: 'system_overnight_vah',
          name: 'labeledHLine',
          points: [{ timestamp: candles[0].time * 1000, value: ovp.va_high }],
          styles: { lineColor: 'rgba(52, 152, 219, 0.85)', label: 'ON VAH', lineStyle: 'dashed', lineWidth: 1.5 },
          lock: true
        });
      }
      if (ovp.va_low) {
        chart.createOverlay({
          id: 'system_overnight_val',
          name: 'labeledHLine',
          points: [{ timestamp: candles[0].time * 1000, value: ovp.va_low }],
          styles: { lineColor: 'rgba(231, 76, 60, 0.85)', label: 'ON VAL', lineStyle: 'dashed', lineWidth: 1.5 },
          lock: true
        });
      }
      if (ovp.poc) {
        chart.createOverlay({
          id: 'system_overnight_poc',
          name: 'labeledHLine',
          points: [{ timestamp: candles[0].time * 1000, value: ovp.poc }],
          styles: { lineColor: 'rgba(243, 156, 18, 0.9)', label: 'ON POC', lineStyle: 'solid', lineWidth: 2 },
          lock: true
        });
      }
    }

    // 5. Create Trade segments (closed trades)
    if (layers.trades && trades.length && candles.length) {
      // Group trades by entry_time to avoid drawing multiple overlapping boxes for partial exits
      const groupedTrades = {};
      trades.forEach(t => {
        if (!groupedTrades[t.entry_time]) groupedTrades[t.entry_time] = [];
        groupedTrades[t.entry_time].push(t);
      });

      Object.values(groupedTrades).forEach(group => {
        const t0 = group[0];
        // The final exit is the one with the latest exit_time
        const finalExit = group.reduce((latest, t) => new Date(t.exit_time).getTime() > new Date(latest.exit_time).getTime() ? t : latest, group[0]);

        const entryTimeMs = new Date(t0.entry_time).getTime();
        let exitTimeMs = new Date(finalExit.exit_time).getTime();
        if (exitTimeMs <= entryTimeMs) exitTimeMs = entryTimeMs + 60000;
        const directionLong = t0.direction && t0.direction.toLowerCase() === 'long';

        let snappedEntryTime = entryTimeMs;
        let snappedExitTime = exitTimeMs;
        if (formattedCandles.length) {
          const entryDiffs = formattedCandles.map(c => ({ c, diff: Math.abs(c.timestamp - entryTimeMs) }));
          entryDiffs.sort((a, b) => a.diff - b.diff);
          snappedEntryTime = entryDiffs[0].c.timestamp;

          const exitDiffs = formattedCandles.map(c => ({ c, diff: Math.abs(c.timestamp - exitTimeMs) }));
          exitDiffs.sort((a, b) => a.diff - b.diff);
          snappedExitTime = exitDiffs[0].c.timestamp;

          if (snappedExitTime <= snappedEntryTime && exitTimeMs > entryTimeMs) {
            const entryIdx = formattedCandles.indexOf(entryDiffs[0].c);
            if (entryIdx < formattedCandles.length - 1) {
              snappedExitTime = formattedCandles[entryIdx + 1].timestamp;
            } else {
              snappedExitTime = snappedEntryTime + 60000;
            }
          }
        }
        
        // Cap to prevent looking into the future during replay
        if (snappedExitTime > maxTimeMs && formattedCandles.length > 0) {
           snappedExitTime = formattedCandles[formattedCandles.length - 1].timestamp;
        }

        if (entryTimeMs <= maxTimeMs) {
          const overlayId = `system_trade_${t0.entry_time}`;
          chart.createOverlay({
            id: overlayId,
            name: directionLong ? 'longPosition' : 'shortPosition',
            points: [
              { timestamp: snappedEntryTime, value: Number(t0.entry) },
              { timestamp: snappedExitTime, value: Number(t0.stop) },
              { timestamp: snappedExitTime, value: Number(finalExit.target) || Number(t0.target) }
            ],
            styles: { quantity: 1 },
            lock: true
          });
        }
      });
    }


    // 6. Create OPEN TRADE overlay
    if (layers.trades && openTrade && openTrade.date === date && candles.length) {
      const tradeDate = openTrade.entry_time.split('T')[0];
      if (tradeDate === date) {
        const entryTimeMs = new Date(openTrade.entry_time).getTime();
        if (entryTimeMs <= maxTimeMs) {
          const lastCandleTime = formattedCandles[formattedCandles.length - 1].timestamp;
          const exitTimeMs = Math.max(entryTimeMs + 60000, lastCandleTime + 120000);

          let snappedEntryTime = entryTimeMs;
          let snappedExitTime = exitTimeMs;
          if (formattedCandles.length) {
            const entryDiffs = formattedCandles.map(c => ({ c, diff: Math.abs(c.timestamp - entryTimeMs) }));
            entryDiffs.sort((a, b) => a.diff - b.diff);
            snappedEntryTime = entryDiffs[0].c.timestamp;

            const exitDiffs = formattedCandles.map(c => ({ c, diff: Math.abs(c.timestamp - exitTimeMs) }));
            exitDiffs.sort((a, b) => a.diff - b.diff);
            snappedExitTime = exitDiffs[0].c.timestamp;
          }

          chart.createOverlay({
            id: `system_opentrade_${openTrade.entry_time}`,
            name: (openTrade.direction && openTrade.direction.toLowerCase() === 'long') ? 'longPosition' : 'shortPosition',
            points: [
              { timestamp: snappedEntryTime, value: Number(openTrade.entry) },
              { timestamp: snappedExitTime, value: Number(openTrade.stop) },
              { timestamp: snappedExitTime, value: Number(openTrade.target) }
            ],
            styles: { quantity: 1 },
            lock: true
          });
        }
      }
    }

    // 7. Create LIVE ANALYSIS Marker
    const targetReasoning = activeReasoning || latestReasoning;
    if (targetReasoning && targetReasoning.date === date && candles.length) {
      let analysisTimeMs = null;
      if (targetReasoning.bar_time_utc) {
        analysisTimeMs = new Date(targetReasoning.date + 'T' + targetReasoning.bar_time_utc + ':00Z').getTime();
      } else if (targetReasoning.bar_time_et) {
        // Fallback for older mock data structures if needed, although utc is usually present
        const dtStr = `${targetReasoning.date}T${targetReasoning.bar_time_et}:00`;
        // Not perfect timezone mapping, but usually close enough for fallback
        analysisTimeMs = new Date(dtStr).getTime();
      }

      let targetCandle = null;
      if (analysisTimeMs && formattedCandles.length) {
        const diffs = formattedCandles.map(c => ({ c, diff: Math.abs(c.timestamp - analysisTimeMs) }));
        diffs.sort((a, b) => a.diff - b.diff);
        if (diffs[0].diff < 360000) {
          targetCandle = diffs[0].c;
        }
      }

      if (targetCandle && targetCandle.timestamp <= maxTimeMs) {
        chart.createOverlay({
          id: 'system_liveanalysis',
          name: 'liveAnalysisMarker',
          points: [{ timestamp: targetCandle.timestamp, value: targetCandle.high }],
          lock: true
        });
      }
    }

    // 8. Create Big Trades markers
    if (layers.bigTrades && data?.big_trades?.length && candles.length) {
      const sorted = [...data.big_trades].sort((a, b) => b.size - a.size).slice(0, 20);
      const MIN_SIZE = sorted.length > 0 ? sorted[sorted.length - 1].size : 30;
      const btMap = {};
      data.big_trades.filter(bt => bt.size >= MIN_SIZE && (bt.time * 1000) <= maxTimeMs).forEach(bt => {
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

    // 9. Auto-scroll logic
    if (autoScroll && formattedCandles.length > 0) {
      try {
         // klinecharts v10 uses scrollToRealTime or manual offset
         if (chart.scrollToRealTime) {
             chart.scrollToRealTime();
         } else {
             const lastCandle = formattedCandles[formattedCandles.length - 1];
             chart.scrollToTimestamp(lastCandle.timestamp);
         }
      } catch (e) {
         console.warn("Scroll failed", e);
      }
    } else if (!autoScroll && (activeReasoning || activeTrade) && formattedCandles.length > 0) {
      // If user clicked a reasoning/trade, jump to it
      try {
         const targetMs = activeReasoning ? new Date(activeReasoning.bar_time_utc).getTime() : new Date(activeTrade.entry_time).getTime();
         if (chart.scrollToTimestamp) chart.scrollToTimestamp(targetMs);
      } catch(e){}
    }
  }, [trades, openTrade, latestReasoning, activeTrade, activeReasoning, data, date, chartReady, autoScroll, layers]);

  const prevJumpRef = useRef(jumpTimestamp)

  const prevScrollTargetRef = useRef(null)

  // Scroll logic for activeTrade, jumpTimestamp and latestReasoning
  useEffect(() => {
    if (!chartRef.current || !data?.m1_ny) return;
    
    let targetTimeMs = null;
    let isForcedJump = false;

    if (jumpTimestamp !== prevJumpRef.current) {
      isForcedJump = true;
      prevJumpRef.current = jumpTimestamp;
    }
    
    const isNewTradeSelected = activeTrade !== prevActiveTradeRef.current;
    if (isNewTradeSelected) {
      prevActiveTradeRef.current = activeTrade;
    }

    if (activeTrade && isNewTradeSelected) {
      const et = activeTrade.entry_time;
      targetTimeMs = et.includes('T') ? new Date(et).getTime() : new Date(`${activeTrade.date || date}T${activeTrade.bar_time_utc}:00Z`).getTime();
    } else if (isForcedJump && activeReasoning) {
      if (activeReasoning.bar_time_utc) {
        targetTimeMs = new Date(activeReasoning.bar_time_utc).getTime();
      }
    } else if (autoScroll && latestReasoning) {
      if (latestReasoning.bar_time_utc) {
        targetTimeMs = new Date(latestReasoning.bar_time_utc).getTime();
      } else if (latestReasoning.bar_time_et) {
        const targetCandle = data.m1_ny.find(c => {
          const d = new Date(c.time * 1000);
          const hh = d.toLocaleString('en-US', { hour: 'numeric', hour12: false, timeZone: 'America/New_York' }).padStart(2, '0');
          const mm = d.toLocaleString('en-US', { minute: '2-digit', timeZone: 'America/New_York' }).padStart(2, '0');
          return `${hh}:${mm}` === latestReasoning.bar_time_et || `${parseInt(hh, 10)}:${mm}` === latestReasoning.bar_time_et;
        });
        if (targetCandle) targetTimeMs = targetCandle.time * 1000;
        else targetTimeMs = data.m1_ny[data.m1_ny.length - 1].time * 1000;
      }
    }

    if (targetTimeMs && (isForcedJump || targetTimeMs !== prevScrollTargetRef.current)) {
      try {
        const index = data.m1_ny.findIndex(c => c.time * 1000 >= targetTimeMs);
        if (index !== -1) {
          if (typeof chartRef.current.scrollToDataIndex === 'function') {
            chartRef.current.scrollToDataIndex(index);
          } else if (typeof chartRef.current.scrollToRealTime === 'function') {
            chartRef.current.scrollToRealTime();
          } else if (typeof chartRef.current.setOffsetRightDistance === 'function') {
            const distance = data.m1_ny.length - 1 - index;
            chartRef.current.setOffsetRightDistance(distance * 6);
          }
        }
        prevScrollTargetRef.current = targetTimeMs;
      } catch (e) {
        console.error('Scroll failed:', e);
      }
    }
  }, [activeTrade, jumpTimestamp, data?.m1_ny?.length, latestReasoning?.bar_time_utc, autoScroll])

  // Create drawings toolbar actions
  const handleSetActiveTool = (tool) => {
    setActiveTool(tool)
    if (!chartRef.current || !tool) return

    chartRef.current.createOverlay({
      name: tool,
      onSelected: (e) => {
        setSelectedDrawing(e.overlay)
      },
      onDeselected: () => {
        setSelectedDrawing(null)
      },
      onDrawEnd: () => {
        saveUserDrawings(chartRef.current, date)
        setActiveTool(null)
      }
    })
  }

  const handleDeleteSelected = () => {
    if (chartRef.current && selectedDrawing) {
      chartRef.current.removeOverlay({ id: selectedDrawing.id })
      setSelectedDrawing(null)
      saveUserDrawings(chartRef.current, date)
    }
  }

  const handleClearAll = () => {
    if (window.confirm('Sei sicuro di voler cancellare tutti i tuoi disegni geometrici su questa giornata?')) {
      if (chartRef.current) {
        // Remove only user drawings
        const drawings = chartRef.current.getOverlays().filter(o =>
          ['segment', 'customRectangle', 'longPosition', 'shortPosition', 'anchoredVolumeProfile'].includes(o.name) &&
          (!o.id || !o.id.startsWith('system_'))
        )
        drawings.forEach(d => {
          chartRef.current.removeOverlay({ id: d.id })
        })
      }
      setSelectedDrawing(null)
      localStorage.removeItem(`kline_drawings_${date}`)
    }
  }

  const handleUpdateDrawing = (updatedProps) => {
    if (chartRef.current && selectedDrawing) {
      chartRef.current.createOverlay({
        id: selectedDrawing.id,
        ...updatedProps
      })
      // Sync local React state
      setSelectedDrawing(prev => ({
        ...prev,
        ...updatedProps
      }))
      saveUserDrawings(chartRef.current, date)
    }
  }

  // Keyboard shortcut listener for Backspace/Delete keys
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (document.activeElement.tagName !== 'INPUT') {
          handleDeleteSelected()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedDrawing])

  // MouseUp listener to capture dragging completions of drawings
  const handleMouseUp = () => {
    setTimeout(() => {
      saveUserDrawings(chartRef.current, date)
    }, 100)
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', flex:1, minHeight:0, overflow:'hidden' }} onMouseUp={handleMouseUp}>
      {/* Header */}
      <div className="chart-header">
        <div>
          <div className="chart-title">
            📈 {date} — NQ Futures
            {data ? ` · ${data.m1_ny?.length || 0} barre M1 · ${data.big_trades?.length || 0} Big Trades` : ''}
          </div>
          <div className="chart-subtitle">
            {isLoading
              ? 'Caricamento dati reali...'
              : data
                ? `POC ${data.vp?.poc ?? '?'} · VAH ${data.vp?.va_high ?? '?'} · VAL ${data.vp?.va_low ?? '?'}`
                : '⚠️ Dati non ancora esportati — esegui scratch/export_dashboard_data.py'}
          </div>
        </div>
        <div className="chart-tools">
          <button 
            className="chart-tool-btn"
            onClick={onToggleTimeZone}
            style={{ 
              border: '1px solid rgba(255,255,255,0.1)', 
              color: 'var(--accent-blue)',
              marginRight: '12px',
              fontWeight: '600'
            }}
            title="Cambia fuso orario del grafico tra Exchange (NY) e Locale (IT)"
          >
            🕒 {timeZone === 'America/New_York' ? 'Exchange (NY)' : 'Locale (IT)'}
          </button>
          <button 
            className="chart-tool-btn"
            onClick={() => onAutoScrollChange(!autoScroll)}
            style={{ 
              border: autoScroll ? '1px solid rgba(72,187,120,0.5)' : '1px solid rgba(255,255,255,0.1)', 
              color: autoScroll ? 'var(--accent-green)' : 'var(--text-muted)',
              marginRight: '12px'
            }}
            title="Centra automaticamente il grafico sull'ultima candela analizzata da Fabio"
          >
            {autoScroll ? 'Lock: ON' : 'Lock: OFF'}
          </button>
          <button className="chart-tool-btn active">M1</button>
          <button 
            className={`chart-tool-btn ${layers.trades ? 'active' : ''}`}
            onClick={() => setLayers(l => ({ ...l, trades: !l.trades }))}
          >Trades</button>
          <button 
            className={`chart-tool-btn ${layers.vwap ? 'active' : ''}`}
            onClick={() => {
              const next = !layers.vwap;
              setLayers(l => ({ ...l, vwap: next }));
              if (chartRef.current) {
                if (next) chartRef.current.createIndicator('VWAP', { pane: { id: 'candle_pane' }, isStack: true })
                else {
                  try { chartRef.current.removeIndicator('candle_pane', 'VWAP') } catch(e) {}
                }
              }
            }}
          >VWAP</button>
          <button 
            className={`chart-tool-btn ${layers.vp ? 'active' : ''}`}
            onClick={() => setLayers(l => ({ ...l, vp: !l.vp }))}
          >VP</button>
          <button 
            className={`chart-tool-btn ${layers.bigTrades ? 'active' : ''}`}
            onClick={() => setLayers(l => ({ ...l, bigTrades: !l.bigTrades }))}
          >Big Trades</button>
        </div>
      </div>

      {/* Legenda */}
      {data && (
        <div style={{ padding:'4px 14px', display:'flex', gap:14, fontSize:10, color:'rgba(255,255,255,0.4)', borderBottom:'1px solid rgba(255,255,255,0.06)', flexShrink:0 }}>
          <span style={{ color:'#f6ad55' }}>▬ VWAP</span>
          <span style={{ color:'#f6e05e' }}>▬ POC</span>
          <span style={{ color:'rgba(99,179,237,0.7)' }}>╌ VAH</span>
          <span style={{ color:'rgba(252,129,129,0.7)' }}>╌ VAL</span>
          <span style={{ color:'#48bb78' }}>▲ Buy Istituzionale</span>
          <span style={{ color:'#fc8181' }}>▼ Sell Istituzionale</span>
          <span>★ = Trade aperto</span>
        </div>
      )}

      {/* Layout principale del grafico con toolbar a sinistra */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, position: 'relative' }}>
        <DrawingToolbar
          activeTool={activeTool}
          setActiveTool={handleSetActiveTool}
          onDeleteSelected={handleDeleteSelected}
          onClearAll={handleClearAll}
          hasSelected={!!selectedDrawing}
        />
        
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
          <div ref={containerRef} style={{ flex: 1, background: '#0d1117', overflow: 'hidden' }} />
          
          <BigTradesTape 
            bigTrades={data?.big_trades || []} 
            currentTimeMs={jumpTimestamp || (data?.m1_ny?.[data.m1_ny.length-1]?.time * 1000) || Date.now()} 
            timeZone={timeZone} 
          />

          {/* Loading / Importing Overlay */}
          {isImporting && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 50,
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(13, 17, 23, 0.85)', backdropFilter: 'blur(8px)', color: 'var(--text-primary)'
            }}>
              <div style={{ fontSize: 40, marginBottom: 16, animation: 'spin 2s linear infinite' }}>⏳</div>
              <div style={{ fontSize: 16, fontWeight: 'bold', color: 'var(--accent-blue)' }}>Estrazione dati per {date}...</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>Generazione delle candele e profili di volume in corso.</div>
            </div>
          )}
          
          {/* Floating Open Trade Widget */}
          {openTrade && openTrade.entry_time && openTrade.entry_time.split('T')[0] === date && (
            <div style={{
              position: 'absolute', top: 16, right: 16, zIndex: 10,
              background: 'rgba(30, 41, 59, 0.85)', backdropFilter: 'blur(8px)',
              border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: 12,
              color: 'var(--text-primary)', fontSize: 12, width: 220,
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: 4 }}>
                <span style={{ fontWeight: 'bold', color: 'var(--accent-blue)' }}>TRADE IN CORSO</span>
                <span className={`tag tag-${(openTrade.direction && openTrade.direction.toLowerCase() === 'long') ? 'long' : 'short'}`}>{openTrade.direction.toUpperCase()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)' }}>Entry</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{openTrade.entry}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)' }}>Target</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-green)' }}>{openTrade.target}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Stop</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-red)' }}>{openTrade.stop}</span>
              </div>
            </div>
          )}

          {selectedDrawing && (
            <DrawingSettingsModal
              selectedDrawing={selectedDrawing}
              onUpdateDrawing={handleUpdateDrawing}
              onClose={() => setSelectedDrawing(null)}
            />
          )}
        </div>
      </div>
    </div>
  )
}
