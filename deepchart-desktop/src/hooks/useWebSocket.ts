/**
 * Hook WebSocket con auto-reconnect e dispatch a Zustand store.
 * Gestisce tutti i tipi di messaggi del server DeepPrint Pro.
 */
import { useEffect, useRef, useCallback } from 'react';
import { useTradingStore } from '../store/tradingStore';

const WS_URL = 'ws://localhost:8765';
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(RECONNECT_BASE_MS);
  const unmountedRef = useRef(false);

  const {
    setWsStatus,
    setSendWsMessage,
    addCandle,
    setBatchCandles,
    clearCandles,
    setVolumeProfile,
    setSessionCtx,
    setDomData,
    setReplayStatus,
    setAvailableDates,
    addAlert,
    setTradeMarkers,
    setDailyRoadmap,
    setAgentSignals,
    setMemoryStats,
  } = useTradingStore();

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data);
      const { type, data } = msg;

      switch (type) {
        case 'candle_update':
          if (data) addCandle(data);
          break;

        case 'history_batch':
          // Batch iniziale di candele storiche
          if (data?.candles && Array.isArray(data.candles)) {
            clearCandles();
            setBatchCandles(data.candles);
          }
          break;

        case 'volume_profile_update':
          if (data) setVolumeProfile(data);
          break;

        case 'session_context':
          if (data) setSessionCtx(data);
          break;

        case 'dom_update':
          if (data) setDomData(data);
          break;

        case 'replay_status':
          if (data) {
            setReplayStatus(
              data.mode || 'paused',
              data.currentDate || '',
              data.currentBarIdx || 0,
              data.totalBars || 0,
              data.speedMultiplier || 60,
            );
          }
          break;

        case 'available_dates':
          if (data?.dates) setAvailableDates(data.dates);
          break;

        case 'trade_markers':
          if (data?.trades) setTradeMarkers(data.trades);
          break;

        case 'daily_roadmap':
          setDailyRoadmap(data || null);
          break;

        case 'agent_signals_batch':
          if (data?.signals) {
            setAgentSignals(data.signals);
            // Per ogni signal con decisione 'trade', aggiungi alert
            for (const signal of data.signals) {
              if (signal.finalDecision === 'trade') {
                addAlert({
                  type: 'trade',
                  direction: signal.direction === 'long' ? 'long' : 'short',
                  confidence: signal.confidence,
                  setupType: signal.setupType,
                  message: `${signal.direction?.toUpperCase()} — ${signal.setupType} — ${signal.confidence}% confidence`,
                  reasoning: signal.reasoning,
                });
              }
            }
          }
          break;

        case 'memory_stats':
          if (data?.stats) setMemoryStats(data.stats);
          break;

        case 'agent_signal':
          if (data) {
            addAlert({
              type: data.finalDecision === 'trade' ? 'trade' : 'no_trade',
              direction: data.direction,
              confidence: data.confidence,
              setupType: data.setupType,
              message: `${data.direction?.toUpperCase()} — ${data.setupType} — ${data.confidence}% confidence`,
              reasoning: data.reasoning,
            });
          }
          break;

        case 'session_end':
          addAlert({
            type: 'system',
            message: `Sessione ${data?.date || ''} terminata (${data?.totalBars || 0} barre)`,
          });
          break;

        case 'error':
          console.error('[WS] Server error:', data?.message);
          addAlert({ type: 'system', message: `Errore server: ${data?.message}` });
          break;

        case 'pong':
          // heartbeat ok
          break;

        default:
          // Messaggio sconosciuto, ignora silenziosamente
          break;
      }
    } catch (e) {
      console.error('[WS] Errore parsing messaggio:', e);
    }
  }, [addCandle, setBatchCandles, clearCandles, setVolumeProfile, setSessionCtx, setDomData, setReplayStatus, setAvailableDates, addAlert]);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setWsStatus('connecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (unmountedRef.current) { ws.close(); return; }
      setWsStatus('connected');
      reconnectDelayRef.current = RECONNECT_BASE_MS; // reset backoff
      console.log('[WS] Connesso a DeepPrint Pro server');

      // Richiedi stato iniziale
      ws.send(JSON.stringify({ action: 'get_available_dates' }));
    };

    ws.onmessage = handleMessage;

    ws.onerror = (e) => {
      console.warn('[WS] Errore connessione:', e);
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      setWsStatus('disconnected');
      wsRef.current = null;
      console.log(`[WS] Disconnesso. Riconnessione in ${reconnectDelayRef.current}ms...`);

      // Exponential backoff
      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, RECONNECT_MAX_MS);
        connect();
      }, reconnectDelayRef.current);
    };
  }, [handleMessage, setWsStatus]);

  // Funzione per inviare messaggi al server
  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      console.warn('[WS] Non connesso, impossibile inviare:', msg);
    }
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    setSendWsMessage(send);
    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect, send, setSendWsMessage]);

  return { send };
}
