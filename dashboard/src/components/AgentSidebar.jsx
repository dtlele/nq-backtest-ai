import { useState, useEffect, useRef } from 'react'

// ── Typing animation hook ──────────────────────────────────────────────────
function useTypingText(text, active) {
  const [displayed, setDisplayed] = useState('')
  const [done, setDone] = useState(false)
  useEffect(() => {
    if (!text) { setDisplayed(''); setDone(false); return }
    if (!active) { setDisplayed(text); setDone(true); return }
    setDisplayed('')
    setDone(false)
    let i = 0
    const interval = setInterval(() => {
      i++
      setDisplayed(text.slice(0, i))
      if (i >= text.length) { clearInterval(interval); setDone(true) }
    }, 12)
    return () => clearInterval(interval)
  }, [text, active])
  return { displayed, done }
}

// ── Confidence gauge ───────────────────────────────────────────────────────
function ConfidenceGauge({ value }) {
  const color = value >= 75 ? 'var(--accent-green)' : value >= 50 ? 'var(--accent-orange)' : 'var(--accent-red)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        flex: 1, height: 5, background: 'rgba(255,255,255,0.07)', borderRadius: 4, overflow: 'hidden',
      }}>
        <div style={{
          width: `${value}%`, height: '100%', background: color,
          borderRadius: 4,
          transition: 'width 1s ease, background 0.5s ease',
          boxShadow: `0 0 8px ${color}60`,
        }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color, minWidth: 28 }}>{value}%</span>
    </div>
  )
}

// ── ThinkingBadge ──────────────────────────────────────────────────────────
function ThinkingBadge() {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: 'rgba(99,179,237,0.12)', border: '1px solid rgba(99,179,237,0.25)',
      borderRadius: 20, padding: '2px 8px', fontSize: 9, fontWeight: 700, letterSpacing: '0.06em', color: 'var(--accent-blue)',
    }}>
      <span style={{ animation: 'thinking-pulse 1s infinite' }}>●</span> THINKING
    </div>
  )
}

// ── AgentCard wrapper ──────────────────────────────────────────────────────
function AgentCard({ icon, title, subtitle, accent = '#63b3ed', isActive = false, isThinking = false, children }) {
  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: `1px solid ${isActive ? accent + '40' : 'var(--border)'}`,
      borderRadius: 10,
      overflow: 'hidden',
      transition: 'border-color 0.3s',
      boxShadow: isActive ? `0 0 20px ${accent}15` : 'none',
    }}>
      {/* Card header */}
      <div style={{
        padding: '8px 12px',
        background: isActive ? `${accent}10` : 'var(--bg-elevated)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span style={{ fontSize: 13 }}>{icon}</span>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.05em', color: isActive ? accent : 'var(--text-secondary)' }}>{title}</div>
            {subtitle && <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>{subtitle}</div>}
          </div>
        </div>
        {isThinking && <ThinkingBadge />}
        {isActive && !isThinking && (
          <div style={{
            width: 6, height: 6, borderRadius: '50%', background: accent,
            boxShadow: `0 0 8px ${accent}`,
            animation: 'thinking-pulse 1.5s infinite',
          }} />
        )}
      </div>
      <div style={{ padding: '10px 12px' }}>{children}</div>
    </div>
  )
}

