import React from 'react';

export default function LiveMonitorPanel({ sessionState, latestReasoning, onJump }) {
  if (!sessionState || !latestReasoning) {
    return (
      <div className="trade-panel" style={{ marginBottom: 12 }}>
        <div className="panel-header">
          <div className="panel-title">📡 Terminale Live</div>
          <div className="panel-sub">In attesa di dati live...</div>
        </div>
      </div>
    );
  }

  const { equity, daily_pnl_usd, trade_count_today } = sessionState;
  const { 
    date, bar_time_et, bar_open, bar_high, bar_low, bar_close, bar_volume, bar_delta, 
    decision, fabio_reasoning, fabio_confidence,
    wall_level, wall_side, wall_max_size, proximity_to, proximity_level,
    day_type, delta_divergence, effort_no_result, top_wick_ratio, bottom_wick_ratio
  } = latestReasoning;

  const pnlColor = daily_pnl_usd >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

  const decClass = decision === 'LONG' || decision === 'trade' ? 'win' 
                 : decision === 'SHORT' ? 'loss' 
                 : 'hold';

  // Format wick percentages
  const topWickPct = top_wick_ratio ? (top_wick_ratio * 100).toFixed(0) : '0';
  const botWickPct = bottom_wick_ratio ? (bottom_wick_ratio * 100).toFixed(0) : '0';

  return (
    <div style={{
      background: 'var(--bg-base)', display: 'flex', flexDirection: 'column',
      flexShrink: 0, marginBottom: 12, borderBottom: '1px solid var(--border)'
    }}>
      <div className="panel-header" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 10 }}>
        <div className="panel-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: 'var(--accent-red)' }}>●</span> Terminale Live
        </div>
        <div className="panel-sub">Sincronizzazione in tempo reale</div>
      </div>

      <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* Session Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 4 }}>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: 6, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>EQUITY</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold' }}>${equity ? equity.toFixed(0) : '---'}</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: 6, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>DAILY P&L</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', color: pnlColor }}>
              {daily_pnl_usd > 0 ? '+' : ''}${daily_pnl_usd ? daily_pnl_usd.toFixed(0) : '0'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: 6, textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>TRADES</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold' }}>{trade_count_today || 0}</div>
          </div>
        </div>

        {/* Latest Candle Scanner */}
        <div className="detail-section">
          <div 
            className="detail-section-header" 
            style={{ display: 'flex', justifyContent: 'space-between', cursor: 'pointer', transition: 'background 0.2s' }}
            onClick={onJump}
            onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-glass-hover)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'var(--bg-elevated)'}
            title="Clicca per centrare il grafico su questa candela"
          >
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>🔍 Scanner Ultima Candela</span>
            </span>
            <span style={{ color: 'var(--text-primary)' }}>{date} · {bar_time_et || '--:--'} ET</span>
          </div>
          <div className="detail-section-body" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            {/* Column 1: Price & Flow */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="stat-row" style={{ alignItems: 'flex-start' }}>
                <span className="stat-label">OHLC</span>
                <span className="stat-val" style={{ textAlign: 'right', lineHeight: '1.4', fontSize: 11 }}>
                  <div style={{ color: 'var(--text-secondary)' }}>O: {bar_open}</div>
                  <div style={{ color: 'var(--text-secondary)' }}>H: {bar_high}</div>
                  <div style={{ color: 'var(--text-secondary)' }}>L: {bar_low}</div>
                  <div style={{ color: 'var(--accent-blue)', fontWeight: 'bold' }}>C: {bar_close}</div>
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Volume</span>
                <span className="stat-val">{bar_volume || '---'}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Delta</span>
                <span className={`stat-val ${bar_delta > 0 ? 'pos' : 'neg'}`}>{bar_delta > 0 ? '+' : ''}{bar_delta || '---'}</span>
              </div>
            </div>
            {/* Column 2: Context & Orderflow */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, borderLeft: '1px solid var(--border)', paddingLeft: '12px' }}>
              <div className="stat-row">
                <span className="stat-label">Day Type</span>
                <span className="stat-val" style={{ textTransform: 'capitalize' }}>{day_type || 'Unknown'}</span>
              </div>
              <div className="stat-row" style={{ alignItems: 'flex-start' }}>
                <span className="stat-label">Livello Vicino</span>
                <span className="stat-val" style={{ textAlign: 'right', lineHeight: '1.4', fontSize: 11 }}>
                  {proximity_to ? (
                    <>
                      <div>{proximity_to}</div>
                      <div style={{ color: 'var(--text-muted)' }}>({proximity_level})</div>
                    </>
                  ) : 'Nessuno'}
                </span>
              </div>
              <div className="stat-row" style={{ alignItems: 'flex-start' }}>
                <span className="stat-label">Muro Orderbook</span>
                {wall_level ? (
                  <span className={`stat-val ${wall_side === 'ask' ? 'neg' : 'pos'}`} style={{ textAlign: 'right', lineHeight: '1.4', fontSize: 11 }}>
                    <div>{wall_max_size} lvl</div>
                    <div>@ {wall_level} ({wall_side})</div>
                  </span>
                ) : (
                  <span className="stat-val" style={{ color: 'var(--text-muted)' }}>Assente</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Masterclass M3 Candle Metrics Panel */}
        <div className="detail-section" style={{ marginTop: 4 }}>
          <div className="detail-section-header">
            <span>🛡️ Metriche Masterclass M3</span>
          </div>
          <div className="detail-section-body" style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: 11 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>Delta Divergenza:</span>
              <span className={`tag ${delta_divergence ? 'tag-loss' : 'tag-hold'}`} style={{ padding: '2px 6px', fontSize: 9 }}>
                {delta_divergence ? 'ATTIVA 🚨' : 'ASSENTE'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>Assorbimento Istituzionale:</span>
              <span className={`tag ${effort_no_result ? 'tag-win' : 'tag-hold'}`} style={{ padding: '2px 6px', fontSize: 9 }}>
                {effort_no_result ? 'EFFORT NO RESULT 🛡️' : 'ASSENTE'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>Top Wick Ratio (Rifiuto H):</span>
              <span style={{ fontWeight: 'bold', color: top_wick_ratio >= 0.40 ? 'var(--accent-orange)' : 'var(--text-primary)' }}>
                {topWickPct}% {top_wick_ratio >= 0.40 && '⚠️'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-muted)' }}>Bottom Wick Ratio (Rifiuto L):</span>
              <span style={{ fontWeight: 'bold', color: bottom_wick_ratio >= 0.40 ? 'var(--accent-orange)' : 'var(--text-primary)' }}>
                {botWickPct}% {bottom_wick_ratio >= 0.40 && '⚠️'}
              </span>
            </div>
          </div>
        </div>

        {/* Live Reasoning */}
        <div className="detail-section" style={{ marginTop: 8 }}>
          <div className="detail-section-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>🤖 Fabio Live Reasoning</span>
            <span className={`tag tag-${decClass}`}>{decision ? decision.toUpperCase() : 'WAITING'}</span>
          </div>
          <div className="detail-section-body">
            <p className="reasoning-text" style={{ fontStyle: 'italic', borderLeft: '2px solid var(--accent-blue)', paddingLeft: 8, margin: 0 }}>
              {fabio_reasoning || "In attesa della prossima candela..."}
            </p>
            {fabio_confidence !== undefined && (
               <div style={{ marginTop: 8, fontSize: 10, color: 'var(--text-muted)', textAlign: 'right' }}>
                 Confidenza: {fabio_confidence}%
               </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
