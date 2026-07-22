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

const getAmtProfileStyle = (profile) => {
  if (!profile) return { color: 'var(--text-secondary)', borderColor: 'var(--border)', background: 'var(--bg-glass)' };
  const p = profile.toLowerCase();
  if (p.includes('neutral')) {
    return { color: 'var(--accent-purple)', borderColor: 'var(--accent-purple)', background: 'rgba(159,122,234,0.1)', border: '1px solid rgba(159,122,234,0.3)' };
  }
  if (p.includes('normal variation')) {
    return { color: 'var(--accent-blue)', borderColor: 'var(--accent-blue)', background: 'rgba(99,179,237,0.1)', border: '1px solid rgba(99,179,237,0.3)' };
  }
  if (p.includes('normal day')) {
    return { color: '#00f0ff', borderColor: '#00f0ff', background: 'rgba(0,240,255,0.08)', border: '1px solid rgba(0,240,255,0.25)' };
  }
  if (p.includes('non-trend') || p.includes('balance')) {
    return { color: 'var(--accent-orange)', borderColor: 'var(--accent-orange)', background: 'rgba(246,173,85,0.08)', border: '1px solid rgba(246,173,85,0.25)' };
  }
  return { color: 'var(--text-secondary)', borderColor: 'var(--border)', background: 'var(--bg-elevated)', border: '1px solid var(--border)' };
};

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

      {/* Context & Biases Checklist */}
      <div className="detail-section">
        <div className="detail-section-header">Context & Biases</div>
        <div className="detail-section-body" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          
          {/* Profiles and News row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px' }}>AMT Day Profile</div>
              <div style={{ 
                fontSize: '9.5px', 
                fontWeight: 'bold', 
                padding: '3px 6px', 
                borderRadius: '4px', 
                display: 'inline-block',
                ...getAmtProfileStyle(trade.amt_day_profile)
              }}>
                {trade.amt_day_profile || 'Price Discovery Phase'}
              </div>
            </div>
            
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px' }}>Macro News Block</div>
              <span className="tag" style={{
                fontSize: '9px', padding: '2px 6px',
                color: trade.news_flag && trade.news_flag !== 'none' ? 'var(--accent-orange)' : 'var(--text-secondary)',
                borderColor: trade.news_flag && trade.news_flag !== 'none' ? 'var(--accent-orange)' : 'var(--border)',
                background: trade.news_flag && trade.news_flag !== 'none' ? 'rgba(246, 173, 85, 0.1)' : 'var(--bg-glass)'
              }}>
                {trade.news_flag && trade.news_flag !== 'none' ? `⚠️ NEWS: ${trade.news_flag.toUpperCase()}` : '✅ NO NEWS BLOCK'}
              </span>
            </div>
          </div>

          {/* Macro Regime Box */}
          {(() => {
            const macro = trade.macro_regime || { regime: 'CHOP/BALANCE', duration_mins: 0, trigger: 'Inside Range / Dynamic', bias: 'none' };
            const regimeColor = macro.regime?.includes('EXPANSIVE') 
              ? 'var(--accent-green)' 
              : macro.regime?.includes('ACCUMULATION') 
                ? 'var(--accent-blue)' 
                : 'var(--accent-orange)';
            return (
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '6px', padding: '8px', fontSize: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Macro Regime State</span>
                  {macro.duration_mins > 0 && <span style={{ fontSize: '8.5px', color: 'var(--text-secondary)', background: 'var(--bg-elevated)', padding: '1px 4px', borderRadius: '3px' }}>⏱️ {macro.duration_mins}m</span>}
                </div>
                <div style={{ fontWeight: 'bold', color: regimeColor }}>{macro.regime || 'CHOP/BALANCE'}</div>
                <div style={{ fontSize: '9px', color: 'var(--text-secondary)', marginTop: '4px' }}><span style={{ color: 'var(--text-muted)' }}>Trigger:</span> {macro.trigger || 'N/A'}</div>
                <div style={{ fontSize: '9px', color: 'var(--text-secondary)', marginTop: '2px' }}><span style={{ color: 'var(--text-muted)' }}>Bias:</span> <span style={{ fontWeight: 'bold', color: macro.bias === 'long' ? 'var(--accent-green)' : macro.bias === 'short' ? 'var(--accent-red)' : 'var(--text-secondary)' }}>{macro.bias?.toUpperCase() || 'NEUTRAL'}</span></div>
              </div>
            );
          })()}

          {/* Wick Trapped Order Flow Checklist */}
          {((trade.trapped_info && trade.trapped_info !== 'none') || (trade.trapped_follow_through && !trade.trapped_follow_through.includes('No significant trapped'))) && (
            <div style={{ background: 'var(--bg-void)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '8px', fontSize: '9.5px', fontFamily: 'var(--font-mono)' }}>
              <div style={{ color: 'var(--accent-green)', fontWeight: 'bold', textTransform: 'uppercase', fontSize: '9px', fontFamily: 'var(--font-sans)', marginBottom: '4px' }}>Trapped Wick & Order Flow Confirmation</div>
              {trade.trapped_info && <div style={{ color: 'var(--accent-blue)', marginBottom: '3px' }}>⚡ {trade.trapped_info}</div>}
              {trade.trapped_follow_through && (
                <div style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                  {trade.trapped_follow_through}
                </div>
              )}
            </div>
          )}

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

      {/* Context & Biases Checklist */}
      <div className="detail-section">
        <div className="detail-section-header">Context & Biases</div>
        <div className="detail-section-body" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          
          {/* Profiles and News row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px' }}>AMT Day Profile</div>
              <div style={{ 
                fontSize: '9.5px', 
                fontWeight: 'bold', 
                padding: '3px 6px', 
                borderRadius: '4px', 
                display: 'inline-block',
                ...getAmtProfileStyle(proposal.amt_day_profile)
              }}>
                {proposal.amt_day_profile || 'Price Discovery Phase'}
              </div>
            </div>
            
            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: '4px' }}>Macro News Block</div>
              <span className="tag" style={{
                fontSize: '9px', padding: '2px 6px',
                color: proposal.news_flag && proposal.news_flag !== 'none' ? 'var(--accent-orange)' : 'var(--text-secondary)',
                borderColor: proposal.news_flag && proposal.news_flag !== 'none' ? 'var(--accent-orange)' : 'var(--border)',
                background: proposal.news_flag && proposal.news_flag !== 'none' ? 'rgba(246, 173, 85, 0.1)' : 'var(--bg-glass)'
              }}>
                {proposal.news_flag && proposal.news_flag !== 'none' ? `⚠️ NEWS: ${proposal.news_flag.toUpperCase()}` : '✅ NO NEWS BLOCK'}
              </span>
            </div>
          </div>

          {/* Macro Regime Box */}
          {(() => {
            const macro = proposal.macro_regime || { regime: 'CHOP/BALANCE', duration_mins: 0, trigger: 'Inside Range / Dynamic', bias: 'none' };
            const regimeColor = macro.regime?.includes('EXPANSIVE') 
              ? 'var(--accent-green)' 
              : macro.regime?.includes('ACCUMULATION') 
                ? 'var(--accent-blue)' 
                : 'var(--accent-orange)';
            return (
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '6px', padding: '8px', fontSize: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Macro Regime State</span>
                  {macro.duration_mins > 0 && <span style={{ fontSize: '8.5px', color: 'var(--text-secondary)', background: 'var(--bg-elevated)', padding: '1px 4px', borderRadius: '3px' }}>⏱️ {macro.duration_mins}m</span>}
                </div>
                <div style={{ fontWeight: 'bold', color: regimeColor }}>{macro.regime || 'CHOP/BALANCE'}</div>
                <div style={{ fontSize: '9px', color: 'var(--text-secondary)', marginTop: '4px' }}><span style={{ color: 'var(--text-muted)' }}>Trigger:</span> {macro.trigger || 'N/A'}</div>
                <div style={{ fontSize: '9px', color: 'var(--text-secondary)', marginTop: '2px' }}><span style={{ color: 'var(--text-muted)' }}>Bias:</span> <span style={{ fontWeight: 'bold', color: macro.bias === 'long' ? 'var(--accent-green)' : macro.bias === 'short' ? 'var(--accent-red)' : 'var(--text-secondary)' }}>{macro.bias?.toUpperCase() || 'NEUTRAL'}</span></div>
              </div>
            );
          })()}

          {/* Wick Trapped Order Flow Checklist */}
          {((proposal.trapped_info && proposal.trapped_info !== 'none') || (proposal.trapped_follow_through && !proposal.trapped_follow_through.includes('No significant trapped'))) && (
            <div style={{ background: 'var(--bg-void)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '8px', fontSize: '9.5px', fontFamily: 'var(--font-mono)' }}>
              <div style={{ color: 'var(--accent-green)', fontWeight: 'bold', textTransform: 'uppercase', fontSize: '9px', fontFamily: 'var(--font-sans)', marginBottom: '4px' }}>Trapped Wick & Order Flow Confirmation</div>
              {proposal.trapped_info && <div style={{ color: 'var(--accent-blue)', marginBottom: '3px' }}>⚡ {proposal.trapped_info}</div>}
              {proposal.trapped_follow_through && (
                <div style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                  {proposal.trapped_follow_through}
                </div>
              )}
            </div>
          )}

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
          </div>
        )}
      </div>
    </div>
  );
}
