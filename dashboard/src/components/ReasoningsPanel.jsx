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

  const filteredReasonings = reasonings.filter(r => {
    const matchesSearch = 
      r.fabio_reasoning?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.no_trade_reason?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.bar_time_et?.includes(searchTerm);
    
    if (filterType === 'all') return matchesSearch;
    if (filterType === 'trade') return matchesSearch && r.decision?.toLowerCase() === 'trade';
    if (filterType === 'no_trade') return matchesSearch && r.decision?.toLowerCase() === 'no_trade';
    if (filterType === 'prefiltered') return matchesSearch && r.decision?.toLowerCase() === 'prefiltered';
    return matchesSearch;
  });

  const getDecisionBadgeClass = (d) => {
    if (d?.toLowerCase() === 'trade') return 'tag-win';
    if (d?.toLowerCase() === 'no_trade') return 'tag-nav';
    return 'tag-hold';
  };

  const getDecisionLabel = (r) => {
    if (r.decision?.toLowerCase() === 'trade') {
      return r.direction?.toUpperCase() === 'LONG' ? '🟩 LONG TRADE' : '🟥 SHORT TRADE';
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
          {['all', 'trade', 'no_trade', 'prefiltered'].map(type => (
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
                background: filterType === type ? 'var(--accent-blue-glow)' : 'var(--bg-glass)',
                border: filterType === type ? '1px solid var(--accent-blue)' : '1px solid var(--border)',
                color: filterType === type ? 'var(--accent-blue)' : 'var(--text-secondary)',
                cursor: 'pointer'
              }}
            >
              {type === 'all' ? 'Tutti' : type === 'trade' ? 'Trades' : type === 'no_trade' ? 'No Trade' : 'Skipped'}
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
                    <div style={{ marginTop: 10, padding: 8, background: 'rgba(0,0,0,0.2)', borderRadius: 6, display: 'flex', flexDirection: 'column', gap: 6, border: '1px solid rgba(255,255,255,0.05)' }}>
                      {/* Grid for today / yesterday profiles */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        <div>
                          <div style={{ fontSize: 9, color: 'var(--accent-blue)', textTransform: 'uppercase', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 2 }}>Oggi ({r.day_type || 'Chop'})</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginTop: 4, fontSize: 9.5 }}>
                            <div><span style={{ color: 'var(--text-muted)' }}>IB:</span> {r.ib_low ? `${r.ib_low} - ${r.ib_high}` : 'N/A'}</div>
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

                      {/* Footprint metrics */}
                      <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 6, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 9.5 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <div><span style={{ color: 'var(--text-muted)' }}>Volume:</span> {r.bar_volume || 'N/A'}</div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Delta:</span> <span style={{ color: (r.bar_delta || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{r.bar_delta > 0 ? `+${r.bar_delta}` : r.bar_delta || 'N/A'}</span></div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Close %:</span> {r.close_percentile !== undefined ? `${(r.close_percentile * 100).toFixed(1)}%` : 'N/A'}</div>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <div><span style={{ color: 'var(--text-muted)' }}>Wicks:</span> T {r.top_wick_ratio !== undefined ? `${(r.top_wick_ratio * 100).toFixed(0)}%` : 'N/A'} | B {r.bottom_wick_ratio !== undefined ? `${(r.bottom_wick_ratio * 100).toFixed(0)}%` : 'N/A'}</div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Div. Delta:</span> {r.delta_divergence ? '⚠️ Sì' : 'No'}</div>
                          <div><span style={{ color: 'var(--text-muted)' }}>Effort vs NoRes:</span> {r.effort_no_result ? '⚠️ Sì' : 'No'}</div>
                        </div>
                      </div>

                      {/* Session Memory Timeline */}
                      {r.session_memory && r.session_memory.length > 0 && (
                        <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <div style={{ fontSize: 9, color: 'var(--accent-cyan, #00f0ff)', textTransform: 'uppercase', fontWeight: 'bold' }}>Session Memory History</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4, maxHeight: '120px', overflowY: 'auto', paddingRight: 4 }}>
                            {r.session_memory.map((mem, idx) => (
                              <div key={idx} style={{ fontSize: 9.5, color: 'var(--text-secondary)', lineHeight: '1.3', display: 'flex', gap: 6 }}>
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
