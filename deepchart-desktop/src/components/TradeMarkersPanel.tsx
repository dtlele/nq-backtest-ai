/**
 * TradeMarkersPanel — Trade eseguiti del giorno dal CleanBridge.
 * Tabella: entry/stop/target, exitReason, pnlUsd (verde/rosso).
 * Totale P&L giornata in testa.
 * Stile coerente con AlertPanel.
 */
import React, { useState, useMemo } from 'react';
import { useTradingStore, TradeMarker } from '../store/tradingStore';
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown, AlertCircle, DollarSign } from 'lucide-react';

// ─── TradeRow ─────────────────────────────────────────────────────────────────

const TradeRow: React.FC<{ trade: TradeMarker }> = ({ trade }) => {
  const [expanded, setExpanded] = useState(false);
  const isLong = trade.direction === 'long' || trade.direction === 'buy';

  return (
    <div
      className={`border rounded cursor-pointer transition-all ${
        trade.pnlUsd >= 0
          ? 'border-emerald-800/40 bg-emerald-950/15 hover:bg-emerald-950/30'
          : 'border-rose-800/40 bg-rose-950/15 hover:bg-rose-950/30'
      }`}
      onClick={() => setExpanded(e => !e)}
    >
      {/* Riga compatta */}
      <div className="flex items-center gap-2 px-2 py-1.5 text-[10px] font-mono">
        {/* Direction icon */}
        <span className={isLong ? 'text-emerald-400' : 'text-rose-400'}>
          {isLong ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
        </span>

        {/* Entry time */}
        <span className="text-slate-400 w-10 shrink-0">{trade.entryTime?.slice(0, 5) || '--:--'}</span>

        {/* Entry price */}
        <span className="text-slate-300 w-14 shrink-0">{trade.entry?.toFixed(2)}</span>

        {/* PnL */}
        <span className={`font-bold shrink-0 ${
          trade.pnlUsd >= 0 ? 'text-emerald-400' : 'text-rose-400'
        }`}>
          {trade.pnlUsd >= 0 ? '+' : ''}{trade.pnlUsd?.toFixed(0)}
        </span>

        {/* Exit reason */}
        <span className="text-slate-500 truncate flex-1 text-[9px]">{trade.exitReason || '—'}</span>

        {/* Expand */}
        {expanded ? <ChevronDown size={10} className="text-slate-600 shrink-0" /> : <ChevronRight size={10} className="text-slate-600 shrink-0" />}
      </div>

      {/* Detail espanso */}
      {expanded && (
        <div className="px-2 pb-2 space-y-1.5 border-t border-slate-800/50 pt-1.5">
          <div className="grid grid-cols-3 gap-1 text-[9px] font-mono">
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">Entry</span>
              <div className="text-slate-200 font-bold">{trade.entry?.toFixed(2)}</div>
            </div>
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">Stop</span>
              <div className="text-rose-300 font-bold">{trade.stop?.toFixed(2)}</div>
            </div>
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">Target</span>
              <div className="text-emerald-300 font-bold">{trade.target?.toFixed(2)}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-1 text-[9px] font-mono">
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">Exit</span>
              <div className="text-slate-300">{trade.exitPrice?.toFixed(2)}</div>
            </div>
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">Reason</span>
              <div className="text-slate-300">{trade.exitReason || '—'}</div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-1 text-[9px] font-mono">
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">PnL Ticks</span>
              <div className={trade.pnlTicks >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{trade.pnlTicks >= 0 ? '+' : ''}{trade.pnlTicks}</div>
            </div>
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">Contracts</span>
              <div className="text-slate-300">{trade.contracts}</div>
            </div>
            <div className="bg-slate-900/60 rounded p-1">
              <span className="text-slate-500">Setup</span>
              <div className="text-slate-300">{trade.setupType || '—'}</div>
            </div>
          </div>

          {trade.fabioReasoning && (
            <div className="bg-blue-950/20 border border-blue-800/30 rounded p-1.5">
              <span className="text-[8px] font-bold text-blue-300 uppercase tracking-wider">Fabio</span>
              <div className="text-[9px] text-slate-400 font-mono mt-0.5 leading-relaxed">
                {trade.fabioReasoning.slice(0, 200)}{trade.fabioReasoning.length > 200 ? '...' : ''}
              </div>
            </div>
          )}

          {trade.andreaReasoning && (
            <div className="bg-violet-950/20 border border-violet-800/30 rounded p-1.5">
              <span className="text-[8px] font-bold text-violet-300 uppercase tracking-wider">Andrea</span>
              <div className="text-[9px] text-slate-400 font-mono mt-0.5 leading-relaxed">
                {trade.andreaReasoning.slice(0, 200)}{trade.andreaReasoning.length > 200 ? '...' : ''}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ─── TradeMarkersPanel ────────────────────────────────────────────────────────

export const TradeMarkersPanel: React.FC = () => {
  const { tradeMarkers } = useTradingStore();
  const [collapsed, setCollapsed] = useState(false);

  const totalPnl = useMemo(
    () => tradeMarkers.reduce((sum, t) => sum + (t.pnlUsd || 0), 0),
    [tradeMarkers]
  );

  const winCount = useMemo(
    () => tradeMarkers.filter(t => (t.pnlUsd || 0) > 0).length,
    [tradeMarkers]
  );

  return (
    <div className="w-full bg-[#0b1020] border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-900/60 border-b border-slate-800 hover:bg-slate-800/70 transition-colors"
      >
        <div className="flex items-center gap-2">
          <DollarSign size={13} className="text-amber-400" />
          <span className="text-[11px] font-bold text-white tracking-wide">TRADE ESEGUITI</span>
          {tradeMarkers.length > 0 && (
            <>
              <span className="text-[10px] font-mono text-slate-500">{tradeMarkers.length}</span>
              <span className={`text-[10px] font-bold font-mono ${
                totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(0)} USD
              </span>
            </>
          )}
        </div>
        {collapsed ? <ChevronRight size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
      </button>

      {!collapsed && (
        <div className="max-h-80 overflow-y-auto">
          {/* Stats bar */}
          {tradeMarkers.length > 0 && (
            <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-900/30 border-b border-slate-800/50 text-[9px] font-mono">
              <span className="text-slate-500">
                Win: <span className="text-emerald-400 font-bold">{winCount}/{tradeMarkers.length}</span>
              </span>
              <span className="text-slate-500">
                WinRate: <span className="text-slate-300 font-bold">
                  {tradeMarkers.length > 0 ? ((winCount / tradeMarkers.length) * 100).toFixed(0) : 0}%
                </span>
              </span>
              <span className="text-slate-500">
                Avg: <span className={totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                  {(totalPnl / tradeMarkers.length).toFixed(0)}
                </span>
              </span>
            </div>
          )}

          <div className="p-2 space-y-1">
            {tradeMarkers.length === 0 ? (
              <div className="flex items-center justify-center py-6">
                <div className="text-center">
                  <AlertCircle size={18} className="text-slate-600 mx-auto mb-1" />
                  <div className="text-[10px] text-slate-600 italic">Nessun trade</div>
                  <div className="text-[9px] text-slate-700">per questa data</div>
                </div>
              </div>
            ) : (
              tradeMarkers.map((t, i) => (
                <TradeRow key={`trade-${i}`} trade={t} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};