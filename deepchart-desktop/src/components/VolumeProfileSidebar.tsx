/**
 * VolumeProfileSidebar — Istogramma orizzontale VP sincronizzato al footprint.
 * Mostra: POC (giallo), Value Area (verde), HVN (blu), LVN (arancione),
 *         profile relativo alla sessione corrente.
 */
import React, { useMemo } from 'react';
import { useTradingStore } from '../store/tradingStore';

const TICK_SIZE = 0.25;

interface VPSidebarProps {
  /** Prezzo massimo visibile nel footprint (sincronizzato) */
  maxPrice: number;
  /** Prezzo minimo visibile nel footprint (sincronizzato) */
  minPrice: number;
  /** Altezza per ogni tick in pixel (come nel footprint) */
  cellHeight: number;
  /** Pan Y applicato al footprint (per sincronizzare scroll verticale) */
  panY: number;
  /** Scale del footprint */
  scale: number;
}

export const VolumeProfileSidebar: React.FC<VPSidebarProps> = ({
  maxPrice, minPrice, cellHeight, panY, scale
}) => {
  const { volumeProfile } = useTradingStore();

  const maxVol = useMemo(() => {
    if (!volumeProfile?.profile?.length) return 1;
    return Math.max(...volumeProfile.profile.map(p => p.volume));
  }, [volumeProfile]);

  const pocSet    = useMemo(() => new Set([volumeProfile?.poc].filter(Boolean).map(v => Math.round(v! / TICK_SIZE) * TICK_SIZE)), [volumeProfile]);
  const hvnSet    = useMemo(() => new Set((volumeProfile?.hvnLevels || []).map(v => Math.round(v / TICK_SIZE) * TICK_SIZE)), [volumeProfile]);
  const lvnSet    = useMemo(() => new Set((volumeProfile?.lvnLevels || []).map(v => Math.round(v / TICK_SIZE) * TICK_SIZE)), [volumeProfile]);
  const vaHigh    = volumeProfile?.vaHigh ?? null;
  const vaLow     = volumeProfile?.vaLow  ?? null;

  // Crea una mappa price→volume dal profilo
  const volMap = useMemo(() => {
    const m = new Map<number, number>();
    volumeProfile?.profile.forEach(p => {
      const key = Math.round(p.price / TICK_SIZE) * TICK_SIZE;
      m.set(key, p.volume);
    });
    return m;
  }, [volumeProfile]);

  if (!volumeProfile) {
    return (
      <div className="w-24 bg-[#0b1020] border-l border-slate-800 flex items-center justify-center">
        <span className="text-[9px] text-slate-600 font-mono text-center px-1">
          VP<br/>caricamento...
        </span>
      </div>
    );
  }

  // Genera array di prezzi nella stessa finestra del footprint
  const prices: number[] = [];
  for (let p = maxPrice; p >= minPrice - TICK_SIZE * 0.5; p -= TICK_SIZE) {
    prices.push(Math.round(p / TICK_SIZE) * TICK_SIZE);
  }

  return (
    <div className="w-24 bg-[#0b1020] border-l border-slate-800 flex flex-col shrink-0 overflow-hidden relative">
      {/* Header */}
      <div className="h-6 bg-slate-900/80 border-b border-slate-800 flex items-center justify-center">
        <span className="text-[9px] text-slate-500 font-bold tracking-widest">VOL PROFILE</span>
      </div>

      {/* Bars container — sincronizzato con pan Y */}
      <div
        className="flex-1 relative overflow-hidden"
      >
        <div
          className="absolute w-full flex flex-col"
          style={{
            transform: `translateY(${panY}px) scaleY(${scale})`,
            transformOrigin: 'top center',
            top: 0,
          }}
        >
          {prices.map((price) => {
            const vol = volMap.get(price) ?? 0;
            const widthPct = maxVol > 0 ? (vol / maxVol) * 100 : 0;
            const isPoc = pocSet.has(price);
            const isHvn = hvnSet.has(price);
            const isLvn = lvnSet.has(price);
            const isVA  = vaHigh !== null && vaLow !== null && price <= vaHigh && price >= vaLow;

            let barColor = 'bg-slate-700/70';
            if (isPoc)       barColor = 'bg-yellow-400';
            else if (isHvn)  barColor = 'bg-sky-500/80';
            else if (isLvn)  barColor = 'bg-orange-500/70';
            else if (isVA)   barColor = 'bg-emerald-600/60';

            return (
              <div
                key={price}
                style={{ height: cellHeight }}
                className="flex items-center relative overflow-hidden"
                title={`${price.toFixed(2)} → vol: ${vol.toFixed(0)}`}
              >
                {/* Background bar */}
                {vol > 0 && (
                  <div
                    className={`absolute right-0 h-[70%] rounded-l-sm ${barColor} transition-all`}
                    style={{ width: `${Math.max(2, widthPct)}%` }}
                  />
                )}
                {/* POC label */}
                {isPoc && (
                  <span className="absolute left-0.5 text-[8px] text-yellow-400 font-black z-10 leading-none">
                    POC
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="border-t border-slate-800 p-1 flex flex-col gap-0.5">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-sm bg-yellow-400 shrink-0" />
          <span className="text-[8px] text-slate-500">POC</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-sm bg-emerald-600/60 shrink-0" />
          <span className="text-[8px] text-slate-500">Value Area</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-sm bg-sky-500/80 shrink-0" />
          <span className="text-[8px] text-slate-500">HVN</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-sm bg-orange-500/70 shrink-0" />
          <span className="text-[8px] text-slate-500">LVN</span>
        </div>
        {volumeProfile.poc > 0 && (
          <div className="mt-1 pt-1 border-t border-slate-800/50">
            <div className="text-[8px] text-slate-600">POC</div>
            <div className="text-[9px] text-yellow-400 font-mono font-bold">{volumeProfile.poc.toFixed(2)}</div>
            <div className="text-[8px] text-slate-600 mt-0.5">VAH</div>
            <div className="text-[9px] text-emerald-400 font-mono">{volumeProfile.vaHigh.toFixed(2)}</div>
            <div className="text-[8px] text-slate-600">VAL</div>
            <div className="text-[9px] text-emerald-400 font-mono">{volumeProfile.vaLow.toFixed(2)}</div>
          </div>
        )}
      </div>
    </div>
  );
};
