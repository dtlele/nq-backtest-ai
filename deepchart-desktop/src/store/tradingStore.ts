/**
 * Zustand Global Store — DeepPrint Pro
 * Stato centralizzato per tutta la piattaforma volumetrica.
 */
import { create } from 'zustand';

// ─── Tipi dati ───────────────────────────────────────────────────────────────

export interface FootprintLevel {
  price: number;
  bidVol: number;
  askVol: number;
  delta: number;
  imbalance: 'bid' | 'ask' | 'none';
  isPoc: boolean;
  isHvn: boolean;
  isLvn: boolean;
  isVah: boolean;
  isVal: boolean;
  isIbHigh: boolean;
  isIbLow: boolean;
}

export interface BigTrade {
  price: number;
  size: number;
  side: 'A' | 'B';
  timestamp: string;
}

export interface AgentSignal {
  direction: 'long' | 'short' | 'none';
  confidence: number;
  entry: number;
  stop: number;
  target: number;
  setupType: string;
  reasoning: string;
  decision: 'trade' | 'no_trade';
}

export interface FootprintCandle {
  barTimeUtc: string;
  barOpen: number;
  barHigh: number;
  barLow: number;
  barClose: number;
  barVolume: number;
  barBuyVolume: number;
  barSellVolume: number;
  barDelta: number;
  barDeltaPct: number;
  barCvd: number;
  barVwap: number;
  levels: FootprintLevel[];
  bigTrades: BigTrade[];
  agentSignal?: AgentSignal;
}

export interface VolumeProfileLevel {
  price: number;
  volume: number;
  pct: number;
}

export interface VolumeProfileData {
  poc: number;
  vaHigh: number;
  vaLow: number;
  hvnLevels: number[];
  lvnLevels: number[];
  profile: VolumeProfileLevel[];
}

export interface SessionContextData {
  ibHigh: number;
  ibLow: number;
  ibRange: number;
  ibComplete: boolean;
  dayType: 'trend_up' | 'trend_down' | 'balance' | 'transition_state' | 'unknown';
  gexRegime: 'positive' | 'negative' | 'unknown';
  zeroGammaLevel: number;
  callWall: number;
  putWall: number;
}

export interface DOMEntry {
  price: number;
  size: number;
}

export interface DOMData {
  bids: DOMEntry[];
  asks: DOMEntry[];
  lastTradePrice?: number;
  lastTradeSize?: number;
  lastTradeSide?: 'A' | 'B';
}

export interface Alert {
  id: string;
  type: 'trade' | 'no_trade' | 'system';
  direction?: 'long' | 'short';
  confidence?: number;
  setupType?: string;
  message: string;
  reasoning?: string;
  timestamp: number;
}

// ─── Store ───────────────────────────────────────────────────────────────────

interface TradingStore {
  // WebSocket
  wsStatus: 'connected' | 'disconnected' | 'connecting';
  setWsStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
  sendWsMessage: ((msg: object) => void) | null;
  setSendWsMessage: (fn: (msg: object) => void) => void;

  // Dati candele
  candles: FootprintCandle[];
  addCandle: (candle: FootprintCandle) => void;
  setBatchCandles: (candles: FootprintCandle[]) => void;
  clearCandles: () => void;

  // Volume Profile
  volumeProfile: VolumeProfileData | null;
  setVolumeProfile: (vp: VolumeProfileData) => void;

  // Session Context
  sessionCtx: SessionContextData | null;
  setSessionCtx: (ctx: SessionContextData) => void;

  // DOM
  domData: DOMData | null;
  setDomData: (dom: DOMData) => void;

  // Replay
  replayMode: 'live' | 'replay' | 'paused';
  replayDate: string;
  availableDates: string[];
  replayBarIdx: number;
  replayTotalBars: number;
  replaySpeed: number;
  setReplayStatus: (mode: string, date: string, barIdx: number, totalBars: number, speed: number) => void;
  setAvailableDates: (dates: string[]) => void;
  setReplayDate: (date: string) => void;

