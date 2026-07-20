import React, { useState, useEffect } from 'react';
import { Activity, Settings, Database, Crosshair, BarChart2 } from 'lucide-react';
import { FootprintChart, type FootprintCandle } from './components/FootprintChart';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Mock generation for demonstration of Footprint
function generateMockData(): FootprintCandle[] {
  const candles: FootprintCandle[] = [];
  let currentPrice = 25600;
  
  for (let i = 0; i < 20; i++) {
    const isUp = Math.random() > 0.5;
    const levels = [];
    const numLevels = Math.floor(Math.random() * 10) + 15; // 15-25 levels per candle
    
    let totalVol = 0;
    let totalDelta = 0;
    
    let levelPrice = currentPrice - (numLevels * 0.25) / 2;
    for (let j = 0; j < numLevels; j++) {
      const bid = Math.floor(Math.random() * 200);
      const ask = Math.floor(Math.random() * 200);
      const delta = ask - bid;
      
      let imb: 'none' | 'bid' | 'ask' = 'none';
      if (ask > bid * 3 && ask > 50) imb = 'ask';
      if (bid > ask * 3 && bid > 50) imb = 'bid';
      
      levels.push({
        price: levelPrice,
        bidVol: bid,
        askVol: ask,
        delta: delta,
        isImbalance: imb
      });
      
      totalVol += (bid + ask);
      totalDelta += delta;
      levelPrice += 0.25;
    }
    
    // Sort levels descending by price (highest at top)
    levels.sort((a, b) => b.price - a.price);
    
    candles.push({
      timestamp: new Date(Date.now() - (20 - i) * 60000).toISOString(),
      open: currentPrice,
      close: isUp ? currentPrice + 5 : currentPrice - 5,
      high: currentPrice + 10,
      low: currentPrice - 10,
      delta: totalDelta,
      volume: totalVol,
      levels: levels
    });
    
    currentPrice = isUp ? currentPrice + 5 : currentPrice - 5;
  }
  return candles;
}

