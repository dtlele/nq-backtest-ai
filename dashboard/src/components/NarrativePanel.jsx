import React, { useState } from 'react';

function fmtTime(iso, tz = 'America/New_York') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', timeZone: tz });
  } catch {
    return '';
  }
}

export default function NarrativePanel({ reasonings = [], onJump, timeZone }) {
  const [searchTerm, setSearchTerm] = useState('');

  // Filter out entries that don't have a market narrative
  const narrativeEntries = reasonings.filter(r => r.market_narrative && r.market_narrative.trim() !== '');

  const filteredEntries = narrativeEntries.filter(r => {
    return r.market_narrative.toLowerCase().includes(searchTerm.toLowerCase()) ||
           r.bar_time_et?.includes(searchTerm);
  }).reverse();

  const getDecisionBadgeClass = (d) => {
    if (d?.toLowerCase() === 'trade') return 'tag-win';
    if (d?.toLowerCase() === 'no_trade') return 'tag-nav';
    return 'tag-hold';
  };

  const getDecisionLabel = (r) => {
    if (r.decision?.toLowerCase() === 'trade') {
      return r.direction?.toUpperCase() === 'LONG' ? '🟩 LONG' : '🟥 SHORT';
    }
    if (r.decision?.toLowerCase() === 'no_trade') return '🚫 NO TRADE';
    return '⚡ SKIPPED';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-base)' }}>
      {/* Search Bar */}
      <div style={{ padding: 12, borderBottom: '1px solid var(--border)' }}>
        <input
          type="text"
          placeholder="Cerca nella narrazione..."
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
      </div>

      {/* Narrative Timeline */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {filteredEntries.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 11 }}>
            Nessuna narrazione registrata per questa giornata.
          </div>
        ) : (
          <div style={{ position: 'relative', borderLeft: '2px solid var(--border)', marginLeft: 8, paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 20 }}>
            {filteredEntries.map((r, i) => (
              <div 
                key={i} 
                style={{ 
                  position: 'relative',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  padding: 12,
                  fontSize: 11.5,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                }}
              >
                {/* Timeline dot */}
                <div style={{
                  position: 'absolute',
                  left: -23,
                  top: 14,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: r.decision?.toLowerCase() === 'trade' ? 'var(--accent-green)' : 'var(--text-muted)',
                  border: '2px solid var(--bg-base)',
                  boxShadow: '0 0 0 1px var(--border)'
                }} />

                {/* Header info */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 'bold', fontSize: 11, color: 'var(--accent-blue)' }}>
                      {fmtTime(r.bar_time_utc, timeZone)} {timeZone === 'America/New_York' ? 'ET' : 'Local'}
                    </span>
                    <span className={`tag ${getDecisionBadgeClass(r.decision)}`} style={{ fontSize: 9, padding: '1px 5px' }}>
                      {getDecisionLabel(r)}
                    </span>
                  </div>
                  {onJump && (
                    <button
                      onClick={() => onJump(r)}
                      style={{
                        padding: '2px 6px',
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid var(--border)',
                        borderRadius: 4,
                        fontSize: 9,
                        color: 'var(--text-secondary)',
                        cursor: 'pointer'
                      }}
                    >
                      🎯 Jump
                    </button>
                  )}
                </div>

                {/* Context indicators */}
                <div style={{ display: 'flex', gap: 10, fontSize: 9.5, color: 'var(--text-muted)', marginBottom: 8, flexWrap: 'wrap', background: 'rgba(0,0,0,0.1)', padding: '4px 6px', borderRadius: 4 }}>
                  <span><strong>Giorno:</strong> {r.day_type || 'Chop'}</span>
                  {r.ib_low && <span>| <strong>IB:</strong> {r.ib_low}-{r.ib_high}</span>}
                  {r.va_low && <span>| <strong>VA:</strong> {r.va_low}-{r.va_high}</span>}
                  {r.poc && <span>| <strong>POC:</strong> {r.poc}</span>}
                  {r.bar_volume && <span>| <strong>Vol:</strong> {r.bar_volume}</span>}
                  {r.bar_delta !== undefined && (
                    <span>| <strong>Delta:</strong> <span style={{ color: r.bar_delta >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{r.bar_delta > 0 ? `+${r.bar_delta}` : r.bar_delta}</span></span>
                  )}
                  {r.close_percentile !== undefined && <span>| <strong>Chiusura %:</strong> {(r.close_percentile * 100).toFixed(0)}%</span>}
                </div>

                {/* Narrative Text */}
                <div style={{ 
                  lineHeight: '1.45', 
                  color: 'var(--text-primary)',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'system-ui, sans-serif'
                }}>
                  {r.market_narrative}
                </div>

                {/* Small indicator of the decision context */}
                {r.fabio_reasoning && (
                  <div style={{ 
                    marginTop: 10, 
                    padding: '6px 8px', 
                    background: 'rgba(255,255,255,0.02)', 
                    borderRadius: 4, 
                    borderLeft: '2px solid var(--border)',
                    fontSize: 10,
                    color: 'var(--text-muted)',
                    fontStyle: 'italic'
                  }}>
                    <strong>Decision Context:</strong> {r.fabio_reasoning.slice(0, 100)}...
                  </div>
                )}

                {/* Session Memory Timeline */}
                {r.session_memory && r.session_memory.length > 0 && (
                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', marginTop: 8, paddingTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div style={{ fontSize: 9, color: 'var(--accent-cyan, #00f0ff)', textTransform: 'uppercase', fontWeight: 'bold' }}>Session Memory History</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4, maxHeight: '100px', overflowY: 'auto', paddingRight: 4 }}>
                      {r.session_memory.map((mem, idx) => {
                        const splitIdx = mem.indexOf(']') + 1;
                        const timePart = splitIdx > 0 ? mem.substring(0, splitIdx) : '';
                        const descPart = splitIdx > 0 ? mem.substring(splitIdx) : mem;
                        return (
                          <div key={idx} style={{ fontSize: 9.5, color: 'var(--text-secondary)', lineHeight: '1.3', display: 'flex', gap: 6 }}>
                            <span style={{ color: 'var(--accent-cyan, #00f0ff)', whiteSpace: 'nowrap' }}>{timePart}</span>
                            <span>{descPart}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