  // UI State
  activeTimeframe: '1m' | '5m';
  setActiveTimeframe: (tf: '1m' | '5m') => void;
  showVP: boolean;
  setShowVP: (v: boolean) => void;
  showGEX: boolean;
  setShowGEX: (v: boolean) => void;
  showAgentSignals: boolean;
  setShowAgentSignals: (v: boolean) => void;
  showIBBox: boolean;
  setShowIBBox: (v: boolean) => void;
  showCVD: boolean;
  setShowCVD: (v: boolean) => void;
  showBigTrades: boolean;
  setShowBigTrades: (v: boolean) => void;
  selectedCandle: FootprintCandle | null;
  setSelectedCandle: (c: FootprintCandle | null) => void;

  // Alerts
  alerts: Alert[];
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp'>) => void;
  dismissAlert: (id: string) => void;
  clearAlerts: () => void;
}

let alertIdCounter = 0;

export const useTradingStore = create<TradingStore>((set, get) => ({
  // WebSocket
  wsStatus: 'disconnected',
  setWsStatus: (status) => set({ wsStatus: status }),
  sendWsMessage: null,
  setSendWsMessage: (fn) => set({ sendWsMessage: fn }),

  // Candele
  candles: [],
  addCandle: (candle) => set((state) => {
    const existing = state.candles;
    const last = existing[existing.length - 1];
    // Se stessa timestamp, aggiorna l'ultima (barra corrente)
    if (last && last.barTimeUtc === candle.barTimeUtc) {
      return { candles: [...existing.slice(0, -1), candle] };
    }
    // Altrimenti aggiungi, mantieni max 300 candele
    const updated = [...existing, candle];
    return { candles: updated.length > 300 ? updated.slice(-300) : updated };
  }),
  setBatchCandles: (candles) => set({ candles }),
  clearCandles: () => set({ candles: [] }),

  // Volume Profile
  volumeProfile: null,
  setVolumeProfile: (vp) => set({ volumeProfile: vp }),

  // Session Context
  sessionCtx: null,
  setSessionCtx: (ctx) => set({ sessionCtx: ctx }),

  // DOM
  domData: null,
  setDomData: (dom) => set({ domData: dom }),

  // Replay
  replayMode: 'paused',
  replayDate: '',
  availableDates: [],
  replayBarIdx: 0,
  replayTotalBars: 0,
  replaySpeed: 60,
  setReplayStatus: (mode, date, barIdx, totalBars, speed) => set({
    replayMode: mode as any,
    replayDate: date,
    replayBarIdx: barIdx,
    replayTotalBars: totalBars,
    replaySpeed: speed,
  }),
  setAvailableDates: (dates) => set({ availableDates: dates }),
  setReplayDate: (date) => {
    const { sendWsMessage } = get();
    set({ replayDate: date });
    sendWsMessage?.({ action: 'set_replay_date', date });
  },

  // UI State
  activeTimeframe: '1m',
  setActiveTimeframe: (tf) => set({ activeTimeframe: tf }),
  showVP: true,
  setShowVP: (v) => set({ showVP: v }),
  showGEX: true,
  setShowGEX: (v) => set({ showGEX: v }),
  showAgentSignals: true,
  setShowAgentSignals: (v) => set({ showAgentSignals: v }),
  showIBBox: true,
  setShowIBBox: (v) => set({ showIBBox: v }),
  showCVD: true,
  setShowCVD: (v) => set({ showCVD: v }),
  showBigTrades: true,
  setShowBigTrades: (v) => set({ showBigTrades: v }),
  selectedCandle: null,
  setSelectedCandle: (c) => set({ selectedCandle: c }),

  // Alerts
  alerts: [],
  addAlert: (alert) => set((state) => ({
    alerts: [
      ...state.alerts.slice(-9), // max 10 alert
      { ...alert, id: `alert-${++alertIdCounter}`, timestamp: Date.now() }
    ]
  })),
  dismissAlert: (id) => set((state) => ({
    alerts: state.alerts.filter(a => a.id !== id)
  })),
  clearAlerts: () => set({ alerts: [] }),
}));