// ── Step 1: Context Card ───────────────────────────────────────────────────
function ContextAgentCard({ latestReasoning }) {
  const hasData = latestReasoning && latestReasoning.date

  const bias = latestReasoning?.bias || latestReasoning?.fabio_direction || null
  const dayType = latestReasoning?.day_type || '---'
  const marketState = latestReasoning?.market_state || '---'
  const narrative = latestReasoning?.session_narrative || latestReasoning?.fabio_reasoning || ''
  const isThinking = !hasData

  const { displayed } = useTypingText(narrative, !!narrative)

  const biasColor = bias === 'long' ? 'var(--accent-green)' : bias === 'short' ? 'var(--accent-red)' : 'var(--text-muted)'
  const biasLabel = bias ? bias.toUpperCase() : 'NEUTRAL'

  return (
    <AgentCard
      icon="🧠"
      title="STEP 1 — CONTEXT AGENT"
      subtitle="Setup recognition · Trapped side · Market state"
      accent="#9f7aea"
      isActive={hasData}
      isThinking={isThinking}
    >
      {!hasData ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 11, textAlign: 'center', padding: '12px 0' }}>
          In attesa di dati sessione...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Bias + State row */}
          <div style={{ display: 'flex', gap: 6 }}>
            <div style={{
              flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
              border: `1px solid ${biasColor}25`,
            }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>BIAS</div>
              <div style={{ fontSize: 13, fontWeight: 800, color: biasColor, fontFamily: 'var(--font-mono)' }}>{biasLabel}</div>
            </div>
            <div style={{
              flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
            }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>DAY TYPE</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase' }}>{dayType}</div>
            </div>
            <div style={{
              flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
            }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>MARKET</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{marketState}</div>
            </div>
          </div>

          {/* Volume Profile snapshot */}
          {(latestReasoning?.proximity_level || latestReasoning?.wall_level) && (
            <div style={{ display: 'flex', gap: 6 }}>
              {latestReasoning.proximity_level && (
                <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '5px 8px' }}>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>NEAR LEVEL</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-yellow)' }}>{latestReasoning.proximity_level}</div>
                </div>
              )}
              {latestReasoning.wall_level && (
                <div style={{ flex: 1, background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '5px 8px' }}>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>WALL</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent-orange)' }}>{latestReasoning.wall_level} ({latestReasoning.wall_side})</div>
                </div>
              )}
            </div>
          )}

          {/* Narrative */}
          {displayed && (
            <div style={{
              background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '8px 10px',
              fontSize: 10, lineHeight: 1.65, color: 'var(--text-secondary)',
              borderLeft: '2px solid #9f7aea40',
              maxHeight: 100, overflowY: 'auto',
            }}>
              {displayed}
              <span style={{ animation: 'cursor-blink 1s infinite', color: '#9f7aea' }}>|</span>
            </div>
          )}
        </div>
      )}
    </AgentCard>
  )
}

// ── Step 2: Execution Card ─────────────────────────────────────────────────
function ExecutionAgentCard({ latestReasoning }) {
  const decision = latestReasoning?.decision?.toLowerCase()
  const isTrade = decision === 'trade'
  const direction = latestReasoning?.direction?.toLowerCase()
  const confidence = latestReasoning?.fabio_confidence || 0
  const entry = latestReasoning?.bar_close || null
  const reasoning = latestReasoning?.fabio_reasoning || ''
  const { displayed } = useTypingText(reasoning, isTrade && !!reasoning)

  const dirColor = direction === 'long' ? 'var(--accent-green)' : direction === 'short' ? 'var(--accent-red)' : 'var(--text-muted)'
  const accent = direction === 'long' ? '#48bb78' : direction === 'short' ? '#fc8181' : '#63b3ed'

  return (
    <AgentCard
      icon="⚡"
      title="STEP 2 — EXECUTION AGENT"
      subtitle="Entry · Stop · Target · R:R · Confidence"
      accent={accent}
      isActive={isTrade}
    >
      {!isTrade ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 11, textAlign: 'center', padding: '8px 0' }}>
          {latestReasoning ? (
            <span style={{ color: 'var(--accent-orange)', fontSize: 10 }}>⛔ No valid setup — {latestReasoning?.no_trade_reason?.slice(0, 60) || 'Setup non confermato'}</span>
          ) : (
            'In attesa di analisi...'
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Direction + Confidence */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <div style={{
              padding: '5px 12px', borderRadius: 8,
              background: `${accent}20`, border: `1px solid ${accent}40`,
              fontSize: 14, fontWeight: 800, color: dirColor, fontFamily: 'var(--font-mono)',
              letterSpacing: '0.04em',
            }}>
              {direction?.toUpperCase() || '---'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 3 }}>CONFIDENCE</div>
              <ConfidenceGauge value={confidence} />
            </div>
          </div>

          {/* Entry / Stop / Target */}
          {entry && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 5 }}>
              {[
                { label: 'ENTRY', value: entry?.toFixed(2), color: 'var(--text-primary)' },
                { label: 'STOP', value: latestReasoning?.stop?.toFixed?.(2) || '---', color: 'var(--accent-red)' },
                { label: 'TARGET', value: latestReasoning?.target?.toFixed?.(2) || '---', color: 'var(--accent-green)' },
              ].map(item => (
                <div key={item.label} style={{
                  background: 'rgba(0,0,0,0.25)', borderRadius: 7, padding: '6px 8px', textAlign: 'center',
                }}>
                  <div style={{ fontSize: 8, color: 'var(--text-muted)', marginBottom: 2 }}>{item.label}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: item.color }}>{item.value}</div>
                </div>
              ))}
            </div>
          )}

          {/* Reasoning snippet */}
          {displayed && (
            <div style={{
              background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '7px 9px',
              fontSize: 10, lineHeight: 1.6, color: 'var(--text-secondary)',
              borderLeft: `2px solid ${accent}60`,
              maxHeight: 90, overflowY: 'auto',
            }}>
              {displayed}
              <span style={{ animation: 'cursor-blink 1s infinite', color: accent }}>|</span>
            </div>
          )}
        </div>
      )}
    </AgentCard>
  )
}

