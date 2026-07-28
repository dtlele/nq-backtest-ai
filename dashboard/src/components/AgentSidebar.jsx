import { useState, useEffect, useRef } from 'react'
import TradePanel from './TradePanel'
import NarrativePanel from './NarrativePanel'

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
        padding: '12px 14px',
        background: isActive ? `${accent}10` : 'var(--bg-elevated)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span style={{ fontSize: 13 }}>{icon}</span>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.05em', color: isActive ? accent : 'var(--text-secondary)' }}>{title}</div>
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
      <div style={{ padding: '14px' }}>{children}</div>
    </div>
  )
}

// ── Step 1: Context Card ───────────────────────────────────────────────────
function ContextAgentCard({ latestReasoning, openTrade }) {
  const hasData = latestReasoning && latestReasoning.date

  const bias = latestReasoning?.bias || latestReasoning?.fabio_direction || latestReasoning?.direction || null
  const confidence = latestReasoning?.fabio_confidence || 0
  // FIX: when a trade is OPEN, the latest reasoning is apm_hold/apm_trail (not a proposal).
  // The 'no trade' panel should only show if there's no open trade AND the latest
  // reasoning is a rejected proposal.
  const hasOpenTrade = Boolean(openTrade && openTrade.entry)
  const isApmDecision = latestReasoning?.decision?.toLowerCase().startsWith('apm_')
  const isNoTrade = !hasOpenTrade && !isApmDecision && latestReasoning?.decision?.toLowerCase() !== 'trade'

  const trueBias = latestReasoning?.session_bias || 'none'
  const dayType = latestReasoning?.day_type || '---'
  const isThinking = !hasData

  const biasColor = bias === 'long' ? 'var(--accent-green)' : bias === 'short' ? 'var(--accent-red)' : 'var(--text-muted)'
  const biasLabel = bias ? bias.toUpperCase() : 'NEUTRAL'

  const trueBiasColor = trueBias === 'long' ? 'var(--accent-green)' : trueBias === 'short' ? 'var(--accent-red)' : 'var(--text-muted)'
  const trueBiasLabel = trueBias ? trueBias.toUpperCase() : 'NEUTRAL'

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
          {/* Bias + State + Phase row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10 }}>
            <div style={{
              flex: 1, minWidth: '28%', background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
              border: `1px solid ${biasColor}25`,
            }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>BIAS (FABIO)</div>
              <div style={{ fontSize: 13, fontWeight: 800, color: biasColor, fontFamily: 'var(--font-mono)' }}>{biasLabel}</div>
            </div>
            {trueBias && trueBias !== 'none' && (
              <div style={{
                flex: 1, minWidth: '28%', background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
                border: `1px solid ${trueBiasColor}40`,
              }}>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>TRUE BIAS (AMT)</div>
                <div style={{ fontSize: 13, fontWeight: 800, color: trueBiasColor, fontFamily: 'var(--font-mono)' }}>{trueBiasLabel}</div>
              </div>
            )}
            {latestReasoning?.fabio_imbalance_phase && latestReasoning.fabio_imbalance_phase !== 'none' && (
              <div style={{
                flex: 1, minWidth: '30%', background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
                border: latestReasoning.fabio_imbalance_phase === 'accumulation' ? '1px solid var(--accent-blue)' : '1px solid var(--accent-orange)'
              }}>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>PHASE</div>
                <div style={{ fontSize: 11, fontWeight: 800, color: latestReasoning.fabio_imbalance_phase === 'accumulation' ? 'var(--accent-blue)' : 'var(--accent-orange)', textTransform: 'uppercase' }}>
                  {latestReasoning.fabio_imbalance_phase}
                </div>
              </div>
            )}
            <div style={{
              flex: 1, minWidth: '30%', background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
            }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>DAY TYPE</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase' }}>{dayType}</div>
            </div>
            <div style={{
              flex: 1, minWidth: '30%', background: 'rgba(0,0,0,0.2)', borderRadius: 7, padding: '6px 10px',
            }}>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>STRUCTURE</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{latestReasoning?.market_structure || '---'}</div>
            </div>
          </div>

          <div style={{ height: 1, background: 'rgba(255,255,255,0.05)', margin: '4px 0' }} />
          
          <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
             <div style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>EXECUTION CONFIDENCE ⚡</div>
             <ConfidenceGauge value={confidence} />
             {isNoTrade && (
               <div style={{ color: 'var(--accent-red)', fontSize: 10, marginTop: 4, fontWeight: 600 }}>
                 ⛔ No valid setup — {latestReasoning?.no_trade_reason?.slice(0, 80) || `fabio_confidence=${confidence} < 70`}
               </div>
             )}
          </div>

        </div>
      )}
    </AgentCard>
  )
}


// ── Pre-Session Roadmap ────────────────────────────────────────────────────
function RoadmapCard({ latestReasoning }) {
  const roadmap = latestReasoning?.daily_roadmap;
  if (!roadmap || !roadmap.context_analysis) return null;
  
  const currentBias = latestReasoning?.bias || latestReasoning?.fabio_direction || latestReasoning?.direction || 'none';
  const isBullish = currentBias === 'long';
  const isBearish = currentBias === 'short';
  const isChop = currentBias === 'none';

  return (
    <AgentCard icon="🗺️" title="PRE-SESSION HYPOTHESES" subtitle="Roadmap Iniziale & Scenari" accent="#f56565" isActive={true}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10 }}>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '8px 10px', borderRadius: 6, fontSize: 11, color: 'var(--text-secondary)', fontStyle: 'italic', borderLeft: '2px solid #f56565' }}>
          {roadmap.context_analysis}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ padding: '8px 10px', borderRadius: 6, background: isBullish ? 'rgba(72,187,120,0.15)' : 'rgba(0,0,0,0.2)', border: isBullish ? '1px solid rgba(72,187,120,0.4)' : '1px solid transparent', transition: 'all 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent-green)', letterSpacing: '0.04em' }}>1. BULLISH SCENARIO</div>
              {isBullish && <div style={{ fontSize: 9, color: 'var(--accent-green)', fontWeight: 700, padding: '2px 6px', background: 'rgba(72,187,120,0.2)', borderRadius: 10 }}>PLAYING OUT</div>}
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--text-primary)', lineHeight: 1.4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Trigger:</span> {roadmap.bullish_scenario?.trigger_description}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>Target: {roadmap.bullish_scenario?.target_level}</div>
          </div>
          <div style={{ padding: '8px 10px', borderRadius: 6, background: isBearish ? 'rgba(245,101,101,0.15)' : 'rgba(0,0,0,0.2)', border: isBearish ? '1px solid rgba(245,101,101,0.4)' : '1px solid transparent', transition: 'all 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent-red)', letterSpacing: '0.04em' }}>2. BEARISH SCENARIO</div>
              {isBearish && <div style={{ fontSize: 9, color: 'var(--accent-red)', fontWeight: 700, padding: '2px 6px', background: 'rgba(245,101,101,0.2)', borderRadius: 10 }}>PLAYING OUT</div>}
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--text-primary)', lineHeight: 1.4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Trigger:</span> {roadmap.bearish_scenario?.trigger_description}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>Target: {roadmap.bearish_scenario?.target_level}</div>
          </div>
          <div style={{ padding: '8px 10px', borderRadius: 6, background: isChop ? 'rgba(237,137,54,0.15)' : 'rgba(0,0,0,0.2)', border: isChop ? '1px solid rgba(237,137,54,0.4)' : '1px solid transparent', transition: 'all 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent-orange)', letterSpacing: '0.04em' }}>3. CHOP SCENARIO</div>
              {isChop && <div style={{ fontSize: 9, color: 'var(--accent-orange)', fontWeight: 700, padding: '2px 6px', background: 'rgba(237,137,54,0.2)', borderRadius: 10 }}>PLAYING OUT</div>}
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--text-primary)', lineHeight: 1.4 }}>
              Range atteso tra <span style={{ fontFamily: 'var(--font-mono)' }}>{roadmap.chop_scenario?.range_low}</span> e <span style={{ fontFamily: 'var(--font-mono)' }}>{roadmap.chop_scenario?.range_high}</span>.
            </div>
          </div>
        </div>
      </div>
    </AgentCard>
  )
}

// ── Parsing Audit Scores ───────────────────────────────────────────────────
function parseAuditScores(reasoningText) {
  if (!reasoningText) return null;
  const match = reasoningText.match(/- Audit Fase Temporale:\s*([\s\S]*?)(?:- Note Classificazione Giornata:|-|$)/);
  if (!match) return null;
  const lines = match[1].trim().split('\n');
  const scores = lines.map(line => {
    const parts = line.split(':');
    if (parts.length === 2) {
       return { key: parts[0].trim(), value: parts[1].trim() };
    }
    return null;
  }).filter(Boolean);
  return scores.length ? scores : null;
}

// ── Audit & Full Reasoning Card ─────────────────────────────────────────────
function AuditAndReasoningCard({ latestReasoning }) {
  const reasoning = latestReasoning?.fabio_reasoning || '';
  const narrativeUpdate = latestReasoning?.market_narrative_update || '';
  const { displayed } = useTypingText(reasoning, !!reasoning);
  const { displayed: displayedNarrative } = useTypingText(narrativeUpdate, !!narrativeUpdate);
  const scores = parseAuditScores(reasoning);
  const hasData = !!latestReasoning?.date;

  return (
    <AgentCard
      icon="🎯"
      title="AUDIT & FULL REASONING"
      subtitle="Flusso logico dell'agente e validazioni temporali"
      accent="#f6ad55"
      isActive={hasData}
    >
      {!hasData ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 11, textAlign: 'center', padding: '8px 0' }}>
          Nessun ragionamento disponibile
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {scores && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, background: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 8 }}>
              {scores.map(s => {
                const valNum = parseInt(s.value);
                const color = valNum >= 80 ? 'var(--accent-green)' : valNum >= 50 ? 'var(--accent-orange)' : 'var(--accent-red)';
                const cleanKey = s.key.replace(/_score$/, '').replace(/^q\d+_/, '').replace(/_/g, ' ').toUpperCase();
                return (
                  <div key={s.key} style={{ display: 'flex', flexDirection: 'column', background: 'rgba(255,255,255,0.03)', padding: '4px 6px', borderRadius: 4, borderLeft: `2px solid ${color}` }}>
                     <div style={{ fontSize: 8, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{cleanKey}</div>
                     <div style={{ fontSize: 12, fontWeight: 800, color, fontFamily: 'var(--font-mono)' }}>{s.value}</div>
                  </div>
                )
              })}
            </div>
          )}

          {displayed && (
            <div style={{
              background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: '14px',
              fontSize: 11, lineHeight: 1.6, color: 'var(--text-primary)',
              borderLeft: `2px solid #f6ad55`,
              maxHeight: 'none',
              whiteSpace: 'pre-wrap',
            }}>
              {displayed}
              <span style={{ animation: 'cursor-blink 1s infinite', color: '#f6ad55' }}>|</span>
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
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 800, color: item.color || 'var(--text-primary)' }}>{item.value}</div>
            </div>
          ))}
        </div>

        {/* Active Trade Management reasoning */}
        {liveReasoning?.fabio_setup === 'apm' && liveReasoning?.fabio_reasoning && (
          <div style={{
            fontSize: 10, lineHeight: 1.5, padding: '8px 10px',
            background: 'rgba(255,255,255,0.03)', borderRadius: 6,
            borderLeft: '2px solid var(--accent-yellow)', marginTop: 4,
            textAlign: 'left'
          }}>
            <div style={{ fontWeight: 800, fontSize: 8, color: 'var(--text-muted)', marginBottom: 2, letterSpacing: '0.04em' }}>
              AGGIORNAMENTO GESTIONE (APM):
            </div>
            <div style={{ color: 'var(--text-primary)', fontStyle: 'italic' }}>
              "{liveReasoning.fabio_reasoning}"
            </div>
            {liveReasoning.decision && (
              <div style={{ fontSize: 9, fontWeight: 700, color: 'var(--accent-yellow)', marginTop: 4, textTransform: 'uppercase' }}>
                Azione: {liveReasoning.decision.replace('apm_', '')}
              </div>
            )}
          </div>
        )}
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

export default function AgentSidebar({ latestReasoning, openTrade, reasonings, onJump, timeZone, dayTrades = [], dayProposals = [], activeTrade, onSelectTrade, activeDate }) {
  const [tab, setTab] = useState('agents') // 'agents' | 'log' | 'trade'
  const [selectedTrade, setSelectedTrade] = useState(null)

  const prevOpenTradeTime = useRef(null)



  return (
    <div style={{
      width: 'clamp(420px, 35vw, 550px)',
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
          { id: 'pre_session', label: '🗺️ Schema Iniziale' },
          { id: 'agents', label: '🚀 Dashboard Live' },
          { id: 'narrative', label: '📖 Narrazione' },
          { id: 'trade', label: '💰 Trades' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              flex: 1, padding: '9px 2px', fontSize: 9.5, fontWeight: 600,
              borderBottom: tab === t.id ? '2px solid var(--accent-blue)' : '2px solid transparent',
              color: tab === t.id ? 'var(--text-primary)' : 'var(--text-muted)',
              transition: 'all 0.15s',
              background: 'none', border: 'none',
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
                    padding: '4px 8px', borderRadius: 5, fontSize: 11, fontWeight: 800,
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
            {openTrade && <ActiveTradeCard openTrade={openTrade} liveReasoning={latestReasoning} />}
            <ContextAgentCard latestReasoning={latestReasoning} openTrade={openTrade} />
            
            <AuditAndReasoningCard latestReasoning={latestReasoning} />
          </>
        )}
        {tab === 'pre_session' && (
          <RoadmapCard latestReasoning={latestReasoning} />
        )}
        {tab === 'narrative' && (
          <NarrativePanel reasonings={reasonings} onJump={onJump} timeZone={timeZone} />
        )}
        {tab === 'narrative' && (
          <NarrativePanel reasonings={reasonings} onJump={onJump} timeZone={timeZone} />
        )}
        {tab === 'trade' && (
          <TradePanel
            trade={activeTrade || openTrade}
            allTrades={dayTrades}
            proposals={dayProposals}
            onSelect={onSelectTrade}
            timeZone={timeZone}
          />
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
