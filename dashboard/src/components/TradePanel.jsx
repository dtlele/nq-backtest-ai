function fmtTime(iso, tz = 'America/New_York') {
  return new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', timeZone: tz })
}

function ApmDecisionClass(d) {
  if (d.includes('TARGET')) return 'win'
  if (d.includes('STOP')) return 'loss'
  if (d.includes('TRAIL')) return 'trail'
  if (d.includes('ENTRY')) return 'entry'
  return 'hold'
}

function TradeDetail({ trade, timeZone }) {
  const isWin = trade.pnl_usd > 0
  return (
    <>
      {/* Alerts */}
      {trade.vwap > 0 && (
        <div className={`alert-box ${trade.direction === 'long' ? 'vwap-long' : 'vwap-short'}`}>
          <span>📊</span>
          <span>
            Price {trade.direction === 'long' ? 'ABOVE' : 'BELOW'} VWAP ({trade.vwap.toFixed(2)}) —
            {trade.direction === 'long' ? ' buying pressure (Zarattini & Aziz)' : ' selling pressure (Zarattini & Aziz)'}
          </span>
        </div>
      )}
      {trade.nav_alert && (
        <div className="alert-box nav">
          <span>🚨</span>
          <span>ABNORMAL VOLUME SPIKE — Volume &gt;2.33σ sopra media sessione (Bajo 2010). Continuazione istituzionale attesa.</span>
        </div>
      )}

      {/* Stats */}
      <div className="detail-section">
        <div className="detail-section-header">Trade Stats</div>
        <div className="detail-section-body">
          <div className="stat-row">
            <span className="stat-label">Direzione</span>
            <span className={`tag tag-${trade.direction === 'long' ? 'long' : 'short'}`}>{trade.direction.toUpperCase()}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Entry</span>
            <span className="stat-val">{trade.entry?.toFixed(2)} · {trade.entry_time ? fmtTime(trade.entry_time, timeZone) : ''} {timeZone === 'America/New_York' ? 'ET' : 'Local'}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Exit</span>
            <span className="stat-val">{trade.exit_price?.toFixed(2)} · {trade.exit_time ? fmtTime(trade.exit_time, timeZone) : ''} {timeZone === 'America/New_York' ? 'ET' : 'Local'}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Stop / Target</span>
            <span className="stat-val">{trade.stop} / {trade.target}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">P&amp;L</span>
            <span className={`stat-val ${isWin ? 'pos' : 'neg'}`} style={{ color: isWin ? 'var(--accent-green)' : 'var(--accent-red)' }}>
              {isWin ? '+' : ''}${trade.pnl_usd?.toFixed(2)} ({trade.pnl_ticks > 0 ? '+' : ''}{trade.pnl_ticks} ticks)
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Confidenza / R</span>
            <span className="stat-val">{trade.final_confidence}% · {trade.r_ratio}R</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Contratti</span>
            <span className="stat-val">{trade.contracts}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Setup</span>
            <span className="stat-val" style={{ color: 'var(--text-secondary)' }}>{trade.setup_type?.replace(/_/g, ' ') || 'N/A'}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Exit reason</span>
            <span className={`tag tag-${trade.exit_reason === 'target' ? 'win' : 'loss'}`}>{trade.exit_reason || 'unknown'}</span>
          </div>
        </div>
      </div>

      {/* Fabio reasoning */}
      <div className="detail-section">
        <div className="detail-section-header">🤖 Fabio — Analisi Entry</div>
        <div className="detail-section-body">
          <p className="reasoning-text">{trade.fabio_reasoning}</p>
        </div>
      </div>

      {/* Andrea reasoning - always shown */}
      <div className="detail-section">
        <div className="detail-section-header">🔍 Andrea — Conferma Strutturale</div>
        <div className="detail-section-body">
          <p className="reasoning-text">
            {trade.andrea_reasoning || '(Nessuna conferma di Andrea per questo trade)'}
          </p>
        </div>
      </div>

      {/* APM Timeline */}
      {trade.apm_events && (
        <div className="detail-section">
          <div className="detail-section-header">⚡ APM — Gestione Posizione</div>
          <div className="detail-section-body">
            {trade.apm_events.map((ev, i) => (
              <div key={i} className="apm-event">
                <span className="apm-time">{ev.time}</span>
                <div className="apm-body">
                  <div className="apm-decision">
                    <span className={`apm-decision ${ApmDecisionClass(ev.decision)}`}>{ev.decision}</span>
                    {ev.rr > 0 && <span className="apm-rr">R:R {ev.rr}</span>}
                  </div>
                  <div className="apm-reason">{ev.reason}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}

function ProposalDetail({ proposal, timeZone }) {
  return (
    <>
      <div className="alert-box vwap-short" style={{ backgroundColor: 'var(--bg-glass)', borderColor: 'var(--border)' }}>
        <span>ℹ️</span>
        <span>
          Questo setup è stato proposto da Fabio ma scartato dai filtri successivi (es. spread, rischio, filtri di sistema).
        </span>
      </div>

      {/* Stats */}
      <div className="detail-section">
        <div className="detail-section-header">Proposal Stats</div>
        <div className="detail-section-body">
          <div className="stat-row">
            <span className="stat-label">Direzione</span>
            <span className={`tag tag-${proposal.direction === 'long' ? 'long' : 'short'}`}>{proposal.direction.toUpperCase()}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Proposta Entry</span>
            <span className="stat-val">{proposal.entry?.toFixed(2) || 'N/A'} · {fmtTime(proposal.bar_time_utc, timeZone)} {timeZone === 'America/New_York' ? 'ET' : 'Local'}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Stop / Target</span>
            <span className="stat-val">{proposal.stop} / {proposal.target}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Confidenza</span>
            <span className="stat-val">{proposal.confidence}%</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Setup Type</span>
            <span className="stat-val" style={{ color: 'var(--text-secondary)' }}>{proposal.setup_type?.replace(/_/g, ' ') || 'N/A'}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Motivo No Trade</span>
            <span className="tag tag-loss" style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={proposal.no_trade_reason}>
              {proposal.no_trade_reason || 'Sconosciuto'}
            </span>
          </div>
        </div>
      </div>

      {/* Fabio reasoning */}
      <div className="detail-section">
        <div className="detail-section-header">🤖 Fabio — Analisi Setup</div>
        <div className="detail-section-body">
          <p className="reasoning-text">{proposal.fabio_reasoning || '(Nessun ragionamento disponibile)'}</p>
        </div>
      </div>
    </>
  )
}

export default function TradePanel({ trade, allTrades = [], proposals = [], onSelect, timeZone }) {
  return (
    <div className="trade-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div className="panel-header" style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div className="panel-title" style={{ fontSize: 14, fontWeight: 'bold' }}>Trade Lifecycle</div>
            <div className="panel-sub" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {trade
                ? `${trade.direction.toUpperCase()} @ ${trade.entry?.toFixed(2)}`
                : 'Lista delle operazioni del giorno'}
            </div>
          </div>
          {trade && (
            <button 
              onClick={() => onSelect(null)}
              style={{
                background: 'var(--bg-glass)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
                padding: '4px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: 10
              }}
            >
              ← Lista
            </button>
          )}
        </div>
      </div>
      
      <div className="panel-scroll" style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {trade ? (
          trade.exit_price ? (
            <TradeDetail trade={trade} timeZone={timeZone} />
          ) : (
            <ProposalDetail proposal={trade} timeZone={timeZone} />
          )
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Executed Trades Section */}
            <div>
              <div style={{ fontSize: 12, fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                🟢 Eseguiti ({allTrades.length})
              </div>
              {allTrades.length === 0 ? (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic', padding: '8px 0' }}>
                  Nessun trade eseguito oggi.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {allTrades.map((t, idx) => {
                    const isWin = t.pnl_usd > 0;
                    return (
                      <div 
                        key={idx} 
                        onClick={() => onSelect(t)}
                        style={{
                          background: 'var(--bg-glass)',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          padding: '10px 12px',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          transition: 'border-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-blue)'}
                        onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: 10, fontWeight: 'bold', color: 'var(--text-muted)' }}>
                              {t.entry_time ? fmtTime(t.entry_time, timeZone) : ''} {timeZone === 'America/New_York' ? 'ET' : 'Local'}
                            </span>
                            <span className={`tag tag-${t.direction === 'long' ? 'long' : 'short'}`} style={{ fontSize: 9, padding: '2px 4px' }}>
                              {t.direction.toUpperCase()}
                            </span>
                            <span style={{ fontSize: 11, fontWeight: 'bold' }}>
                              @{t.entry?.toFixed(2)}
                            </span>
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: '4px' }}>
                            Setup: {t.setup_type || 'N/A'} · Qty: {t.contracts}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontSize: 11, fontWeight: 'bold', color: isWin ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                            {isWin ? '+' : ''}${t.pnl_usd?.toFixed(2)}
                          </div>
                          <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>
                            {t.exit_reason}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Proposals Section */}
            <div>
              <div style={{ fontSize: 12, fontWeight: 'bold', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '8px', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                ⚪ Scartati / No Trade ({proposals.length})
              </div>
              {proposals.length === 0 ? (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic', padding: '8px 0' }}>
                  Nessun setup scartato oggi.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {proposals.map((p, idx) => {
                    return (
                      <div 
                        key={idx} 
                        onClick={() => onSelect(p)}
                        style={{
                          background: 'var(--bg-glass)',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          padding: '10px 12px',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          transition: 'border-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-blue)'}
                        onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
                      >
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: 10, fontWeight: 'bold', color: 'var(--text-muted)' }}>
                              {p.bar_time_utc ? fmtTime(p.bar_time_utc, timeZone) : ''} {timeZone === 'America/New_York' ? 'ET' : 'Local'}
                            </span>
                            <span className={`tag tag-${p.direction === 'long' ? 'long' : 'short'}`} style={{ fontSize: 9, padding: '2px 4px' }}>
                              {p.direction.toUpperCase()}
                            </span>
                            <span style={{ fontSize: 11, fontWeight: 'bold' }}>
                              @{p.entry?.toFixed(2) || 'N/A'}
                            </span>
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: '4px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            Setup: {p.setup_type || 'N/A'}
                          </div>
                        </div>
                        <div style={{ textTransform: 'uppercase', fontSize: 9, padding: '2px 6px', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-red)', maxWidth: '120px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={p.no_trade_reason}>
                          {p.no_trade_reason?.replace(/_/g, ' ') || 'VETO'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
