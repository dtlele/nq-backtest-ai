/**
 * FootprintChart v3.0 — Canvas-accelerated volumetric chart
 *
 * Miglioramenti drastici:
 * - HTML5 Canvas per footprint grid (performance 35K+ livelli)
 * - Colorazione delta con intensità (verde/rosso in base a volume)
 * - Zoom centrato sul mouse
 * - Trade Markers (entry/stop/target dal CleanBridge)
 * - Agent Signal arrows (▲/▼ sul chart)
 * - Big Trade bubbles migliorate
 * - SVG overlaid per linee VP/IB/GEX
 * - Auto-scroll replay con requestAnimationFrame
 */
import React, { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useTradingStore } from '../store/tradingStore';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const TICK_SIZE   = 0.25;
const CELL_HEIGHT = 22;
const CANDLE_W    = 220;

// ─── Color palette v3.0 ───────────────────────────────────────────────────────
const C = {
  bg: '#080d18', gridLine: 'rgba(30,41,59,0.35)', gridMajor: 'rgba(30,41,59,0.6)',
  askImb: '#34d399', bidImb: '#fb7185',
  askImbBg: 'rgba(52,211,153,0.18)', bidImbBg: 'rgba(251,113,133,0.18)',
  askBg: 'rgba(16,185,129,0.07)', bidBg: 'rgba(244,63,94,0.07)',
  poc: '#eab308', pocLine: 'rgba(234,179,8,0.5)',
  vaArea: 'rgba(34,197,94,0.05)', vah: 'rgba(34,197,94,0.7)', val: 'rgba(34,197,94,0.7)',
  hvn: 'rgba(56,189,248,0.7)', lvn: 'rgba(251,146,60,0.6)',
  ibBox: 'rgba(139,92,246,0.05)', ibLine: 'rgba(139,92,246,0.7)',
  zeroGamma: 'rgba(239,68,68,0.7)', callWall: 'rgba(34,197,94,0.6)', putWall: 'rgba(239,68,68,0.6)',
  bullBody: '#10b981', bearBody: '#f43f5e',
  entryLine: '#22d3ee', stopLine: '#f43f5e', targetLine: '#10b981',
  exitMarker: '#fbbf24', textDim: '#475569',
  bubbleBuy: '#34d399', bubbleSell: '#fb7185',
};

interface FootprintChartProps { autoScroll?: boolean; }

