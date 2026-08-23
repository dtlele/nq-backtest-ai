/**
 * AlertPanel — Sistema di notifiche toast per segnali agenti e system alerts.
 * Slide-in dal basso destra, auto-dismiss dopo 10s, click per dettaglio reasoning.
 */
import React, { useEffect, useState } from 'react';
import { useTradingStore, Alert } from '../store/tradingStore';

const TYPE_STYLES: Record<Alert['type'], string> = {
  trade:    'border-emerald-500/70 bg-gradient-to-r from-emerald-950/90 to-slate-900/95',
  no_trade: 'border-slate-600/70 bg-slate-900/95',
  system:   'border-blue-500/50 bg-gradient-to-r from-blue-950/80 to-slate-900/95',
};

const AUTO_DISMISS_MS = 10000;

interface AlertItemProps {
  alert: Alert;
  onDismiss: (id: string) => void;
}

const AlertItem: React.FC<AlertItemProps> = ({ alert, onDismiss }) => {
  const [expanded, setExpanded] = useState(false);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onDismiss(alert.id), 300);
    }, AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, [alert.id, onDismiss]);

  if (!visible) return null;

  return (
    <div
      className={`
        relative border rounded-lg px-3 py-2.5 cursor-pointer
        transition-all duration-300 ease-in-out
        backdrop-blur-md shadow-2xl
        ${TYPE_STYLES[alert.type]}
        animate-slide-in
      `}
      style={{ animation: 'slideInRight 0.3s ease-out' }}
      onClick={() => setExpanded(e => !e)}
    >
      {/* Close button */}
      <button
        className="absolute top-1.5 right-1.5 text-slate-500 hover:text-white transition-colors"
        onClick={(e) => { e.stopPropagation(); onDismiss(alert.id); }}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
      </button>

      {/* Header */}
      <div className="flex items-center gap-2 pr-4">
        {alert.type === 'trade' && (
          <span className={`text-lg font-black ${alert.direction === 'long' ? 'text-emerald-400' : 'text-rose-400'}`}>
            {alert.direction === 'long' ? '▲' : '▼'}
          </span>
        )}
        {alert.type === 'system' && (
          <span className="text-blue-400 text-sm">ℹ</span>
        )}
        <span className="text-xs font-bold text-white leading-tight">{alert.message}</span>
        {alert.confidence !== undefined && (
          <span className={`ml-auto text-xs font-bold px-1.5 py-0.5 rounded ${
            alert.confidence >= 78 ? 'bg-emerald-700 text-emerald-200' :
            alert.confidence >= 60 ? 'bg-amber-700 text-amber-200' :
            'bg-slate-700 text-slate-300'
          }`}>
            {alert.confidence}%
          </span>
        )}
      </div>

      {/* Expanded reasoning */}
      {expanded && alert.reasoning && (
        <div className="mt-2 pt-2 border-t border-slate-700/50 text-[10px] text-slate-300 font-mono leading-relaxed max-h-24 overflow-y-auto">
          {alert.reasoning.slice(0, 300)}{alert.reasoning.length > 300 ? '...' : ''}
        </div>
      )}

      {/* Progress bar auto-dismiss */}
      <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-b-lg overflow-hidden">
        <div
          className={`h-full ${alert.type === 'trade' ? 'bg-emerald-500' : alert.type === 'system' ? 'bg-blue-500' : 'bg-slate-500'}`}
          style={{
            animation: `shrink ${AUTO_DISMISS_MS}ms linear forwards`,
          }}
        />
      </div>
    </div>
  );
};

export const AlertPanel: React.FC = () => {
  const { alerts, dismissAlert } = useTradingStore();

  if (alerts.length === 0) return null;

  return (
    <>
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
        @keyframes shrink {
          from { width: 100%; }
          to   { width: 0%;   }
        }
      `}</style>

      <div className="fixed bottom-20 right-4 z-50 flex flex-col gap-2 w-72 pointer-events-none">
        {alerts.map(alert => (
          <div key={alert.id} className="pointer-events-auto">
            <AlertItem alert={alert} onDismiss={dismissAlert} />
          </div>
        ))}
      </div>
    </>
  );
};