// ── Active Trade Card ──────────────────────────────────────────────────────
function ActiveTradeCard({ openTrade, liveReasoning }) {
  if (!openTrade) return (
    <AgentCard icon="📊" title="POSIZIONE APERTA" subtitle="Nessun trade in corso" accent="#63b3ed" isActive={false}>
      <div style={{ color: 'var(--text-muted)', fontSize: 11, textAlign: 'center', padding: '8px 0' }}>
        Nessuna posizione aperta
      </div>
    </AgentCard>
  )

  const { direction, entry, stop, target, contracts } = openTrade
  const currentPrice = liveReasoning?.bar_close || entry
  const isLong = direction === 'long'
  const pnlPts = isLong ? currentPrice - entry : entry - currentPrice
  const risk = isLong ? entry - stop : stop - entry
  const reward = isLong ? target - entry : entry - target
  const rr = reward > 0 ? (reward / risk).toFixed(2) : '?'
  const rrCurrent = risk > 0 ? Math.abs(pnlPts / risk).toFixed(2) : '?'
  const pnlUsd = pnlPts * 20 * (contracts || 1)
  const pnlColor = pnlPts >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
  const progPct = Math.min(100, Math.max(0, (reward > 0 ? Math.abs(pnlPts) / reward * 100 : 0)))

  return (
    <AgentCard
      icon={isLong ? '🟩' : '🟥'}
      title="POSIZIONE APERTA"
      subtitle={`${direction?.toUpperCase()} · ${contracts} contracts`}
      accent={isLong ? '#48bb78' : '#fc8181'}
      isActive={true}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* P&L Big number */}
        <div style={{
          textAlign: 'center', padding: '10px 0',
          background: 'rgba(0,0,0,0.25)', borderRadius: 8,
          border: `1px solid ${pnlPts >= 0 ? 'rgba(72,187,120,0.25)' : 'rgba(252,129,129,0.2)'}`,
        }}>
          <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: 4 }}>P&L APERTO</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 800, color: pnlColor }}>
            {pnlPts >= 0 ? '+' : ''}{pnlPts.toFixed(2)} pt
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: pnlColor, opacity: 0.8 }}>
            {pnlUsd >= 0 ? '+' : ''}${pnlUsd.toFixed(0)} USD
          </div>
        </div>

        {/* Progress to target */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span>STOP {stop?.toFixed(2)}</span>
            <span>{progPct.toFixed(0)}% verso target</span>
            <span>TARGET {target?.toFixed(2)}</span>
          </div>
          <div style={{ height: 6, background: 'rgba(255,255,255,0.07)', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{
              width: `${progPct}%`, height: '100%',
              background: `linear-gradient(90deg, ${isLong ? '#48bb78' : '#fc8181'}, ${isLong ? '#9f7aea' : '#f6ad55'})`,
              borderRadius: 4, transition: 'width 1s ease',
              boxShadow: `0 0 8px ${isLong ? '#48bb7880' : '#fc818180'}`,
            }} />
          </div>
        </div>

        {/* Quick stats */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 5 }}>
          {[
            { label: 'ENTRY', value: entry?.toFixed(2) },
            { label: 'R:R TARGET', value: rr + 'R' },
            { label: 'R:R LIVE', value: rrCurrent + 'R', color: pnlPts >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' },
          ].map(item => (
            <div key={item.label} style={{
              background: 'rgba(0,0,0,0.2)', borderRadius: 6, padding: '5px 7px', textAlign: 'center',
            }}>
              <div style={{ fontSize: 8, color: 'var(--text-muted)', marginBottom: 1 }}>{item.label}</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: item.color || 'var(--text-primary)' }}>{item.value}</div>
            </div>
          ))}
        </div>
      </div>
    </AgentCard>
  )
}

