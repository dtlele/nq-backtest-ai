/**
 * RoadmapPanel — Daily Roadmap dal CleanBridge.
 * Card collassabile con contextAnalysis e scenari bull/bear.
 * Stile coerente con AlertPanel (TradingStore + Tailwind).
 */
import React, { useState } from 'react';
import { useTradingStore } from '../store/tradingStore';
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

export const RoadmapPanel: React.FC = () => {
  const { dailyRoadmap } = useTradingStore();
  const [collapsed, setCollapsed] = useState(false);

  if (!dailyRoadmap) return null;

  const { contextAnalysis, bullish, bearish } = dailyRoadmap;

  return (
    <div className="w-full bg-[#0b1020] border border-slate-800 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setCollapsed(c => !c)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-900/60 border-b border-slate-800 hover:bg-slate-800/70 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-white tracking-wide">ROADMAP GIORNALIERA</span>
          <span className="text-[10px] font-mono text-slate-500">{dailyRoadmap.date}</span>
        </div>
        {collapsed ? <ChevronRight size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
      </button>

      {!collapsed && (
        <div className="px-3 py-2 space-y-2 max-h-96 overflow-y-auto">
          {/* Context Analysis */}
          <div className="text-[10px] text-slate-300 font-mono leading-relaxed bg-slate-900/40 rounded p-2 border border-slate-800/50">
            {contextAnalysis || 'Nessuna analisi del contesto disponibile.'}
          </div>

          {/* Bullish Scenario */}
          <div className="bg-emerald-950/30 border border-emerald-800/40 rounded p-2">
            <div className="flex items-center gap-1.5 mb-1">
              <TrendingUp size={12} className="text-emerald-400" />
              <span className="text-[10px] font-bold text-emerald-300 uppercase tracking-wider">Bullish</span>
            </div>
            {bullish?.trigger_description && (
              <div className="text-[10px] text-slate-300 font-mono leading-relaxed">
                <span className="text-slate-500">Trigger: </span>{bullish.trigger_description}
              </div>
            )}
            {bullish?.target_level && (
              <div className="text-[10px] text-emerald-300 font-mono mt-1">
                Target: <span className="font-bold">{bullish.target_level.toFixed(2)}</span>
              </div>
            )}
            {!bullish?.trigger_description && !bullish?.target_level && (
              <div className="text-[10px] text-slate-600 italic">Nessuno scenario bullish definito</div>
            )}
          </div>

          {/* Bearish Scenario */}
          <div className="bg-rose-950/30 border border-rose-800/40 rounded p-2">
            <div className="flex items-center gap-1.5 mb-1">
              <TrendingDown size={12} className="text-rose-400" />
              <span className="text-[10px] font-bold text-rose-300 uppercase tracking-wider">Bearish</span>
            </div>
            {bearish?.trigger_description && (
              <div className="text-[10px] text-slate-300 font-mono leading-relaxed">
                <span className="text-slate-500">Trigger: </span>{bearish.trigger_description}
              </div>
            )}
            {bearish?.target_level && (
              <div className="text-[10px] text-rose-300 font-mono mt-1">
                Target: <span className="font-bold">{bearish.target_level.toFixed(2)}</span>
              </div>
            )}
            {!bearish?.trigger_description && !bearish?.target_level && (
              <div className="text-[10px] text-slate-600 italic">Nessuno scenario bearish definito</div>
            )}
          </div>

          {/* Key Levels */}
          {dailyRoadmap.keyLevels && dailyRoadmap.keyLevels.length > 0 && (
            <div className="bg-slate-900/40 border border-slate-800/50 rounded p-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Key Levels</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {dailyRoadmap.keyLevels.map((level, i) => (
                  <span key={i} className="text-[10px] font-mono text-sky-300 bg-sky-950/30 px-1.5 py-0.5 rounded border border-sky-800/30">
                    {typeof level === 'number' ? level.toFixed(2) : level}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const RoadmapPanelInline: React.FC = () => {
  const { dailyRoadmap } = useTradingStore();

  return (
    <div className="w-[220px] bg-[#0b1020] border-l border-slate-800 flex flex-col shrink-0">
      <div className="h-6 bg-slate-900/80 border-b border-slate-700 flex items-center justify-center shrink-0">
        <span className="text-[9px] text-slate-400 font-bold tracking-widest">ROADMAP</span>
      </div>

      {!dailyRoadmap ? (
        <div className="flex-1 flex items-center justify-center p-3">
          <div className="text-center">
            <AlertCircle size={16} className="text-slate-600 mx-auto mb-1" />
            <div className="text-[10px] text-slate-600 italic">Nessuna roadmap</div>
            <div className="text-[9px] text-slate-700">per questa data</div>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-2 space-y-2 text-[10px]">
          <div className="text-[9px] text-slate-500 font-mono leading-relaxed bg-slate-900/40 rounded p-1.5">
            {dailyRoadmap.contextAnalysis?.slice(0, 120) || ''}
            {(dailyRoadmap.contextAnalysis?.length || 0) > 120 ? '...' : ''}
          </div>

          {dailyRoadmap.bullish?.trigger_description && (
            <div className="bg-emerald-950/30 border border-emerald-800/40 rounded p-1.5">
              <div className="flex items-center gap-1 mb-0.5">
                <TrendingUp size={10} className="text-emerald-400" />
                <span className="text-[9px] font-bold text-emerald-300">Bull</span>
              </div>
              <div className="text-[9px] text-slate-400 font-mono leading-tight">
                {dailyRoadmap.bullish.trigger_description?.slice(0, 80)}
              </div>
              {dailyRoadmap.bullish.target_level && (
                <div className="text-[9px] text-emerald-300 font-mono mt-0.5">
                  Tgt: {dailyRoadmap.bullish.target_level.toFixed(2)}
                </div>
              )}
            </div>
          )}

          {dailyRoadmap.bearish?.trigger_description && (
            <div className="bg-rose-950/30 border border-rose-800/40 rounded p-1.5">
              <div className="flex items-center gap-1 mb-0.5">
                <TrendingDown size={10} className="text-rose-400" />
                <span className="text-[9px] font-bold text-rose-300">Bear</span>
              </div>
              <div className="text-[9px] text-slate-400 font-mono leading-tight">
                {dailyRoadmap.bearish.trigger_description?.slice(0, 80)}
              </div>
              {dailyRoadmap.bearish.target_level && (
                <div className="text-[9px] text-rose-300 font-mono mt-0.5">
                  Tgt: {dailyRoadmap.bearish.target_level.toFixed(2)}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
