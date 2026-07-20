/**
 * ReplayControls — Barra di controllo del replay storico.
 * Play, Pause, Step, Speed, Date picker, Seek slider.
 */
import React, { useCallback } from 'react';
import { useTradingStore } from '../store/tradingStore';

const SPEEDS = [
  { label: '0.5×', value: 30 },
  { label: '1×',   value: 60 },
  { label: '5×',   value: 300 },
  { label: '30×',  value: 1800 },
  { label: 'MAX',  value: 99999 },
];

export const ReplayControls: React.FC = () => {
  const {
    replayMode,
    replayDate,
    availableDates,
    replayBarIdx,
    replayTotalBars,
    replaySpeed,
    sendWsMessage,
    setAvailableDates,
  } = useTradingStore();

  const send = useCallback((msg: object) => {
    sendWsMessage?.(msg);
  }, [sendWsMessage]);

  const isPlaying = replayMode === 'replay';
  const progress  = replayTotalBars > 0 ? (replayBarIdx / replayTotalBars) * 100 : 0;

  const handlePlay  = () => send({ action: 'replay_play'  });
  const handlePause = () => send({ action: 'replay_pause' });
  const handleStepF = () => send({ action: 'replay_step_forward' });
  const handleStepB = () => send({ action: 'replay_step_back'    });
  const handleSpeed = (v: number) => send({ action: 'set_speed', multiplier: v });
  const handleSeek  = (e: React.ChangeEvent<HTMLInputElement>) =>
    send({ action: 'seek', bar_idx: parseInt(e.target.value) });
  const handleDate  = (e: React.ChangeEvent<HTMLSelectElement>) =>
    send({ action: 'set_replay_date', date: e.target.value });

  // Formatta bar_idx come orario ET approssimativo (09:30 + N minuti)
  const barToTime = (idx: number) => {
    const totalMin = 9 * 60 + 30 + idx;
    const h = Math.floor(totalMin / 60) % 24;
    const m = totalMin % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')} ET`;
  };

  return (
    <div className="h-14 bg-[#0d131f] border-t border-slate-800 flex items-center px-4 gap-3 shrink-0 select-none">
      {/* Date selector */}
      <select
        value={replayDate}
        onChange={handleDate}
        className="bg-slate-800 text-slate-300 text-xs font-mono border border-slate-700 rounded px-2 py-1 h-7 focus:outline-none focus:border-blue-500 hover:border-slate-500 transition-colors"
        title="Seleziona data sessione"
      >
        {availableDates.map(d => (
          <option key={d} value={d}>{d}</option>
        ))}
      </select>

      {/* Divider */}
      <div className="w-px h-6 bg-slate-700" />

      {/* Transport controls */}
      <div className="flex items-center gap-1">
        {/* Step back */}
        <button
          onClick={handleStepB}
          className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          title="Step indietro (1 barra)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/>
          </svg>
        </button>

        {/* Play / Pause */}
        <button
          onClick={isPlaying ? handlePause : handlePlay}
          className={`p-1.5 rounded transition-colors ${
            isPlaying
              ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
              : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
          }`}
          title={isPlaying ? 'Pausa' : 'Play'}
        >
          {isPlaying ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z"/>
            </svg>
          )}
        </button>

        {/* Step forward */}
        <button
          onClick={handleStepF}
          className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          title="Step avanti (1 barra)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 18l8.5-6L6 6v12zm2.5-6l5.5 3.98V8.02L8.5 12zM16 6h2v12h-2z"/>
          </svg>
        </button>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-slate-700" />

      {/* Speed buttons */}
      <div className="flex items-center gap-1">
        {SPEEDS.map(s => (
          <button
            key={s.value}
            onClick={() => handleSpeed(s.value)}
            className={`px-2 py-0.5 text-[10px] font-bold rounded transition-colors ${
              Math.abs(replaySpeed - s.value) < 1
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white border border-slate-700'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-slate-700" />

      {/* Seek slider */}
      <div className="flex-1 flex items-center gap-2 min-w-0">
        <input
          type="range"
          min={0}
          max={replayTotalBars || 1}
          value={replayBarIdx}
          onChange={handleSeek}
          className="flex-1 h-1.5 rounded-full accent-blue-500 cursor-pointer"
          style={{ minWidth: 60 }}
        />
        <span className="text-[10px] font-mono text-slate-500 whitespace-nowrap shrink-0">
          {barToTime(replayBarIdx)} · {replayBarIdx}/{replayTotalBars}
        </span>
      </div>

      {/* Modo */}
      <div className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${
        replayMode === 'replay'
          ? 'bg-emerald-900/60 text-emerald-400 border border-emerald-700/50'
          : 'bg-slate-800 text-slate-500 border border-slate-700'
      }`}>
        {replayMode === 'replay' ? '▶ PLAY' : replayMode === 'paused' ? '⏸ PAUSED' : 'LIVE'}
      </div>
    </div>
  );
};
