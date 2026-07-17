import React, { useState } from 'react';

function fmtTime(iso, tz = 'America/New_York') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', timeZone: tz });
  } catch {
    return '';
  }
}

export default function ReasoningsPanel({ reasonings = [], activeReasoning, onSelect, onJump, timeZone }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all'); // 'all' | 'trade' | 'no_trade' | 'prefiltered'
  const [expandedId, setExpandedId] = useState(null);

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

  const filteredReasonings = reasonings.filter(r => {
    const matchesSearch = 
      r.fabio_reasoning?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.no_trade_reason?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.bar_time_et?.includes(searchTerm);
    
    const isApm = r.market_state === 'active_trade_mgmt' || r.fabio_setup === 'apm' || r.entry_type === 'apm';
    const isPending = r.decision?.toLowerCase() === 'pending';
    if (filterType === 'all') return matchesSearch;
    if (filterType === 'apm') return matchesSearch && isApm;
    if (filterType === 'trade') return matchesSearch && !isApm && (r.decision?.toLowerCase() === 'trade' || r.entry_type === 'limit_pending');
    if (filterType === 'no_trade') return matchesSearch && !isApm && r.decision?.toLowerCase() === 'no_trade';
    if (filterType === 'pending') return matchesSearch && isPending;
    if (filterType === 'prefiltered') return matchesSearch && !isApm && r.decision?.toLowerCase() === 'prefiltered';
    return matchesSearch;
  });

  const getDecisionBadgeClass = (d) => {
    if (d?.toLowerCase() === 'trade') return 'tag-win';
    if (d?.toLowerCase() === 'no_trade') return 'tag-nav';
    if (d?.toLowerCase() === 'pending') return 'tag-hold';
    return 'tag-hold';
  };

  const getDecisionLabel = (r) => {
    if (r.decision?.toLowerCase() === 'trade') {
      const isLimitFill = r.entry_type === 'limit_pending' || r.fabio_setup === 'limit_fill' || r.fabio_setup === 'limit_fill_eod';
      if (isLimitFill) return `✅ LIMIT FILL ${(r.fabio_direction||'').toUpperCase()}`;
      return r.direction?.toUpperCase() === 'LONG' ? '🟩 LONG TRADE' : '🟥 SHORT TRADE';
    }
    if (r.decision?.toLowerCase() === 'pending') {
      return `⏳ PENDING ${(r.trade_direction || r.fabio_direction || '').toUpperCase()} @${r.trade_entry ? Number(r.trade_entry).toFixed(2) : ''}`;
    }
    if (r.decision?.toLowerCase() === 'no_trade') return '🚫 NO TRADE';
    return '⚡ SKIPPED';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-base)' }}>
      {/* Search & Filters */}
      <div style={{ padding: 12, borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <input
          type="text"
          placeholder="Cerca nei ragionamenti..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '6px 10px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text-primary)',
            fontSize: 11,
            outline: 'none'
          }}
        />
        <div style={{ display: 'flex', gap: 4 }}>
          {['all', 'apm', 'trade', 'pending', 'no_trade', 'prefiltered'].map(type => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              style={{
                flex: 1,
                padding: '4px 2px',
                fontSize: 9,
                fontWeight: 'bold',
                textTransform: 'uppercase',
                borderRadius: 4,
                background: filterType === type 
                  ? (type === 'apm' ? 'rgba(246,173,85,0.15)' : 'var(--accent-blue-glow)') 
                  : 'var(--bg-glass)',
                border: filterType === type 
                  ? (type === 'apm' ? '1px solid var(--accent-orange)' : '1px solid var(--accent-blue)')
                  : '1px solid var(--border)',
                color: filterType === type 
                  ? (type === 'apm' ? 'var(--accent-orange)' : 'var(--accent-blue)') 
                  : 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              {type === 'all' ? 'Tutti' : type === 'apm' ? '⚡ APM' : type === 'trade' ? 'Trades' : type === 'no_trade' ? 'No Trade' : 'Skipped'}
            </button>
          ))}
        </div>
      </div>

      {/* Log List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filteredReasonings.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>
            Nessun ragionamento trovato
          </div>
        ) : (
          filteredReasonings.map((r, i) => {
            const isExpanded = expandedId === i;
            const isSelected = activeReasoning === r;
            
            const isApm = r.market_state === 'active_trade_mgmt' || r.fabio_setup === 'apm';
            const apmDecision = isApm ? (r.decision?.replace('apm_', '') || 'hold') : null;
            const apmReasoningRaw = isApm ? (r.no_trade_reason?.replace(/^APM:\s*(\w+)\s*-\s*/, '') || r.fabio_reasoning || '') : null;
            
            // ── APM Card (Trade Management) ──────────────────────────
            if (isApm) {
              const decisionColor = apmDecision === 'early_exit' ? 'var(--accent-red)' 
                : apmDecision === 'hold' ? 'var(--accent-green)' 
                : apmDecision === 'reverse' ? '#ff6b35'
                : 'var(--accent-orange)';
              return (
                <div
                  key={i}
                  style={{
                    background: 'rgba(246,173,85,0.04)',
                    border: isSelected ? '1px solid var(--accent-orange)' : '1px solid rgba(246,173,85,0.25)',
                    borderRadius: 8,
                    overflow: 'hidden',
                    cursor: 'pointer',
                  }}
                  onClick={() => { onSelect(r); setExpandedId(isExpanded ? null : i); }}
                >
                  {/* APM Header */}
                  <div style={{ padding: '7px 12px', background: 'rgba(246,173,85,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 12 }}>⚡</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', fontSize: 11, color: 'var(--accent-orange)' }}>
                        {fmtTime(r.bar_time_utc, timeZone)} — TRADE MGMT
                      </span>
                      <span style={{
                        fontSize: 9, fontWeight: 'bold', textTransform: 'uppercase',
                        padding: '2px 8px', borderRadius: 4,
                        background: `${decisionColor}22`,
                        border: `1px solid ${decisionColor}`,
                        color: decisionColor
                      }}>
                        {apmDecision?.toUpperCase()}
                      </span>
                    </div>
                    <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>APM Fabio</span>
                  </div>
                  {/* APM Levels */}
                  <div style={{ padding: '8px 12px', display: 'flex', gap: 16, fontSize: 10, borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <div><span style={{ color: 'var(--text-muted)' }}>Entry:</span> <span style={{ color: 'var(--accent-green)', fontWeight: 'bold' }}>{r.fabio_entry ?? '—'}</span></div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Stop:</span> <span style={{ color: 'var(--accent-red)', fontWeight: 'bold' }}>{r.fabio_stop ?? '—'}</span></div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Target:</span> <span style={{ color: 'var(--accent-blue)', fontWeight: 'bold' }}>{r.fabio_target ?? '—'}</span></div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Prezzo:</span> <span style={{ fontWeight: 'bold' }}>{r.bar_close}</span></div>
                  </div>
                  {/* APM Reasoning */}
                  {isExpanded && (
                    <div style={{ padding: '8px 12px', fontSize: 10, color: 'var(--text-secondary)', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                      {apmReasoningRaw || 'Nessun reasoning disponibile.'}
                    </div>
                  )}
                </div>
              );
            }

            // ── Standard Card ─────────────────────────────────────────
            return (
              <div
                key={i}
                style={{
                  background: 'var(--bg-surface)',
                  border: isSelected ? '1px solid var(--accent-blue)' : '1px solid var(--border)',
                  borderRadius: 8,
                  overflow: 'hidden',
                  cursor: 'pointer',
                  transition: 'border-color 0.2s, background 0.2s'
                }}
                onClick={() => {
                  onSelect(r);
                  setExpandedId(isExpanded ? null : i);
                }}
              >
                {/* Header */}
                <div style={{
                  padding: '8px 12px',
                  background: isSelected ? 'var(--accent-blue-glow)' : 'var(--bg-elevated)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: 11
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold' }}>
                      {fmtTime(r.bar_time_utc, timeZone)} {timeZone === 'America/New_York' ? 'ET' : 'Local'}
                    </span>
                    <span className={`tag ${getDecisionBadgeClass(r.decision)}`} style={{ fontSize: 9, padding: '1px 6px' }}>
                      {getDecisionLabel(r)}
                    </span>
                    {r.session_bias && r.session_bias !== 'none' && (
                      <span className="tag" style={{
                        fontSize: 9, padding: '1px 6px',
                        color: r.session_bias === 'long' ? 'var(--accent-green)' : 'var(--accent-red)',
                        borderColor: r.session_bias === 'long' ? 'var(--accent-green)' : r.session_bias === 'short' ? 'var(--accent-red)' : 'var(--border)',
                        background: r.session_bias === 'long' ? 'var(--accent-green-glow)' : 'var(--accent-red-glow)'
                      }}>
                        TREND BIAS: {r.session_bias.toUpperCase()}
                      </span>
                    )}
                    {r.fabio_direction && r.fabio_direction !== 'none' && (
                      <span className="tag" style={{
                        fontSize: 9, padding: '1px 6px',
                        color: r.fabio_direction === 'long' ? 'var(--accent-green)' : 'var(--accent-red)',
                        borderColor: r.fabio_direction === 'long' ? 'var(--accent-green)' : r.fabio_direction === 'short' ? 'var(--accent-red)' : 'var(--border)',
                        background: r.fabio_direction === 'long' ? 'var(--accent-green-glow)' : 'var(--accent-red-glow)'
                      }}>
                        FABIO: {r.fabio_direction.toUpperCase()}
                      </span>
                    )}
                    {r.news_flag && r.news_flag !== 'none' && (
                      <span className="tag" style={{
                        fontSize: 9, padding: '1px 6px',
                        color: 'var(--accent-orange)',
                        borderColor: 'var(--accent-orange)',
                        background: 'rgba(246, 173, 85, 0.1)'
                      }}>
                        NEWS: {r.news_flag.toUpperCase()}
                      </span>
                    )}
                    {r.fabio_imbalance_phase && r.fabio_imbalance_phase !== 'none' && (
                      <span className="tag" style={{
                        fontSize: 9, padding: '1px 6px',
                        color: r.fabio_imbalance_phase === 'accumulation' ? 'var(--accent-blue)' : 'var(--accent-orange)',
                        borderColor: r.fabio_imbalance_phase === 'accumulation' ? 'var(--accent-blue)' : 'var(--accent-orange)'
                      }}>
                        {r.fabio_imbalance_phase.toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {r.confidence > 0 && (
                      <span style={{ fontSize: 10, color: 'var(--text-secondary)', fontWeight: 'bold' }}>
                        {r.confidence}%
                      </span>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onJump(r);
                      }}
                      style={{
                        padding: '2px 6px',
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid var(--border)',
                        borderRadius: 4,
                        fontSize: 9,
                        color: 'var(--accent-blue)',
                        cursor: 'pointer'
                      }}
                      title="Centra grafico su questa candela"
                    >
                      🎯 Jump
                    </button>
                  </div>
                </div>

                {/* Body */}
                <div style={{ padding: '8px 12px', fontSize: 11.5 }}>
                  <p style={{
                    margin: 0,
                    lineHeight: '1.4',
                    color: isExpanded ? 'var(--text-primary)' : 'var(--text-secondary)',
                    overflow: 'hidden',
                    display: '-webkit-box',
                    WebkitLineClamp: isExpanded ? 'unset' : 2,
                    WebkitBoxOrient: 'vertical',
                    fontStyle: r.decision?.toLowerCase() !== 'trade' ? 'italic' : 'normal'
                  }}>
                    {r.fabio_reasoning || r.no_trade_reason || 'Nessun dettaglio registrato.'}
                  </p>
                  
                  {isExpanded && r.no_trade_reason && r.decision?.toLowerCase() !== 'trade' && (
                    <div style={{ marginTop: 8, padding: '4px 8px', background: 'rgba(0,0,0,0.15)', borderRadius: 4, borderLeft: '2px solid var(--accent-red)' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>MOTIVO: </span>
                      <span style={{ color: 'var(--accent-red)', fontWeight: 'bold', fontSize: 10 }}>{r.no_trade_reason}</span>
                    </div>
                  )}

                  {isExpanded && (
                    <div style={{ marginTop: 10, padding: 12, background: 'var(--bg-surface)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 10, border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 4px 20px rgba(0,0,0,0.4)' }}>
                      
                      {/* Macro news alert if active */}
                      {r.news_flag && r.news_flag !== 'none' && (
                        <div style={{
                          padding: '8px 12px',
                          background: 'rgba(246, 173, 85, 0.08)',
                          border: '1px solid var(--accent-orange)',
                          borderRadius: 6,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          fontSize: 10,
                          lineHeight: '1.4'
                        }}>
                          <span style={{ fontSize: 16 }}>⚠️</span>
                          <div>
                            <span style={{ color: 'var(--accent-orange)', fontWeight: 'bold', textTransform: 'uppercase', marginRight: 4 }}>NEWS ALERT: {r.news_flag.toUpperCase()}</span>
                            <span>Restrizione trading attiva per notizie macro ad alto impatto.</span>
                          </div>
                        </div>
                      )}

                      {/* Header Row: Biases & Dalton AMT Day Profile */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                        <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 6, padding: 8 }}>
                          <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: 4 }}>Market Profiles</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 10 }}>
                            <div><span style={{ color: 'var(--text-secondary)' }}>AMT Day Profile:</span></div>
                            <div style={{ 
                              marginTop: 2, 
                              fontSize: 9.5, 
                              fontWeight: 'bold', 
                              padding: '3px 6px', 
                              borderRadius: 4, 
                              display: 'inline-block',
                              ...getAmtProfileStyle(r.amt_day_profile)
                            }}>
                              {r.amt_day_profile || 'Price Discovery Phase'}
                            </div>
                            <div style={{ marginTop: 6 }}><span style={{ color: 'var(--text-secondary)' }}>Trend Type (Bias):</span> <span className="tag" style={{
                              fontSize: 9, padding: '1px 5px',
                              color: r.session_bias === 'long' ? 'var(--accent-green)' : r.session_bias === 'short' ? 'var(--accent-red)' : 'var(--text-secondary)',
                              borderColor: r.session_bias === 'long' ? 'var(--accent-green)' : r.session_bias === 'short' ? 'var(--accent-red)' : 'var(--border)'
                            }}>{r.session_bias?.toUpperCase() || 'NONE'}</span></div>
                          </div>
                        </div>

                        {/* Macro Regime Box */}
                        {(() => {
                          const macro = r.macro_regime || { regime: r.day_type === 'trend_up' ? 'EXPANSIVE (Initiative Momentum)' : r.day_type === 'trend_down' ? 'EXPANSIVE (Initiative Momentum)' : 'CHOP/BALANCE', duration_mins: 0, trigger: 'Inside range', bias: r.session_bias || 'none' };
                          const regimeColor = macro.regime?.includes('EXPANSIVE') 
                            ? 'var(--accent-green)' 
                            : macro.regime?.includes('ACCUMULATION') 
                              ? 'var(--accent-blue)' 
                              : 'var(--accent-orange)';
                          return (
                            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 6, padding: 8 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                                <span style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Macro Regime</span>
                                {macro.duration_mins > 0 && <span style={{ fontSize: 8.5, color: 'var(--text-secondary)', background: 'var(--bg-elevated)', padding: '1px 4px', borderRadius: 3 }}>⏱️ {macro.duration_mins}m</span>}
                              </div>
                              <div style={{ fontSize: 10, fontWeight: 'bold', color: regimeColor }}>{macro.regime?.toUpperCase() || 'CHOP/BALANCE'}</div>
                              <div style={{ fontSize: 9, color: 'var(--text-secondary)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={macro.trigger}><span style={{ color: 'var(--text-muted)' }}>Trig:</span> {macro.trigger || 'N/A'}</div>
                              <div style={{ fontSize: 9, color: 'var(--text-secondary)', marginTop: 2 }}><span style={{ color: 'var(--text-muted)' }}>Bias:</span> <span style={{ fontWeight: 'bold', color: macro.bias === 'long' ? 'var(--accent-green)' : macro.bias === 'short' ? 'var(--accent-red)' : 'var(--text-secondary)' }}>{macro.bias?.toUpperCase() || 'NEUTRAL'}</span></div>
                            </div>
                          );
                        })()}
                      </div>

                      {/* Grid for today / yesterday profiles */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, background: 'rgba(0,0,0,0.1)', padding: 8, borderRadius: 6 }}>
                        <div>
                          <div style={{ fontSize: 9, color: 'var(--accent-blue)', textTransform: 'uppercase', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 2 }}>Oggi ({r.day_type || 'Chop'})</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 4, fontSize: 9.5 }}>
                            <div><span style={{ color: 'var(--text-muted)' }}>IB:</span> {r.ib_low ? `${r.ib_low} - ${r.ib_high}` : 'N/A'} (Range: {r.ib_range ? `${r.ib_range.toFixed(2)} pts` : 'N/A'})</div>
                            <div><span style={{ color: 'var(--text-muted)' }}>VA:</span> {r.va_low ? `${r.va_low} - ${r.va_high}` : 'N/A'}</div>
                            <div><span style={{ color: 'var(--text-muted)' }}>POC:</span> {r.poc || 'N/A'}</div>
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 9, color: 'var(--accent-purple)', textTransform: 'uppercase', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 2 }}>Ieri (Profilo)</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 4, fontSize: 9.5 }}>
                            <div><span style={{ color: 'var(--text-muted)' }}>VAH:</span> {r.prev_day_vah || 'N/A'}</div>
                            <div><span style={{ color: 'var(--text-muted)' }}>VAL:</span> {r.prev_day_val || 'N/A'}</div>
                            <div><span style={{ color: 'var(--text-muted)' }}>POC:</span> {r.prev_day_poc || 'N/A'}</div>
                          </div>
                        </div>
                      </div>

                      {/* Setup Checks Checklist */}
                      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 6, padding: 8 }}>
                        <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: 6 }}>Setup Phase & Checklist</div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 10 }}>
                          
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ color: r.delta_divergence ? 'var(--accent-red)' : 'var(--text-muted)' }}>{r.delta_divergence ? '☑' : '☐'}</span>
                            <span style={{ color: r.delta_divergence ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Delta Divergence</span>
                          </div>
                          
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ color: r.effort_no_result ? 'var(--accent-orange)' : 'var(--text-muted)' }}>{r.effort_no_result ? '☑' : '☐'}</span>
                            <span style={{ color: r.effort_no_result ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Effort vs No Result</span>
                          </div>

                          {(() => {
                            const hasTrappedBuyers = r.trapped_info?.toLowerCase().includes('trapped buyers');
                            return (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span style={{ color: hasTrappedBuyers ? 'var(--accent-red)' : 'var(--text-muted)' }}>{hasTrappedBuyers ? '☑' : '☐'}</span>
                                <span style={{ color: hasTrappedBuyers ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Trapped Buyers (Absorption)</span>
                              </div>
                            );
                          })()}

                          {(() => {
                            const hasTrappedSellers = r.trapped_info?.toLowerCase().includes('trapped sellers');
                            return (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span style={{ color: hasTrappedSellers ? 'var(--accent-green)' : 'var(--text-muted)' }}>{hasTrappedSellers ? '☑' : '☐'}</span>
                                <span style={{ color: hasTrappedSellers ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Trapped Sellers (Absorption)</span>
                              </div>
                            );
                          })()}

                          {(() => {
                            const isConfirmed = r.trapped_follow_through?.toLowerCase().includes('confirmed');
                            return (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span style={{ color: isConfirmed ? 'var(--accent-green)' : 'var(--text-muted)' }}>{isConfirmed ? '☑' : '☐'}</span>
                                <span style={{ color: isConfirmed ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Trap Follow-through Confirmed</span>
                              </div>
                            );
                          })()}

                          {(() => {
                            const isFailed = r.trapped_follow_through?.toLowerCase().includes('failed') || r.trapped_follow_through?.toLowerCase().includes('released');
                            return (
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span style={{ color: isFailed ? 'var(--accent-red)' : 'var(--text-muted)' }}>{isFailed ? '☑' : '☐'}</span>
                                <span style={{ color: isFailed ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Trap Negated / Released</span>
                              </div>
                            );
                          })()}

                        </div>
                      </div>

                      {/* Level and Wall Proximity details */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, background: 'rgba(0,0,0,0.15)', padding: 8, borderRadius: 6, fontSize: 9.5 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <div><span style={{ color: 'var(--text-muted)' }}>Livello Prossimità:</span> {r.proximity_to?.toUpperCase() || 'N/A'} @ {r.proximity_level?.toFixed(2) || 'N/A'}</div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Distanza Chiusura:</span> {r.proximity_level && r.bar_close ? `${(r.bar_close - r.proximity_level).toFixed(2)} pts` : 'N/A'}</div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Volume / Delta Candela:</span> {r.bar_volume || 'N/A'} / <span style={{ color: (r.bar_delta || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{r.bar_delta > 0 ? `+${r.bar_delta}` : r.bar_delta || 'N/A'}</span></div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <div><span style={{ color: 'var(--text-muted)' }}>Prezzo Blocco (Wall):</span> <span style={{ color: r.wall_side === 'bid' ? 'var(--accent-red)' : r.wall_side === 'ask' ? 'var(--accent-green)' : 'var(--text-secondary)' }}>{r.wall_side?.toUpperCase()}</span> @ {r.wall_level?.toFixed(2) || 'N/A'}</div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Dettaglio Wall:</span> Max {r.wall_max_size} contratti · {r.wall_trade_count} trades</div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Wicks Ratio:</span> T {r.top_wick_ratio !== undefined ? `${(r.top_wick_ratio * 100).toFixed(0)}%` : 'N/A'} | B {r.bottom_wick_ratio !== undefined ? `${(r.bottom_wick_ratio * 100).toFixed(0)}%` : 'N/A'} · Close {r.close_percentile !== undefined ? `${(r.close_percentile * 100).toFixed(0)}%` : 'N/A'}</div>
                        </div>
                      </div>

                      {/* Footprint Order Flow Audit (Trapped & Follow-Through Terminal) */}
                      {((r.trapped_info && r.trapped_info !== 'none') || (r.trapped_follow_through && !r.trapped_follow_through.includes('No significant trapped'))) && (
                        <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 8 }}>
                          <div style={{ fontSize: 9, color: 'var(--accent-green)', textTransform: 'uppercase', fontWeight: 'bold', marginBottom: 4 }}>Order Flow Wick Absorption & Follow-Through</div>
                          <div style={{ 
                            background: 'var(--bg-void)', 
                            border: '1px solid rgba(255,255,255,0.05)', 
                            borderRadius: 6, 
                            padding: 8, 
                            fontFamily: 'var(--font-mono)', 
                            fontSize: 9.5, 
                            color: 'var(--text-primary)',
                            lineHeight: '1.4',
                            maxHeight: 120,
                            overflowY: 'auto'
                          }}>
                            {r.trapped_info && <div style={{ color: 'var(--accent-blue)', marginBottom: 4 }}>⚡ {r.trapped_info}</div>}
                            {r.trapped_follow_through && (
                              <div style={{ color: 'var(--text-secondary)' }}>
                                {r.trapped_follow_through.split('\n').map((line, idx) => (
                                  <div key={idx}>{line}</div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Session Memory Timeline */}
                      {r.session_memory && r.session_memory.length > 0 && (
                        <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <div style={{ fontSize: 9, color: 'var(--accent-cyan, #00f0ff)', textTransform: 'uppercase', fontWeight: 'bold' }}>Session Memory Timeline</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: '120px', overflowY: 'auto', paddingRight: 4 }}>
                            {r.session_memory.map((mem, idx) => (
                              <div key={idx} style={{ fontSize: 9, color: 'var(--text-secondary)', lineHeight: '1.35', display: 'flex', gap: 6 }}>
                                <span style={{ color: 'var(--accent-cyan, #00f0ff)', whiteSpace: 'nowrap' }}>{mem.substring(0, 10)}</span>
                                <span>{mem.substring(10)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {isExpanded && r.setup_type && r.setup_type !== 'none' && (
                    <div style={{ marginTop: 6, fontSize: 10, color: 'var(--text-muted)' }}>
                      Setup rilevato: <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{r.setup_type}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
