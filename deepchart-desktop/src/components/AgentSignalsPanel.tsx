/**
 * AgentSignalsPanel — Lista candidati agente (Fabio/Andrea) per la sessione.
 * Ogni riga: ora ET, badge decisione, direction, confidence, setup.
 * Click → espande detail completo.
 * Stile coerente con AlertPanel.
 */
import React, { useState } from 'react';
import { useTradingStore, AgentSignalExt } from '../store/tradingStore';
import { ChevronDown, ChevronRight, AlertCircle, Brain } from 'lucide-react';

// ─── SignalRow ────────────────────────────────────────────────────────────────

const SignalRow: React.FC<{ signal: AgentSignalExt }> = ({ signal }) => {
  const [expanded, setExpanded] = useState(false);
  const isTrade = signal.finalDecision === 'trade';

  return (
    <div
      className={`border rounded cursor-pointer transition-all ${
        isTrade
          ? 'border-emerald-800/50 bg-emerald-950/20 hover:bg-emerald-950/40'
          : 'border-slate-800/50 bg-slate-900/30 hover:bg-slate-800/40'
      }`}
      onClick={() => setExpanded(e => !e)}
    >
      {/* Riga compatta */}
      <div className="flex items-center gap-2 px-2 py-1.5 text-[10px] font-mono">
        {/* Ora */}
        <span className="text-slate-400 w-10 shrink-0">{signal.barTimeEt?.slice(0, 5) || '--:--'}</span>

        {/* Badge decisione */}
        <span className={`shrink-0 text-[8px] font-bold px-1 py-0.5 rounded uppercase tracking-wider ${
          isTrade
            ? 'bg-emerald-700/60 text-emerald-200'
            : 'bg-slate-700/60 text-slate-400'
        }`}>
          {isTrade ? 'TRADE' : 'NO'}
        </span>

        {/* Direction */}
        <span className={`font-bold w-8 shrink-0 ${
          signal.direction === 'long' ? 'text-emerald-400' :
          signal.direction === 'short' ? 'text-rose-400' : 'text-slate-500'
        }`}>
          {signal.direction === 'long' ? '▲' : signal.direction === 'short' ? '▼' : '—'}
        </span>

        {/* Confidence */}
        <span className={`font-bold shrink-0 ${
          signal.confidence >= 78 ? 'text-emerald-300' :
          signal.confidence >= 60 ? 'text-amber-300' : 'text-slate-400'
        }`}>
          {signal.confidence}%
        </span>

        {/* Setup */}
        <span className="text-slate-400 truncate flex-1">{signal.setupType || '—'}</span>

        {/* Expand icon */}
        {expanded ? <ChevronDown size={10} className="text-slate-600 shrink-0" /> : <ChevronRight size={10} className="text-slate-600 shrink-0" />}
      </div>

      {/* Detail espanso */}
      {expanded && (
        <div className="px-2 pb-2 space-y-1.5 border-t border-slate-800/50 pt-1.5">
          {/* Reasoning */}
          {signal.reasoning && (
            <div className="text-[9px] text-slate-400 font-mono leading-relaxed bg-slate-900/60 rounded p-1.5">
              {signal.reasoning.slice(0, 250)}{signal.reasoning.length > 250 ? '...' : ''}
            </div>
          )}

          {/* Dettaglio Fabio */}
          {signal.detail?.fabio && (
            <div className="bg-blue-950/20 border border-blue-800/30 rounded p-1.5">
              <span className="text-[8px] font-bold text-blue-300 uppercase tracking-wider">Fabio</span>
              <div className="text-[9px] text-slate-400 font-mono mt-0.5 space-y-0.5">
                {signal.detail.fabio.setup && <div>Setup: {signal.detail.fabio.setup}</div>}
                {signal.detail.fabio.entry && <div>Entry: {signal.detail.fabio.entry}</div>}
                {signal.detail.fabio.stop && <div>Stop: {signal.detail.fabio.stop}</div>}
                {signal.detail.fabio.target && <div>Target: {signal.detail.fabio.target}</div>}
                {signal.detail.fabio.imbalancePhase && <div>Imbalance: {signal.detail.fabio.imbalancePhase}</div>}
              </div>
            </div>
          )}

          {/* Dettaglio Andrea */}
          {signal.detail?.andrea && (
            <div className="bg-violet-950/20 border border-violet-800/30 rounded p-1.5">
              <span className="text-[8px] font-bold text-violet-300 uppercase tracking-wider">Andrea</span>
              <div className="text-[9px] text-slate-400 font-mono mt-0.5 space-y-0.5">
                <div>Confirmation: {signal.detail.andrea.confirmation}</div>
                {signal.detail.andrea.confidence && <div>Confidence: {signal.detail.andrea.confidence}%</div>}
                {signal.detail.andrea.setup && <div>Setup: {signal.detail.andrea.setup}</div>}
              </div>
            </div>
          )}

          {/* Contesto */}
          {signal.detail?.context && (
            <div className="bg-amber-950/20 border border-amber-800/30 rounded p-1.5">
              <span className="text-[8px] font-bold text-amber-300 uppercase tracking-wider">Contesto</span>
              <div className="text-[9px] text-slate-400 font-mono mt-0.5 space-y-0.5">
                {signal.detail.context.dayType && <div>Day Type: {signal.detail.context.dayType}</div>}
                {signal.detail.context.marketState && <div>Market: {signal.detail.context.marketState}</div>}
                {signal.detail.context.macroRegime && <div>Regime: {signal.detail.context.macroRegime}</div>}
                {signal.detail.context.poc && <div>POC: {signal.detail.context.poc}</div>}
                {signal.detail.context.vaHigh && <div>VAH: {signal.detail.context.vaHigh}</div>}
                {signal.detail.context.vaLow && <div>VAL: {signal.detail.context.vaLow}</div>}
                {signal.detail.context.ibHigh && <div>IBH: {signal.detail.context.ibHigh}</div>}
                {signal.detail.context.ibLow && <div>IBL: {signal.detail.context.ibLow}</div>}
                {signal.detail.context.wallLevel && <div>Wall: {signal.detail.context.wallLevel} ({signal.detail.context.wallSide})</div>}
                {signal.detail.context.ignitionLabel && <div>Ignition: {signal.detail.context.ignitionLabel}</div>}
                {signal.detail.context.newsFlag && <div>News: {signal.detail.context.newsFlag}</div>}
              </div>
            </div>
          )}

          {/* Risultato */}
          {signal.detail?.result && signal.detail.result.pnlUsd !== 0 && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded p-1.5">
              <span className="text-[8px] font-bold text-slate-300 uppercase tracking-wider">Risultato</span>
              <div className="text-[9px] font-mono mt-0.5 space-y-0.5">
                <div className={signal.detail.result.pnlUsd >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                  PnL: {signal.detail.result.pnlUsd >= 0 ? '+' : ''}{signal.detail.result.pnlUsd?.toFixed(2)} USD
                </div>
                {signal.detail.result.exitReason && (
                  <div className="text-slate-400">Exit: {signal.detail.result.exitReason}</div>
                )}
              </div>
            </div>
          )}

          {signal.noTradeReason && !isTrade && (
            <div className="text-[9px] text-slate-500 italic font-mono">
              Motivo: {signal.noTradeReason}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ─── AgentSignalsPanel ────────────────────────────────────────────────────────

export const AgentSignalsPanel: React.FC = () => {
  const { agentSignals } = useTradingStore();
  const [collapsed, setCollapsed] = useState(false);

  const tradeSignals = agentSignals.filter(s => s.finalDecision === 'trade');
  const noTradeSignals = agentSignals.filter(s => s.finalDecision !== 'trade');

  return (
    <div className="w-full bg-[#0b1020] border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-900/60 border-b border-slate-800 hover:bg-slate-800/70 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain size={13} className="text-indigo-400" />
          <span className="text-[11px] font-bold text-white tracking-wide">CANDIDATI</span>
          <span className="text-[10px] font-mono text-slate-500">
            {agentSignals.length}
          </span>
          {tradeSignals.length > 0 && (
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded">
              {tradeSignals.length} trade
            </span>
          )}
        </div>
        {collapsed ? <ChevronRight size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
      </button>

      {!collapsed && (
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {agentSignals.length === 0 ? (
            <div className="flex items-center justify-center py-6">
              <div className="text-center">
                <AlertCircle size={18} className="text-slate-600 mx-auto mb-1" />
                <div className="text-[10px] text-slate-600 italic">Nessun candidato</div>
                <div className="text-[9px] text-slate-700">per questa data</div>
              </div>
            </div>
          ) : (
            <>
              {/* Trade signals first */}
              {tradeSignals.map((s, i) => (
                <SignalRow key={`trade-${i}`} signal={s} />
              ))}
              {/* No-trade signals */}
              {noTradeSignals.map((s, i) => (
                <SignalRow key={`notrade-${i}`} signal={s} />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
};