export default function App() {
  const [data, setData] = useState<FootprintCandle[]>(generateMockData()); // Pre-fill 20 storiche
  const [isConnected, setIsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState('chart');

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8765');
    
    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'candle_update') {
        const raw = msg.data;
        const tickSize = 0.25;
        const high = raw.bar_high;
        const low = raw.bar_low;
        const close = raw.bar_close;
        const vol = raw.bar_volume;
        const delta = raw.bar_delta;
        
        const numTicks = Math.max(1, Math.round((high - low) / tickSize)) + 1;
        const volPerTick = Math.floor(vol / numTicks);
        const deltaPerTick = Math.floor(delta / numTicks);
        
        const levels = [];
        for (let p = high; p >= low; p -= tickSize) {
          const isPoc = Math.abs(p - close) <= 0.5;
          const bVol = Math.max(0, Math.floor(volPerTick / 2) - deltaPerTick + (isPoc ? volPerTick : 0));
          const aVol = Math.max(0, Math.floor(volPerTick / 2) + deltaPerTick + (isPoc ? volPerTick : 0));
          const lvlDelta = aVol - bVol;
          
          levels.push({
            price: p,
            bidVol: bVol,
            askVol: aVol,
            delta: lvlDelta,
            isImbalance: lvlDelta > 30 ? 'ask' : lvlDelta < -30 ? 'bid' : 'none'
          });
        }

        const newCandle: FootprintCandle = {
          timestamp: raw.bar_time_utc || new Date().toISOString(),
          open: raw.bar_open,
          high: raw.bar_high,
          low: raw.bar_low,
          close: raw.bar_close,
          delta: raw.bar_delta,
          volume: raw.bar_volume,
          levels: levels
        };
        
        setData(prev => {
          if (prev.length > 0 && prev[prev.length - 1].timestamp === newCandle.timestamp) {
            const updated = [...prev];
            updated[updated.length - 1] = newCandle;
            return updated;
          }
          return [...prev.slice(-99), newCandle];
        });
      }
    };
    
    return () => ws.close();
  }, []);

  return (
    <div className="flex h-screen bg-trading-bg text-trading-text font-sans overflow-hidden">
      {/* Left Sidebar */}
      <aside className="w-16 bg-trading-panel border-r border-trading-border flex flex-col items-center py-4 space-y-6 z-20">
        <div 
          onClick={() => setActiveTab('chart')}
          className={cn("p-2 rounded-lg cursor-pointer transition-all", activeTab === 'chart' ? "bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]" : "text-trading-muted hover:text-trading-text hover:bg-slate-800")}
        >
          <Activity size={24} />
        </div>
        <div 
          onClick={() => setActiveTab('stats')}
          className={cn("p-2 rounded-lg cursor-pointer transition-all", activeTab === 'stats' ? "bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]" : "text-trading-muted hover:text-trading-text hover:bg-slate-800")}
        >
          <BarChart2 size={24} />
        </div>
        <div 
          onClick={() => setActiveTab('dom')}
          className={cn("p-2 rounded-lg cursor-pointer transition-all", activeTab === 'dom' ? "bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]" : "text-trading-muted hover:text-trading-text hover:bg-slate-800")}
        >
          <Crosshair size={24} />
        </div>
        <div 
          onClick={() => setActiveTab('data')}
          className={cn("p-2 rounded-lg cursor-pointer transition-all", activeTab === 'data' ? "bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]" : "text-trading-muted hover:text-trading-text hover:bg-slate-800")}
        >
          <Database size={24} />
        </div>
        <div 
          onClick={() => setActiveTab('settings')}
          className={cn("mt-auto p-2 rounded-lg cursor-pointer transition-all", activeTab === 'settings' ? "bg-blue-500/20 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)]" : "text-trading-muted hover:text-trading-text hover:bg-slate-800")}
        >
          <Settings size={24} />
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-14 bg-trading-panel border-b border-trading-border flex items-center px-6 justify-between shrink-0 z-10 shadow-md">
          <div className="flex items-center space-x-4">
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400 bg-clip-text text-transparent drop-shadow-sm">
              DeepPrint Pro
            </h1>
            <div className="h-4 w-px bg-trading-border mx-2" />
            <div className="text-sm font-mono flex items-center space-x-2 bg-slate-900/50 px-3 py-1 rounded-full border border-slate-700/50">
              <span className="text-trading-muted font-semibold">MNQ</span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-300">1 Min</span>
            </div>
          </div>
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2 text-xs font-mono bg-slate-900/50 px-3 py-1.5 rounded-full border border-slate-700/50">
               <span className="relative flex h-2.5 w-2.5">
                  <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", isConnected ? "bg-emerald-400" : "bg-rose-400")}></span>
                  <span className={cn("relative inline-flex rounded-full h-2.5 w-2.5", isConnected ? "bg-emerald-500" : "bg-rose-500")}></span>
                </span>
               <span className={isConnected ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                 {isConnected ? 'LIVE SYNC' : 'DISCONNECTED'}
               </span>
             </div>
          </div>
        </header>

        {/* Content Workspace */}
        <div className="flex-1 flex flex-row overflow-hidden">
           {/* Chart Area */}
           <div className="flex-1 relative border-r border-trading-border/50">
             {activeTab === 'chart' ? (
                <FootprintChart data={data} />
             ) : (
                <div className="flex h-full items-center justify-center text-slate-500 font-mono text-xl">
                  {activeTab.toUpperCase()} PANE - Coming Soon
                </div>
             )}
           </div>

           {/* DOM / Order Book Right Panel */}
           <div className="w-64 bg-[#0d131f] flex flex-col shrink-0 border-l border-slate-800 shadow-[-5px_0_15px_rgba(0,0,0,0.2)] z-10">
              <div className="h-8 bg-slate-800/80 border-b border-slate-700 flex items-center justify-center font-bold text-[11px] text-slate-300 tracking-widest">
                ORDER BOOK (DOM)
              </div>
              <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                {/* DOM Mockup */}
                <div className="flex justify-between text-[10px] text-slate-500 border-b border-slate-800 pb-1 mb-1 px-1">
                  <span>BID SIZ</span>
                  <span>PRICE</span>
                  <span>ASK SIZ</span>
                </div>
                {Array.from({length: 30}).map((_, i) => {
                  const price = (21500 - (i * 0.25)).toFixed(2);
                  const isAsk = i < 15;
                  const size = Math.floor(Math.random() * 50) + 1;
                  return (
                    <div key={i} className="flex justify-between items-center text-[11px] font-mono py-0.5 px-1 hover:bg-slate-800/50 cursor-pointer group">
                      <span className="w-1/3 text-left text-emerald-400/80 group-hover:text-emerald-300">{!isAsk ? size : ''}</span>
                      <span className={cn("w-1/3 text-center font-bold", isAsk ? "text-rose-200" : "text-emerald-200")}>{price}</span>
                      <span className="w-1/3 text-right text-rose-400/80 group-hover:text-rose-300">{isAsk ? size : ''}</span>
                    </div>
                  );
                })}
              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
