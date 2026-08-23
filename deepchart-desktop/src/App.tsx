/**
 * App.tsx — DeepPrint Pro v2.0
 * Layout principale con:
 * - Left sidebar (navigazione)
 * - Top header (symbol, timeframe, status WS)
 * - SessionInfoBar (IB, day_type, GEX)
 * - Main area: FootprintChart + VolumeProfile Sidebar + OrderBook DOM
 * - CVD Chart (pannello inferiore)
 * - ReplayControls (barra basso)
 * - AlertPanel (notifiche toast)
 * - Keyboard shortcuts
 */
import React, { useEffect, useCallback } from 'react';
import { Activity, Settings, Database, Crosshair, BarChart2, Eye, EyeOff } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import { FootprintChart }       from './components/FootprintChart';
import { VolumeProfileSidebar } from './components/VolumeProfileSidebar';
import { CVDChart }             from './components/CVDChart';
import { ReplayControls }       from './components/ReplayControls';
import { SessionInfoBar }       from './components/SessionInfoBar';
import { AlertPanel }           from './components/AlertPanel';
import { RoadmapPanel }        from './components/RoadmapPanel';
import { AgentSignalsPanel }   from './components/AgentSignalsPanel';
import { TradeMarkersPanel }   from './components/TradeMarkersPanel';
import { useWebSocket }         from './hooks/useWebSocket';
import { useTradingStore }      from './store/tradingStore';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ─── OrderBook DOM (componente inline) ───────────────────────────────────────
const OrderBookDOM: React.FC = () => {
  const { domData, candles } = useTradingStore();

  // Se nessun dato DOM live, genera DOM simulato dall'ultima candela
  const lastClose = candles[candles.length - 1]?.barClose ?? 21500;

  const generateSimulatedDOM = () => {
    const bids = Array.from({ length: 15 }, (_, i) => ({
      price: lastClose - (i + 1) * 0.25,
      size:  Math.max(1, Math.floor(Math.random() * 40 + 5)),
    }));
    const asks = Array.from({ length: 15 }, (_, i) => ({
      price: lastClose + (i + 1) * 0.25,
      size:  Math.max(1, Math.floor(Math.random() * 40 + 5)),
    }));
    return { bids, asks };
  };

  const dom = domData || generateSimulatedDOM();
  const maxSize = Math.max(
    ...dom.bids.map(b => b.size),
    ...dom.asks.map(a => a.size),
    1
  );

  return (
    <div className="w-[168px] bg-[#0b1020] flex flex-col shrink-0 border-l border-slate-800">
      {/* Header */}
      <div className="h-6 bg-slate-900/80 border-b border-slate-700 flex items-center justify-center shrink-0">
        <span className="text-[9px] text-slate-400 font-bold tracking-widest">ORDER BOOK</span>
      </div>

      {/* Column headers */}
      <div className="flex justify-between text-[9px] text-slate-600 border-b border-slate-800 px-2 py-0.5 shrink-0 font-mono">
        <span>BID SZ</span>
        <span>PRICE</span>
        <span>ASK SZ</span>
      </div>

      {/* Ask side (sopra, top→bottom = higher price → lower price) */}
      <div className="flex flex-col-reverse overflow-hidden" style={{ maxHeight: '45%' }}>
        {dom.asks.slice(0, 15).reverse().map((ask, i) => (
          <div key={`ask-${i}`} className="flex justify-between items-center text-[10px] font-mono py-0.5 px-2 relative hover:bg-slate-800/40">
            <div
              className="absolute right-0 top-0 bottom-0 bg-rose-900/30"
              style={{ width: `${(ask.size / maxSize) * 60}%` }}
            />
            <span className="text-slate-600 z-10">—</span>
            <span className="text-rose-200 font-bold z-10">{ask.price.toFixed(2)}</span>
            <span className="text-rose-400 z-10">{ask.size}</span>
          </div>
        ))}
      </div>

      {/* Spread / Last trade */}
      <div className="flex items-center justify-center py-1.5 bg-slate-800/60 border-y border-slate-700 shrink-0">
        <span className="text-[13px] font-mono font-black text-white">{lastClose.toFixed(2)}</span>
      </div>

      {/* Bid side */}
      <div className="flex flex-col overflow-hidden" style={{ maxHeight: '45%' }}>
        {dom.bids.slice(0, 15).map((bid, i) => (
          <div key={`bid-${i}`} className="flex justify-between items-center text-[10px] font-mono py-0.5 px-2 relative hover:bg-slate-800/40">
            <div
              className="absolute left-0 top-0 bottom-0 bg-emerald-900/30"
              style={{ width: `${(bid.size / maxSize) * 60}%` }}
            />
            <span className="text-emerald-400 z-10">{bid.size}</span>
            <span className="text-emerald-200 font-bold z-10">{bid.price.toFixed(2)}</span>
            <span className="text-slate-600 z-10">—</span>
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="mt-auto border-t border-slate-800 p-2 text-[9px] font-mono text-slate-600 space-y-0.5 shrink-0">
        {domData ? (
          <>
            <div className="flex justify-between">
              <span>Last</span>
              <span className="text-slate-300">{domData.lastTradePrice?.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Size</span>
              <span className={domData.lastTradeSide === 'A' ? 'text-emerald-400' : 'text-rose-400'}>
                {domData.lastTradeSize}
              </span>
            </div>
          </>
        ) : (
          <span className="text-slate-700 italic">DOM simulato</span>
        )}
      </div>
    </div>
  );
};

// ─── Toolbar Toggle Button ────────────────────────────────────────────────────
interface ToggleBtnProps {
  label: string;
  active: boolean;
  onToggle: () => void;
}
const ToggleBtn: React.FC<ToggleBtnProps> = ({ label, active, onToggle }) => (
  <button
    onClick={onToggle}
    className={cn(
      "flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold transition-all border",
      active
        ? "bg-blue-600/30 text-blue-300 border-blue-700/60"
        : "bg-slate-800/50 text-slate-500 border-slate-700/40 hover:text-slate-300"
    )}
  >
    {active ? <Eye size={10} /> : <EyeOff size={10} />}
    {label}
  </button>
);

// ─── App principale ───────────────────────────────────────────────────────────
export default function App() {
  const { send } = useWebSocket();
  void send; // suppress unused warning

  const {
    wsStatus,
    candles,
    replayMode,
    replaySpeed,
    showVP,       setShowVP,
    showGEX,      setShowGEX,
    showIBBox,    setShowIBBox,
    showCVD,      setShowCVD,
    showBigTrades, setShowBigTrades,
    showCleanData, setShowCleanData,
    sendWsMessage,
  } = useTradingStore();

  // ── Keyboard shortcuts ───────────────────────────────────────────────────
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Non intervenire se focus su input/select
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) return;

    switch (e.key) {
      case ' ':
        e.preventDefault();
        if (replayMode === 'replay') sendWsMessage?.({ action: 'replay_pause' });
        else                         sendWsMessage?.({ action: 'replay_play'  });
        break;
      case 'ArrowRight':
        sendWsMessage?.({ action: 'replay_step_forward' });
        break;
      case 'ArrowLeft':
        sendWsMessage?.({ action: 'replay_step_back' });
        break;
      case '+':
      case '=':
        sendWsMessage?.({ action: 'set_speed', multiplier: Math.min(replaySpeed * 2, 99999) });
        break;
      case '-':
        sendWsMessage?.({ action: 'set_speed', multiplier: Math.max(replaySpeed / 2, 30) });
        break;
    }
  }, [replayMode, replaySpeed, sendWsMessage]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // ── Render ───────────────────────────────────────────────────────────────
  const lastCandle = candles[candles.length - 1];

  return (
    <div className="flex h-screen bg-[#070c18] text-slate-200 font-sans overflow-hidden">

      {/* ── Left Sidebar (navigation icons) ──────────────────────────────── */}
      <aside className="w-14 bg-[#0a0e17] border-r border-slate-800 flex flex-col items-center py-3 gap-5 z-20 shrink-0">
        <div className="flex flex-col items-center gap-1.5">
          {/* Logo */}
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-900/40">
            <span className="text-white text-[10px] font-black">DP</span>
          </div>
        </div>

        <div className="flex flex-col gap-3 mt-2">
          {[
            { icon: Activity,  label: 'Chart'    },
            { icon: BarChart2, label: 'Stats'    },
            { icon: Crosshair, label: 'Segnali'  },
            { icon: Database,  label: 'Dati'     },
          ].map(({ icon: Icon, label }) => (
            <button
              key={label}
              className="p-2 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-all"
              title={label}
            >
              <Icon size={18} />
            </button>
          ))}
        </div>

        <button
          className="mt-auto p-2 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-all"
          title="Impostazioni"
        >
          <Settings size={18} />
        </button>
      </aside>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">

        {/* ── Top Header ─────────────────────────────────────────────────── */}
        <header className="h-12 bg-[#0a0e17] border-b border-slate-800 flex items-center px-4 justify-between shrink-0 z-10">
          {/* Left: symbol + timeframe */}
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-black bg-gradient-to-r from-blue-400 via-indigo-300 to-emerald-400 bg-clip-text text-transparent">
              DeepPrint Pro
            </h1>
            <div className="h-4 w-px bg-slate-800" />
            <div className="flex items-center gap-1.5 text-xs font-mono bg-slate-900/60 px-2 py-1 rounded-full border border-slate-700/50">
              <span className="text-blue-300 font-bold">MNQ</span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-300">1 Min</span>
            </div>
            {lastCandle && (
              <>
                <div className="h-4 w-px bg-slate-800" />
                <span className="text-xs font-mono font-bold text-white">
                  {lastCandle.barClose.toFixed(2)}
                </span>
                <span className={cn(
                  "text-xs font-mono",
                  lastCandle.barDelta >= 0 ? "text-emerald-400" : "text-rose-400"
                )}>
                  {lastCandle.barDelta >= 0 ? '▲' : '▼'} {Math.abs(lastCandle.barDelta)}
                </span>
              </>
            )}
          </div>

          {/* Center: overlay toggles */}
          <div className="flex items-center gap-1.5">
            <ToggleBtn label="VP"     active={showVP}        onToggle={() => setShowVP(!showVP)} />
            <ToggleBtn label="IB"     active={showIBBox}     onToggle={() => setShowIBBox(!showIBBox)} />
            <ToggleBtn label="GEX"    active={showGEX}       onToggle={() => setShowGEX(!showGEX)} />
            <ToggleBtn label="CVD"    active={showCVD}       onToggle={() => setShowCVD(!showCVD)} />
            <ToggleBtn label="Bolle"  active={showBigTrades} onToggle={() => setShowBigTrades(!showBigTrades)} />
            <ToggleBtn label="Clean"  active={showCleanData} onToggle={() => setShowCleanData(!showCleanData)} />
          </div>

          {/* Right: WS status + candele count */}
          <div className="flex items-center gap-3 text-xs font-mono">
            {candles.length > 0 && (
              <span className="text-slate-600">{candles.length} barre</span>
            )}
            <div className="flex items-center gap-1.5 bg-slate-900/50 px-3 py-1.5 rounded-full border border-slate-700/50">
              <span className="relative flex h-2 w-2">
                <span className={cn(
                  "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                  wsStatus === 'connected' ? "bg-emerald-400" :
                  wsStatus === 'connecting' ? "bg-amber-400" : "bg-rose-400"
                )} />
                <span className={cn(
                  "relative inline-flex rounded-full h-2 w-2",
                  wsStatus === 'connected' ? "bg-emerald-500" :
                  wsStatus === 'connecting' ? "bg-amber-500" : "bg-rose-500"
                )} />
              </span>
              <span className={cn(
                "font-bold text-[10px] tracking-wider",
                wsStatus === 'connected' ? "text-emerald-400" :
                wsStatus === 'connecting' ? "text-amber-400" : "text-rose-400"
              )}>
                {wsStatus === 'connected'  ? 'LIVE SYNC' :
                 wsStatus === 'connecting' ? 'CONNECTING' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </header>

        {/* ── SessionInfoBar ──────────────────────────────────────────────── */}
        <SessionInfoBar />

        {/* ── Content workspace ──────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">

          {/* Chart area + sidebars */}
          <div className="flex flex-1 min-h-0 overflow-hidden">

            {/* FootprintChart (area principale) */}
            <div className="flex-1 relative min-w-0 overflow-hidden">
              <FootprintChart autoScroll={replayMode === 'replay'} />
            </div>

            {/* Volume Profile Sidebar */}
            {showVP && (
              <VolumeProfileSidebar
                maxPrice={candles.length > 0
                  ? Math.max(...candles.map(c => c.barHigh)) + 4
                  : 21600}
                minPrice={candles.length > 0
                  ? Math.min(...candles.map(c => c.barLow)) - 4
                  : 21400}
                cellHeight={CELL_HEIGHT_EXPORT}
                panY={0}
                scale={1}
              />
            )}

            {/* Order Book DOM */}
            <OrderBookDOM />

            {/* Clean Data Panel (Roadmap + Agent Signals + Trade Markers) */}
            {showCleanData && (
              <div className="w-[260px] bg-[#0b1020] border-l border-slate-800 flex flex-col shrink-0 overflow-y-auto">
                <div className="h-6 bg-slate-900/80 border-b border-slate-700 flex items-center justify-center shrink-0">
                  <span className="text-[9px] text-slate-400 font-bold tracking-widest">DEEP DATA</span>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                  <RoadmapPanel />
                  <AgentSignalsPanel />
                  <TradeMarkersPanel />
                </div>
              </div>
            )}
          </div>

          {/* CVD Chart (pannello inferiore opzionale) */}
          {showCVD && (
            <CVDChart height={90} />
          )}
        </div>

        {/* ── ReplayControls ─────────────────────────────────────────────── */}
        <ReplayControls />
      </main>

      {/* ── Alert Panel ────────────────────────────────────────────────────── */}
      <AlertPanel />

      {/* ── Keyboard hints (visible solo quando nessun dato) ─────────────── */}
      {candles.length === 0 && wsStatus === 'disconnected' && (
        <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-50">
          <div className="bg-slate-900/95 border border-slate-700 rounded-xl p-6 text-center shadow-2xl max-w-sm">
            <div className="text-4xl mb-3">🚀</div>
            <div className="text-white font-bold text-sm mb-2">DeepPrint Pro</div>
            <div className="text-slate-400 text-xs mb-4">Piattaforma Volumetrica NQ Futures</div>
            <div className="bg-slate-800 rounded-lg p-3 text-left text-xs font-mono text-slate-300 space-y-1">
              <div className="text-slate-500"># Avvia il server:</div>
              <div className="text-emerald-400">python platform/ws_server.py</div>
            </div>
            <div className="mt-3 text-[10px] text-slate-600 space-y-0.5">
              <div>SPACE = play/pause · → ← = step · + - = speed</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Esporta cell height per VP sidebar sync
export const CELL_HEIGHT_EXPORT = 22;