// ── Recent Reasonings Timeline ─────────────────────────────────────────────
function ReasoningTimeline({ reasonings, onJump, timeZone }) {
  const recent = (reasonings || []).slice(-12).reverse()
  if (!recent.length) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>
        Ultimi ragionamenti
      </div>
      {recent.map((r, i) => {
        const isTrade = r.decision?.toLowerCase() === 'trade'
        const dir = r.direction?.toLowerCase()
        const time = r.bar_time_et || ''
        const conf = r.fabio_confidence || 0
        const color = dir === 'long' ? 'var(--accent-green)' : dir === 'short' ? 'var(--accent-red)' : 'var(--text-muted)'

        return (
          <div key={i}
            onClick={() => onJump?.(r)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 8px',
              borderRadius: 6,
              cursor: 'pointer',
              transition: 'background 0.15s',
              borderBottom: '1px solid rgba(255,255,255,0.04)',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: isTrade ? color : 'var(--text-muted)', flexShrink: 0 }} />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', minWidth: 38 }}>{time}</div>
            <div style={{ flex: 1, fontSize: 10, color: isTrade ? color : 'var(--text-muted)', fontWeight: isTrade ? 600 : 400 }}>
              {isTrade ? dir?.toUpperCase() : 'No trade'}
            </div>
            {isTrade && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: conf >= 70 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>{conf}%</div>}
          </div>
        )
      })}
    </div>
  )
}

// ── Main AgentSidebar ──────────────────────────────────────────────────────
export default function AgentSidebar({ latestReasoning, openTrade, reasonings, onJump, timeZone }) {
  const [tab, setTab] = useState('agents') // 'agents' | 'log' | 'trade'

  return (
    <div style={{
      width: 320,
      flexShrink: 0,
      background: 'var(--bg-base)',
      borderLeft: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      height: '100%',
    }}>
      {/* Tab switcher */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-surface)',
        flexShrink: 0,
      }}>
        {[
          { id: 'agents', label: '🤖 Agenti' },
          { id: 'trade', label: '📊 Trade' },
          { id: 'log', label: '📋 Log' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              flex: 1, padding: '9px 4px', fontSize: 10, fontWeight: 600,
              borderBottom: tab === t.id ? '2px solid var(--accent-blue)' : '2px solid transparent',
              color: tab === t.id ? 'var(--text-primary)' : 'var(--text-muted)',
              transition: 'all 0.15s',
              background: 'none', border: 'none',
              borderBottom: tab === t.id ? '2px solid var(--accent-blue)' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {tab === 'agents' && (
          <>
            {latestReasoning && (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: 'rgba(0,0,0,0.15)', border: '1px solid var(--border)',
                padding: '6px 10px', borderRadius: 8
              }}>
                <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
                  Analisi candela: <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)', marginLeft: 4 }}>{latestReasoning.bar_time_utc || latestReasoning.bar_time_et || '---'}</span>
                </div>
                <button
                  onClick={() => {
                    let nextR = { ...latestReasoning };
                    if (nextR.bar_time_utc) {
                      const tMs = new Date(nextR.bar_time_utc).getTime() + 60000;
                      nextR.bar_time_utc = new Date(tMs).toISOString();
                    } else if (nextR.bar_time_et) {
                      const parts = nextR.bar_time_et.split(':');
                      let m = parseInt(parts[1], 10) + 1;
                      let h = parseInt(parts[0], 10);
                      if (m >= 60) { m = 0; h += 1; }
                      nextR.bar_time_et = `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
                    }
                    onJump?.(nextR);
                  }}
                  style={{
                    background: 'rgba(99, 179, 237, 0.15)', color: 'var(--accent-blue)', border: '1px solid rgba(99, 179, 237, 0.3)',
                    padding: '4px 8px', borderRadius: 5, fontSize: 10, fontWeight: 700,
                    cursor: 'pointer', transition: 'background 0.2s'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'rgba(99, 179, 237, 0.25)'}
                  onMouseOut={e => e.currentTarget.style.background = 'rgba(99, 179, 237, 0.15)'}
                  title="Fai scorrere il grafico alla candela successiva (+1 minuto)"
                >
                  ⏭️ +1 Min
                </button>
              </div>
            )}
            <ContextAgentCard latestReasoning={latestReasoning} />
            <ExecutionAgentCard latestReasoning={latestReasoning} />
            <ActiveTradeCard openTrade={openTrade} liveReasoning={latestReasoning} />
          </>
        )}
        {tab === 'trade' && (
          <ActiveTradeCard openTrade={openTrade} liveReasoning={latestReasoning} />
        )}
        {tab === 'log' && (
          <ReasoningTimeline reasonings={reasonings} onJump={onJump} timeZone={timeZone} />
        )}
      </div>

      <style>{`
        @keyframes thinking-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.2; }
        }
        @keyframes cursor-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
