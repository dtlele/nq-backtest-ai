/**
 * SessionInfoBar — Barra superiore con info sessione (IB, day_type, GEX, status WS).
 */
import React from 'react';
import { useTradingStore } from '../store/tradingStore';

const DAY_TYPE_COLORS: Record<string, string> = {
  trend_up:         'text-emerald-400 bg-emerald-900/30',
  trend_down:       'text-rose-400 bg-rose-900/30',
  balance:          'text-blue-400 bg-blue-900/30',
  transition_state: 'text-amber-400 bg-amber-900/30',
  unknown:          'text-slate-400 bg-slate-800',
};

const GEX_COLORS: Record<string, string> = {
  positive: 'text-emerald-400',
  negative: 'text-rose-400',
  unknown:  'text-slate-400',
};

export const SessionInfoBar: React.FC = () => {
  const { sessionCtx, wsStatus, replayDate } = useTradingStore();

  const dayTypeStr = sessionCtx?.dayType?.replace('_', ' ').toUpperCase() || 'UNKNOWN';
  const dayTypeColor = DAY_TYPE_COLORS[sessionCtx?.dayType || 'unknown'] || DAY_TYPE_COLORS.unknown;
  const gexColor = GEX_COLORS[sessionCtx?.gexRegime || 'unknown'];

  return (
    <div className="h-8 bg-[#0a0e17] border-b border-slate-800/80 flex items-center px-4 gap-4 text-[11px] font-mono shrink-0 overflow-hidden">
      {/* Data corrente */}
      <span className="text-slate-400">{replayDate || '—'}</span>
      <div className="w-px h-4 bg-slate-800" />

      {sessionCtx ? (
        <>
          {/* IB */}
          <span className="text-slate-500">IB:</span>
          <span className="text-white font-bold">
            {sessionCtx.ibLow.toFixed(2)} — {sessionCtx.ibHigh.toFixed(2)}
          </span>
          <span className="text-slate-600">({sessionCtx.ibRange.toFixed(1)} pts)</span>
          {sessionCtx.ibComplete && (
            <span className="text-emerald-500/70 text-[10px]">[COMPLETE]</span>
          )}
          <div className="w-px h-4 bg-slate-800" />

          {/* Day Type */}
          <span className="text-slate-500">Day:</span>
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${dayTypeColor}`}>
            {dayTypeStr}
          </span>
          <div className="w-px h-4 bg-slate-800" />

          {/* GEX */}
          <span className="text-slate-500">GEX:</span>
          <span className={`font-bold ${gexColor}`}>
            {sessionCtx.gexRegime?.toUpperCase() || '—'}
          </span>
          {sessionCtx.zeroGammaLevel > 0 && (
            <>
              <span className="text-slate-600">·</span>
              <span className="text-slate-500">0γ:</span>
              <span className="text-rose-300">{sessionCtx.zeroGammaLevel.toFixed(2)}</span>
            </>
          )}
          {sessionCtx.callWall > 0 && (
            <>
              <span className="text-slate-600">·</span>
              <span className="text-slate-500">CW:</span>
              <span className="text-emerald-300">{sessionCtx.callWall.toFixed(2)}</span>
            </>
          )}
          {sessionCtx.putWall > 0 && (
            <>
              <span className="text-slate-600">·</span>
              <span className="text-slate-500">PW:</span>
              <span className="text-rose-300">{sessionCtx.putWall.toFixed(2)}</span>
            </>
          )}
        </>
      ) : (
        <span className="text-slate-600 italic">Caricamento sessione...</span>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* WS Status */}
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
            wsStatus === 'connected' ? 'bg-emerald-400' :
            wsStatus === 'connecting' ? 'bg-amber-400' : 'bg-rose-400'
          }`} />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${
            wsStatus === 'connected' ? 'bg-emerald-500' :
            wsStatus === 'connecting' ? 'bg-amber-500' : 'bg-rose-500'
          }`} />
        </span>
        <span className={`font-bold text-[10px] tracking-widest ${
          wsStatus === 'connected' ? 'text-emerald-400' :
          wsStatus === 'connecting' ? 'text-amber-400' : 'text-rose-400'
        }`}>
          {wsStatus === 'connected' ? 'LIVE SYNC' :
           wsStatus === 'connecting' ? 'CONNECTING' : 'DISCONNECTED'}
        </span>
      </div>
    </div>
  );
};