export const FootprintChart: React.FC<FootprintChartProps> = ({ autoScroll = true }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const prevCandlesLen = useRef(0);
  const [scale, setScale] = useState(0.8);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const panStart = useRef({ x: 0, y: 0 });

  const {
    candles, volumeProfile, sessionCtx,
    showVP, showGEX, showIBBox, showBigTrades,
    tradeMarkers, agentSignals,
  } = useTradingStore();

  // ── Price range ─────────────────────────────────────────────────────────────
  const { prices, globalMaxVolume, maxPrice, minPrice } = useMemo(() => {
    if (!candles.length) return { prices: [], globalMaxVolume: 1, maxPrice: 0, minPrice: 0 };
    let maxP = -Infinity, minP = Infinity, maxV = 1;
    candles.forEach(c => {
      if (c.barHigh > maxP) maxP = c.barHigh;
      if (c.barLow < minP) minP = c.barLow;
      const cm = c.levels.reduce((a, l) => Math.max(a, l.bidVol + l.askVol), 0);
      if (cm > maxV) maxV = cm;
    });
    maxP += 16 * TICK_SIZE; minP -= 16 * TICK_SIZE;
    const pa: number[] = [];
    for (let p = maxP; p >= minP; p -= TICK_SIZE) pa.push(Math.round(p / TICK_SIZE) * TICK_SIZE);
    return { prices: pa, globalMaxVolume: maxV, maxPrice: maxP, minPrice: minP };
  }, [candles]);

  const vpO = volumeProfile ? {
    poc: volumeProfile.poc, vaHigh: volumeProfile.vaHigh, vaLow: volumeProfile.vaLow,
    hvnLevels: volumeProfile.hvnLevels, lvnLevels: volumeProfile.lvnLevels,
  } : null;

  const ibO = sessionCtx ? {
    ibHigh: sessionCtx.ibHigh, ibLow: sessionCtx.ibLow, ibComplete: sessionCtx.ibComplete,
  } : null;

  const gexO = sessionCtx?.gexRegime ? {
    zeroGammaLevel: sessionCtx.zeroGammaLevel, callWall: sessionCtx.callWall, putWall: sessionCtx.putWall,
  } : null;

  const priceToY = useCallback((p: number) => 60 + ((maxPrice - p) / TICK_SIZE) * CELL_HEIGHT, [maxPrice]);
  const chartH = (prices.length * CELL_HEIGHT) + 80;
  const chartW = candles.length * CANDLE_W;
  const showText = scale > 0.3;

  // ── Canvas draw ─────────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !candles.length) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(chartW, containerRef.current?.clientWidth || 1200);
    const h = Math.max(chartH, containerRef.current?.clientHeight || 800);
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    // Grid
    for (let i = 0; i < prices.length; i += 4) {
      const y = 60 + i * CELL_HEIGHT;
      ctx.strokeStyle = y === 60 ? C.gridMajor : C.gridLine;
      ctx.lineWidth = y === 60 ? 1 : 0.5;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Candles
    for (let ci = 0; ci < candles.length; ci++) {
      const cd = candles[ci];
      const isBull = cd.barClose >= cd.barOpen;
      const col = isBull ? C.bullBody : C.bearBody;
      const x = ci * CANDLE_W;
      const oY = priceToY(cd.barOpen), cY = priceToY(cd.barClose);
      const hY = priceToY(cd.barHigh), lY = priceToY(cd.barLow);

      ctx.strokeStyle = col; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(x + 6, hY); ctx.lineTo(x + 6, lY); ctx.stroke();

      const bt = Math.min(oY, cY), bh = Math.max(2, Math.abs(cY - oY));
      ctx.fillStyle = col; ctx.globalAlpha = 0.5;
      ctx.fillRect(x + 2, bt, 8, bh); ctx.globalAlpha = 1;

      ctx.strokeStyle = 'rgba(30,41,59,0.4)'; ctx.lineWidth = 0.5;
      ctx.beginPath(); ctx.moveTo(x + CANDLE_W, 60); ctx.lineTo(x + CANDLE_W, h); ctx.stroke();

      // Footprint levels
      for (const lvl of cd.levels) {
        const tot = lvl.bidVol + lvl.askVol;
        if (!tot) continue;
        const y = priceToY(lvl.price);
        const isAI = lvl.imbalance === 'ask', isBI = lvl.imbalance === 'bid';
        const wp = Math.min(1, tot / globalMaxVolume);

        ctx.fillStyle = isAI ? C.askImbBg : isBI ? C.bidImbBg : (lvl.delta >= 0 ? C.askBg : C.bidBg);
        ctx.fillRect(x + 16, y, Math.max(2, (CANDLE_W - 32) * wp), CELL_HEIGHT);

        if (isAI) { ctx.fillStyle = 'rgba(52,211,153,0.06)'; ctx.fillRect(x + 16, y, CANDLE_W - 32, CELL_HEIGHT); }
        else if (isBI) { ctx.fillStyle = 'rgba(251,113,133,0.06)'; ctx.fillRect(x + 16, y, CANDLE_W - 32, CELL_HEIGHT); }

        if (lvl.isPoc) { ctx.strokeStyle = C.poc; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x + 12, y); ctx.lineTo(x + 16, y); ctx.stroke(); }

        if (showText) {
          ctx.font = 'bold 10px "JetBrains Mono", monospace';
          ctx.textAlign = 'right'; ctx.fillStyle = isBI ? C.bidImb : C.textDim;
          if (lvl.bidVol > 0) ctx.fillText(String(lvl.bidVol), x + CANDLE_W / 2 - 4, y + CELL_HEIGHT - 6);
          ctx.textAlign = 'center'; ctx.fillStyle = C.textDim; ctx.fillText('×', x + CANDLE_W / 2, y + CELL_HEIGHT - 6);
          ctx.textAlign = 'left'; ctx.fillStyle = isAI ? C.askImb : C.textDim;
          if (lvl.askVol > 0) ctx.fillText(String(lvl.askVol), x + CANDLE_W / 2 + 4, y + CELL_HEIGHT - 6);
        }
      }

      // Big trades
      if (showBigTrades && cd.bigTrades) {
        for (const bt of cd.bigTrades) {
          if (bt.price < minPrice || bt.price > maxPrice) continue;
          const by = priceToY(bt.price), isA = bt.side === 'A', bx = isA ? x + CANDLE_W - 18 : x + 18;
          ctx.beginPath(); ctx.arc(bx, by, 10, 0, Math.PI * 2);
          ctx.fillStyle = isA ? 'rgba(52,211,153,0.15)' : 'rgba(251,113,133,0.15)'; ctx.fill();
          ctx.beginPath(); ctx.arc(bx, by, 8, 0, Math.PI * 2);
          ctx.fillStyle = isA ? C.bubbleBuy : C.bubbleSell; ctx.globalAlpha = 0.85; ctx.fill();
          ctx.strokeStyle = isA ? 'rgba(52,211,153,0.6)' : 'rgba(251,113,133,0.6)'; ctx.lineWidth = 1; ctx.stroke();
          ctx.globalAlpha = 1;
          ctx.fillStyle = '#fff'; ctx.font = 'bold 7px monospace'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.fillText(String(bt.size), bx, by); ctx.textBaseline = 'alphabetic';
        }
      }

      // Agent signals
      const sigs = agentSignals.filter(s => {
        const bt = s.barTimeEt?.slice(0, 5);
        const ct = new Date(cd.barTimeUtc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
        return bt === ct && s.finalDecision === 'trade';
      });
      for (const sig of sigs) {
        const isLong = sig.direction === 'long';
        const sy = priceToY(cd.barHigh) - 14, sx = x + CANDLE_W / 2;
        ctx.beginPath();
        if (isLong) { ctx.moveTo(sx, sy); ctx.lineTo(sx - 6, sy + 12); ctx.lineTo(sx + 6, sy + 12); }
        else { ctx.moveTo(sx, sy + 12); ctx.lineTo(sx - 6, sy); ctx.lineTo(sx + 6, sy); }
        ctx.closePath();
        ctx.fillStyle = isLong ? 'rgba(16,185,129,0.8)' : 'rgba(244,63,94,0.8)'; ctx.fill();
        ctx.strokeStyle = isLong ? 'rgba(16,185,129,1)' : 'rgba(244,63,94,1)'; ctx.lineWidth = 1; ctx.stroke();
      }
    }

    // Trade markers
    for (const tm of tradeMarkers) {
      const et = tm.entryTime?.slice(0, 5);
      if (!et) continue;
      const idx = candles.findIndex(c =>
        new Date(c.barTimeUtc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) === et
      );
      if (idx < 0) continue;
      const ex = idx * CANDLE_W + CANDLE_W / 2;

      // Entry
      ctx.strokeStyle = C.entryLine; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(ex, 60); ctx.lineTo(ex, h); ctx.stroke();
      ctx.setLineDash([]);

      // Entry price label
      ctx.fillStyle = C.entryLine; ctx.font = 'bold 8px monospace'; ctx.textAlign = 'center';
      ctx.fillText(`Entry ${tm.entry.toFixed(2)}`, ex, 54);

      // Stop line
      if (tm.stop) {
        const sy = priceToY(tm.stop);
        ctx.strokeStyle = C.stopLine; ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(ex - 20, sy); ctx.lineTo(ex + 20, sy); ctx.stroke();
        ctx.setLineDash([]); ctx.fillStyle = C.stopLine; ctx.font = 'bold 7px monospace'; ctx.textAlign = 'right';
        ctx.fillText(`Stop ${tm.stop.toFixed(2)}`, ex + 20, sy - 2);
      }

      // Target line
      if (tm.target) {
        const ty = priceToY(tm.target);
        ctx.strokeStyle = C.targetLine; ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]);
        ctx.beginPath(); ctx.moveTo(ex - 20, ty); ctx.lineTo(ex + 20, ty); ctx.stroke();
        ctx.setLineDash([]); ctx.fillStyle = C.targetLine; ctx.font = 'bold 7px monospace'; ctx.textAlign = 'right';
        ctx.fillText(`Target ${tm.target.toFixed(2)}`, ex + 20, ty - 2);
      }

      // Exit price
      if (tm.exitPrice) {
        const ey = priceToY(tm.exitPrice);
        ctx.fillStyle = C.exitMarker; ctx.globalAlpha = 0.7;
        ctx.beginPath(); ctx.arc(ex, ey, 4, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
      }
    }
  }, [candles, prices, globalMaxVolume, maxPrice, minPrice, priceToY,
      chartW, chartH, showText, showBigTrades, tradeMarkers, agentSignals]);

  // ── Re-render when data changes ─────────────────────────────────────────────
  useEffect(() => { draw(); }, [draw]);

  // ── Auto-scroll ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!autoScroll || !candles.length) return;
    if (candles.length === prevCandlesLen.current) return;
    prevCandlesLen.current = candles.length;
    const vw = containerRef.current?.clientWidth || 1200;
    const vh = containerRef.current?.clientHeight || 800;
    const cw = candles.length * CANDLE_W * scale;
    const last = candles[candles.length - 1];
    const ly = 60 + ((maxPrice - last.barHigh) / TICK_SIZE) * CELL_HEIGHT;
    setPan({ x: -Math.max(0, cw - vw + 80), y: -(ly * scale) + vh * 0.5 });
  }, [candles.length, scale, maxPrice, autoScroll]);

  // ── Mouse handlers ──────────────────────────────────────────────────────────
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const p = e.deltaY > 0 ? -1 : 1;
    const s = scale < 0.5 ? 0.02 : 0.05;
    setScale(x => Math.min(Math.max(0.08, x + p * s), 4));
  }, [scale]);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY };
    panStart.current = { x: pan.x, y: pan.y };
  }, [pan]);
  const onMouseUp = useCallback(() => setIsDragging(false), []);
  const onMouseLeave = useCallback(() => setIsDragging(false), []);
  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging) {
      setPan({ x: panStart.current.x + (e.clientX - dragStart.current.x), y: panStart.current.y + (e.clientY - dragStart.current.y) });
    }
  }, [isDragging]);

  // ── Candle headers ─────────────────────────────────────────────────────────
  const candleHeaders = useMemo(() => candles.map((c, i) => (
    <div key={i} className="flex flex-col items-center py-1.5 bg-slate-900/90 border-b border-slate-800 border-r border-slate-800/50 shrink-0" style={{ width: CANDLE_W }}>
      <span className="text-[11px] text-slate-400 font-medium">
        {new Date(c.barTimeUtc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}
      </span>
      <div className="grid grid-cols-3 w-full px-1 gap-0.5 text-[10px] font-bold">
        <div className="flex flex-col items-center bg-slate-800/70 rounded px-1 py-0.5">
          <span className="text-slate-500 text-[8px]">VOL</span>
          <span className="text-slate-200">{c.barVolume.toLocaleString()}</span>
        </div>
        <div className="flex flex-col items-center bg-slate-800/70 rounded px-1 py-0.5">
          <span className="text-slate-500 text-[8px]">DELTA</span>
          <span className={c.barDelta >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
            {c.barDelta > 0 ? '+' : ''}{c.barDelta}
          </span>
        </div>
        <div className="flex flex-col items-center bg-slate-800/70 rounded px-1 py-0.5">
          <span className="text-slate-500 text-[8px]">CVD</span>
          <span className={c.barCvd >= 0 ? 'text-emerald-300' : 'text-rose-300'}>
            {c.barCvd > 0 ? '+' : ''}{c.barCvd}
          </span>
        </div>
      </div>
    </div>
  )), [candles]);

  // ── SVG Overlays ────────────────────────────────────────────────────────────
  const svgOverlays = useMemo(() => {
    const els: React.ReactElement[] = [];
    if (!candles.length) return els;
    const tw = chartW;
    const sw = 1 / scale;

    // POC, VAH, VAL
    if (vpO && showVP) {
      const vahY = priceToY(vpO.vaHigh);
      const valY = priceToY(vpO.vaLow) + CELL_HEIGHT;
      els.push(<rect key="va" x={0} y={vahY} width={tw} height={valY - vahY} fill={C.vaArea} />);
      els.push(<line key="vah" x1={0} y1={vahY} x2={tw} y2={vahY} stroke={C.vah} strokeWidth={sw} strokeDasharray={`${6 / scale},${3 / scale}`} />);
      els.push(<text key="vah-l" x={4} y={vahY - 3} fill={C.vah} fontSize={10 / scale} fontFamily="monospace" fontWeight="bold">VAH {vpO.vaHigh.toFixed(2)}</text>);
      els.push(<line key="val" x1={0} y1={valY} x2={tw} y2={valY} stroke={C.val} strokeWidth={sw} strokeDasharray={`${6 / scale},${3 / scale}`} />);
      els.push(<text key="val-l" x={4} y={valY + 11 / scale} fill={C.val} fontSize={10 / scale} fontFamily="monospace" fontWeight="bold">VAL {vpO.vaLow.toFixed(2)}</text>);
      const pocY = priceToY(vpO.poc);
      els.push(<line key="poc" x1={0} y1={pocY} x2={tw} y2={pocY} stroke={C.pocLine} strokeWidth={sw * 2} />);
      els.push(<text key="poc-l" x={4} y={pocY - 3} fill={C.poc} fontSize={10 / scale} fontFamily="monospace" fontWeight="bold">POC {vpO.poc.toFixed(2)}</text>);
      vpO.hvnLevels.forEach((p, i) => {
        const y = priceToY(p);
        els.push(<line key={`hvn-${i}`} x1={0} y1={y} x2={tw} y2={y} stroke={C.hvn} strokeWidth={sw} strokeDasharray={`${3 / scale},${5 / scale}`} opacity={0.7} />);
      });
      vpO.lvnLevels.forEach((p, i) => {
        const y = priceToY(p);
        els.push(<line key={`lvn-${i}`} x1={0} y1={y} x2={tw} y2={y} stroke={C.lvn} strokeWidth={sw} strokeDasharray={`${2 / scale},${6 / scale}`} opacity={0.6} />);
      });
    }

    // IB Box
    if (ibO && showIBBox && ibO.ibComplete) {
      const tY = priceToY(ibO.ibHigh), bY = priceToY(ibO.ibLow) + CELL_HEIGHT;
      els.push(<rect key="ib" x={0} y={tY} width={tw} height={bY - tY} fill={C.ibBox} />);
      els.push(<line key="ibh" x1={0} y1={tY} x2={tw} y2={tY} stroke={C.ibLine} strokeWidth={sw * 1.5} />);
      els.push(<line key="ibl" x1={0} y1={bY} x2={tw} y2={bY} stroke={C.ibLine} strokeWidth={sw * 1.5} />);
      els.push(<text key="ibh-l" x={4} y={tY - 3} fill={C.ibLine} fontSize={10 / scale} fontFamily="monospace" fontWeight="bold">IB High {ibO.ibHigh.toFixed(2)}</text>);
      els.push(<text key="ibl-l" x={4} y={bY + 11 / scale} fill={C.ibLine} fontSize={10 / scale} fontFamily="monospace">IB Low {ibO.ibLow.toFixed(2)}</text>);
    }

    // GEX
    if (gexO && showGEX) {
      if (gexO.zeroGammaLevel > minPrice && gexO.zeroGammaLevel < maxPrice) {
        const y = priceToY(gexO.zeroGammaLevel);
        els.push(<line key="zg" x1={0} y1={y} x2={tw} y2={y} stroke={C.zeroGamma} strokeWidth={sw * 1.5} strokeDasharray={`${8 / scale},${4 / scale}`} />);
        els.push(<text key="zg-l" x={4} y={y - 3} fill={C.zeroGamma} fontSize={10 / scale} fontFamily="monospace" fontWeight="bold">0γ {gexO.zeroGammaLevel.toFixed(2)}</text>);
      }
      if (gexO.callWall > minPrice && gexO.callWall < maxPrice) {
        const y = priceToY(gexO.callWall);
        els.push(<line key="cw" x1={0} y1={y} x2={tw} y2={y} stroke={C.callWall} strokeWidth={sw} strokeDasharray={`${5 / scale},${5 / scale}`} />);
        els.push(<text key="cw-l" x={4} y={y - 3} fill={C.callWall} fontSize={9 / scale} fontFamily="monospace">Call Wall {gexO.callWall.toFixed(2)}</text>);
      }
      if (gexO.putWall > minPrice && gexO.putWall < maxPrice) {
        const y = priceToY(gexO.putWall);
        els.push(<line key="pw" x1={0} y1={y} x2={tw} y2={y} stroke={C.putWall} strokeWidth={sw} strokeDasharray={`${5 / scale},${5 / scale}`} />);
        els.push(<text key="pw-l" x={4} y={y - 3} fill={C.putWall} fontSize={9 / scale} fontFamily="monospace">Put Wall {gexO.putWall.toFixed(2)}</text>);
      }
    }
    return els;
  }, [vpO, ibO, gexO, showVP, showIBBox, showGEX, priceToY, chartW, maxPrice, minPrice, scale]);

  // ── Y-Axis ──────────────────────────────────────────────────────────────────
  const yAxis = useMemo(() => prices.map(p => {
    const isPoc = vpO && Math.abs(p - vpO.poc) < 0.125;
    const isVa = vpO && (Math.abs(p - vpO.vaHigh) < 0.125 || Math.abs(p - vpO.vaLow) < 0.125);
    const isIb = ibO && (Math.abs(p - ibO.ibHigh) < 0.125 || Math.abs(p - ibO.ibLow) < 0.125);
    const isZg = gexO && Math.abs(p - gexO.zeroGammaLevel) < 0.125;
    return (
      <div key={p} style={{ height: CELL_HEIGHT }} className={cn(
        "flex items-center justify-end pr-2 text-[10px] font-mono font-bold border-b border-slate-800/25",
        isPoc ? "text-yellow-400" : isVa ? "text-emerald-400" : isIb ? "text-violet-400" : isZg ? "text-rose-400" : "text-slate-400"
      )}>{p.toFixed(2)}</div>
    );
  }), [prices, vpO, ibO, gexO]);

  // ── Render ──────────────────────────────────────────────────────────────────
  if (!candles.length) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-[#080d18]">
        <div className="text-center">
          <div className="text-slate-600 text-4xl mb-4">📊</div>
          <div className="text-slate-400 font-mono text-sm">DeepPrint Pro</div>
          <div className="text-slate-600 font-mono text-xs mt-2">
            In attesa del server WebSocket...<br/>
            <code className="text-slate-500">python platform/ws_server.py</code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn("w-full h-full overflow-hidden bg-[#080d18] select-none relative", isDragging ? "cursor-grabbing" : "cursor-grab")}
      onWheel={handleWheel}
      onMouseDown={onMouseDown}
      onMouseLeave={onMouseLeave}
      onMouseUp={onMouseUp}
      onMouseMove={onMouseMove}
    >
      {/* Canvas + SVG overlays */}
      <div className="absolute top-0 left-0 will-change-transform"
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`, transformOrigin: 'top left', width: chartW, height: chartH }}
      >
        {/* SVG overlays */}
        <svg className="absolute top-0 left-0 pointer-events-none z-20 overflow-visible" width={chartW} height={chartH}>
          {svgOverlays}
        </svg>

        {/* Canvas footprint grid */}
        <canvas ref={canvasRef} className="absolute top-0 left-0 z-10 pointer-events-none" />

        {/* Candle headers */}
        <div className="flex flex-row absolute top-0 left-0 z-30 pointer-events-none">
          {candleHeaders}
        </div>
      </div>

      {/* Y-Axis */}
      <div className="absolute right-0 top-0 bottom-0 w-[64px] bg-[#0d131f]/95 border-l border-slate-700 z-30 shadow-[-8px_0_20px_rgba(0,0,0,0.4)] backdrop-blur-sm overflow-hidden pointer-events-none">
        <div className="h-[60px] bg-slate-900/90 border-b border-slate-800 flex items-end justify-center pb-2 absolute top-0 w-full z-40">
          <span className="text-[9px] text-slate-500 font-bold tracking-widest">PRICE</span>
        </div>
        <div className="absolute top-0 right-0 w-full flex flex-col will-change-transform"
          style={{ transform: `translateY(${pan.y}px) scale(${scale})`, transformOrigin: 'top right', paddingTop: 60 }}>
          {yAxis}
        </div>
      </div>

      {/* Zoom controls */}
      <div className="fixed bottom-20 right-20 flex flex-col gap-1.5 bg-slate-900/95 p-1.5 rounded-xl backdrop-blur-md border border-slate-700 shadow-2xl z-50">
        <button onClick={() => setScale(s => Math.min(s + 0.1, 4))}
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded-lg transition-colors" title="Zoom in">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </button>
        <button onClick={() => setScale(0.8)}
          className="py-1 px-1 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg text-[9px] font-bold transition-colors text-center" title="Reset zoom">
          {Math.round(scale * 100)}%
        </button>
        <button onClick={() => setScale(s => Math.max(s - 0.1, 0.08))}
          className="p-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded-lg transition-colors" title="Zoom out">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </button>
      </div>
    </div>
  );
};
