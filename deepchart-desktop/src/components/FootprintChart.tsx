import React, { useRef, useState, useEffect, useMemo } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface FootprintLevel {
  price: number;
  bidVol: number;
  askVol: number;
  delta: number;
  isImbalance: 'bid' | 'ask' | 'none';
}

export interface FootprintCandle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  delta: number;
  volume: number;
  levels: FootprintLevel[];
}

export const FootprintChart: React.FC<{ data: FootprintCandle[] }> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Pure Vectorial Pan & Zoom State
  const [scale, setScale] = useState(0.8);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  const TICK_SIZE = 0.25;
  const CELL_HEIGHT = 22; 

  const { prices, globalMaxVolume, maxPrice, minPrice } = useMemo(() => {
    if (data.length === 0) return { prices: [], globalMaxVolume: 1, maxPrice: 0, minPrice: 0 };
    
    let maxP = -Infinity;
    let minP = Infinity;
    let maxV = 1;

    data.forEach(c => {
      if (c.high > maxP) maxP = c.high;
      if (c.low < minP) minP = c.low;
      
      const cMaxV = c.levels.reduce((acc, lvl) => Math.max(acc, lvl.bidVol + lvl.askVol), 0);
      if (cMaxV > maxV) maxV = cMaxV;
    });

    maxP += 10 * TICK_SIZE;
    minP -= 10 * TICK_SIZE;

    const pArray = [];
    for (let p = maxP; p >= minP; p -= TICK_SIZE) {
      pArray.push(p);
    }

    return { prices: pArray, globalMaxVolume: maxV, maxPrice: maxP, minPrice: minP };
  }, [data]);

  const handleWheel = (e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey || true) { 
      e.preventDefault();
      const zoomSensitivity = scale < 0.5 ? 0.02 : 0.05;
      const direction = e.deltaY > 0 ? -1 : 1;
      const newScale = Math.min(Math.max(0.05, scale + direction * zoomSensitivity), 3);
      
      // Keep center of screen consistent during zoom (simplified zoom anchor)
      setScale(newScale);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    setPanStart({ x: pan.x, y: pan.y });
  };

  const handleMouseLeave = () => setIsDragging(false);
  const handleMouseUp = () => setIsDragging(false);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    e.preventDefault();
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    
    // Update translation vector
    setPan({ 
      x: panStart.x + dx, 
      y: panStart.y + dy 
    });
  };

  // Center view on init (instead of scrolling, we set initial translation)
  useEffect(() => {
    if (prices.length > 0 && data.length > 0 && pan.x === 0 && pan.y === 0) {
      const chartWidth = data.length * 220; // 220px per candle
      const viewWidth = containerRef.current?.clientWidth || 800;
      const viewHeight = containerRef.current?.clientHeight || 800;
      
      // Calculate where the latest candle is rendered
      const latestCandle = data[data.length - 1];
      const candleY = 60 + ((maxPrice - latestCandle.high) / TICK_SIZE) * CELL_HEIGHT;
      
      // Start aligned to the right, and vertically centered on the latest candle
      setPan({ 
        x: -Math.max(0, chartWidth * scale - viewWidth + 80), 
        y: -(candleY * scale) + (viewHeight / 2)
      }); 
    }
    // Disable exhaustive-deps to prevent array length mismatch during HMR
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prices.length]);

  const showText = scale > 0.35;

  return (
    <div 
      data-testid="chart-container"
      ref={containerRef}
      className={cn(
        "w-full h-full overflow-hidden bg-[#0a0e17] select-none relative flex",
        isDragging ? "cursor-grabbing" : "cursor-grab"
      )}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseLeave={handleMouseLeave}
      onMouseUp={handleMouseUp}
      onMouseMove={handleMouseMove}
    >
      <div 
        className="flex flex-row absolute top-0 left-0 will-change-transform"
        style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${scale})`, transformOrigin: 'top left' }}
      >
        {/* Main Grid: Candles */}
        {data.map((candle, i) => {
          const isBullish = candle.close >= candle.open;
          const colorClass = isBullish ? 'text-emerald-400' : 'text-rose-400';
          const bgClass = isBullish ? 'bg-emerald-500' : 'bg-rose-500';
          
          return (
            <div key={i} className="flex flex-col min-w-[220px] border-r border-slate-800/80 pr-1 group/candle hover:bg-white/[0.02] transition-colors relative">
              
              {/* Header info (Floating on top of grid) */}
              <div className="flex flex-col items-center justify-center py-2 mb-2 bg-slate-900/80 border-b border-slate-800 shadow-md absolute top-0 w-full z-20 backdrop-blur-sm" style={{ opacity: showText ? 1 : 0.3, transform: `translateY(${-pan.y / scale}px)` }}>
                <span className="text-[12px] text-slate-400 font-medium mb-1">
                  {new Date(candle.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                </span>
                <div className="grid grid-cols-2 w-full px-2 gap-1 text-[12px] font-bold">
                  <div className="flex flex-col items-center bg-slate-800/80 rounded px-1 py-1">
                    <span className="text-slate-500 text-[10px] uppercase tracking-wider">Vol</span>
                    <span className="text-slate-200">{candle.volume}</span>
                  </div>
                  <div className="flex flex-col items-center bg-slate-800/80 rounded px-1 py-1">
                    <span className="text-slate-500 text-[10px] uppercase tracking-wider">Delta</span>
                    <span className={cn(colorClass)}>{candle.delta > 0 ? '+' : ''}{candle.delta}</span>
                  </div>
                </div>
              </div>

              {/* Grid Content with top padding so first cells don't hide under header */}
              <div className="flex-grow relative w-full pt-[60px]">
                
                {/* Visual Candlestick Overlay */}
                <div className="absolute left-2 w-3 pointer-events-none z-10 opacity-60 group-hover/candle:opacity-100 transition-opacity">
                  {/* High/Low Wick mapping */}
                  <div className={cn("absolute left-1/2 -translate-x-1/2 w-[2px]", bgClass)}
                       style={{ 
                         top: `${60 + ((maxPrice - candle.high) / TICK_SIZE) * CELL_HEIGHT}px`,
                         height: `${((candle.high - candle.low) / TICK_SIZE) * CELL_HEIGHT}px`
                       }} 
                  />
                  {/* Open/Close Body mapping */}
                  <div className={cn("absolute w-full rounded-[2px] shadow-[0_0_8px_rgba(0,0,0,0.5)]", bgClass)}
                       style={{ 
                         top: `${60 + ((maxPrice - Math.max(candle.open, candle.close)) / TICK_SIZE) * CELL_HEIGHT}px`,
                         height: `${Math.max(1, (Math.abs(candle.open - candle.close) / TICK_SIZE) * CELL_HEIGHT)}px`
                       }} 
                  />
                </div>

                {/* Sparse Matrix - Real Bid x Ask Footprint */}
                <div 
                  className="absolute w-full flex flex-col" 
                  style={{ top: `${60 + ((maxPrice - candle.levels[0]?.price) / TICK_SIZE) * CELL_HEIGHT}px` }}
                >
                  {candle.levels.map((lvl) => {
                    const totalVol = lvl.bidVol + lvl.askVol;
                    const widthPct = Math.max(2, (totalVol / globalMaxVolume) * 100);
                    
                    const askClass = lvl.isImbalance === 'ask' 
                      ? 'text-emerald-300 font-black bg-emerald-900/60 drop-shadow-[0_0_4px_rgba(52,211,153,0.9)]' 
                      : 'text-slate-300 font-medium';
                    const bidClass = lvl.isImbalance === 'bid' 
                      ? 'text-rose-300 font-black bg-rose-900/60 drop-shadow-[0_0_4px_rgba(251,113,133,0.9)]' 
                      : 'text-slate-300 font-medium';

                    const profileColor = lvl.delta >= 0 
                      ? 'bg-gradient-to-l from-emerald-500/30 to-transparent' 
                      : 'bg-gradient-to-l from-rose-500/30 to-transparent';

                    return (
                      <div key={lvl.price} style={{ height: CELL_HEIGHT }} className="flex flex-row items-center relative hover:bg-slate-700/80 cursor-default rounded-[2px] overflow-hidden pl-6 pr-1">
                        {/* Background Volume Profile */}
                        <div 
                          className={cn("absolute inset-y-0 right-0 z-0", profileColor)}
                          style={{ width: `${widthPct}%` }}
                        />
                        
                        {/* Inner Data Container (Bid x Ask) */}
                        <div className={cn("z-10 flex w-full text-[12px] font-mono justify-between items-center h-full px-1", showText ? "opacity-100" : "opacity-0")}>
                          <div className="flex flex-1 justify-between items-center">
                            <span className={cn("flex-1 text-right pr-2", bidClass)}>
                              {lvl.bidVol || '-'}
                            </span>
                            <span className="text-slate-600 mx-1 text-[10px]">x</span>
                            <span className={cn("flex-1 text-left pl-2", askClass)}>
                              {lvl.askVol || '-'}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>
          );
        })}
      </div>
      
      {/* Absolute Y-Axis (Prices) on the Right */}
      <div className="absolute right-0 top-0 bottom-0 w-[60px] bg-[#0d131f]/90 border-l border-slate-700 z-30 shadow-[-10px_0_20px_rgba(0,0,0,0.5)] backdrop-blur-md overflow-hidden pointer-events-none">
        
        {/* Fixed header for Y-Axis */}
        <div className="h-[60px] bg-slate-900/90 border-b border-slate-800 flex flex-col items-center justify-end pb-2 absolute top-0 w-full z-40">
           <span className="text-[10px] text-slate-500 font-bold tracking-widest px-2">PRICE</span>
        </div>

        {/* Scaled and translated prices container */}
        <div className="absolute top-0 right-0 w-[60px] flex flex-col will-change-transform"
             style={{ transform: `translateY(${pan.y}px) scale(${scale})`, transformOrigin: 'top right', paddingTop: '60px' }}>
          {prices.map(p => (
            <div key={p} style={{ height: CELL_HEIGHT }} className="flex items-center justify-end pr-2 text-[11px] font-mono text-slate-400 font-bold border-b border-slate-800/30">
              {p.toFixed(2)}
            </div>
          ))}
        </div>
      </div>

      {/* Zoom controls UI overlay */}
      <div className="fixed bottom-6 right-20 flex flex-col space-y-2 bg-slate-800/90 p-1 rounded-lg backdrop-blur-md border border-slate-700 shadow-2xl z-50">
        <button onClick={() => setScale(s => Math.min(s + 0.1, 3))} className="p-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
        </button>
        <button onClick={() => setScale(0.8)} className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-md text-[10px] font-bold">
          {Math.round(scale * 100)}%
        </button>
        <button onClick={() => setScale(s => Math.max(s - 0.1, 0.05))} className="p-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
        </button>
      </div>
    </div>
  );
}
