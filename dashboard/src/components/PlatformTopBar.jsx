import { useState, useEffect } from 'react'

function useETClock() {
  const [time, setTime] = useState('')
  const [date, setDate] = useState('')
  useEffect(() => {
    const tick = () => {
      const now = new Date()
      setTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'America/New_York', hour12: false }))
      setDate(now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'America/New_York' }))
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])
  return { time, date }
}

export default function PlatformTopBar({ kpi, sessions, activeDate, onDateSelect, openTrade, liveReasoning, runFilter, onRunFilterChange, onOpenEdgeStats, activeTab, onSelectTab }) {
  const { time, date } = useETClock()
  const [prevPrice, setPrevPrice] = useState(null)
  const [priceDir, setPriceDir] = useState(null) // 'up' | 'down' | null
  const [flashKey, setFlashKey] = useState(0)

  // Simulate price ticking from latest reasoning
  const currentPrice = liveReasoning?.bar_close || openTrade?.entry || null
  useEffect(() => {
    if (currentPrice && prevPrice !== null && currentPrice !== prevPrice) {
      setPriceDir(currentPrice > prevPrice ? 'up' : 'down')
      setFlashKey(k => k + 1)
      const t = setTimeout(() => setPriceDir(null), 800)
      return () => clearTimeout(t)
    }
    setPrevPrice(currentPrice)
  }, [currentPrice])

  // Session totals
  const totalPnl = kpi?.totalPnL ?? 0
  const winRate = kpi?.winRate ?? 0
  const totalTrades = kpi?.totalTrades ?? 0
  const sharpe = kpi?.profitFactor ?? null
  const expectancy = kpi?.expectancy ?? null

  const isLive = openTrade != null
  const sessionLabel = activeDate || '---'

  return (
    <div style={{
      height: 48,
      background: 'var(--bg-base)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      gap: 0,
      flexShrink: 0,
      zIndex: 10,
    }}>
      {/* Logo */}
      <div style={{
        width: 190,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '0 14px',
        borderRight: '1px solid var(--border)',
        height: '100%',
      }}>
        <div style={{
          width: 30, height: 30,
          background: 'linear-gradient(135deg, #63b3ed, #9f7aea)',
          borderRadius: 8,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 15, flexShrink: 0,
          boxShadow: '0 0 12px rgba(99,179,237,0.4)',
        }}>⚡</div>
        <div>
          <div style={{ fontWeight: 800, fontSize: 12, letterSpacing: '0.04em', background: 'linear-gradient(90deg, #63b3ed, #9f7aea)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>NQ PREDATOR</div>
          <div style={{ fontSize: 8, color: '#63b3ed', fontWeight: 'bold', letterSpacing: '0.06em' }}>ALL OPTIMIZED SETUPS</div>
        </div>
      </div>

      {/* Instrument + Live Price */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '0 20px',
        borderRight: '1px solid var(--border)',
        height: '100%',
      }}>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>INSTRUMENT</div>
          <div style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>NQ · E-MINI</div>
        </div>
        {currentPrice && (
          <div key={flashKey} style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 20,
            fontWeight: 800,
            color: priceDir === 'up' ? 'var(--accent-green)' : priceDir === 'down' ? 'var(--accent-red)' : 'var(--text-primary)',
            transition: 'color 0.3s ease',
            minWidth: 90,
          }}>
            {currentPrice.toFixed(2)}
          </div>
        )}
      </div>

      {/* KPI strip */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 0,
        flex: 1, height: '100%',
        overflow: 'hidden',
      }}>
        {[
          { label: 'NET P&L', value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(0)}`, color: totalPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' },
          { label: 'WIN RATE', value: `${winRate.toFixed(1)}%`, color: winRate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)' },
          { label: 'TRADES', value: totalTrades, color: 'var(--accent-blue)' },
          sharpe != null ? { label: 'PROFIT FACTOR', value: sharpe.toFixed(2), color: sharpe >= 1.5 ? 'var(--accent-green)' : 'var(--text-secondary)' } : null,
          expectancy != null ? { label: 'EXPECTANCY', value: `$${expectancy.toFixed(0)}`, color: expectancy > 0 ? 'var(--accent-green)' : 'var(--accent-red)' } : null,
        ].filter(Boolean).map((item, i) => (
          <div key={i} style={{
            padding: '0 18px',
            borderRight: '1px solid var(--border)',
            height: '100%',
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
          }}>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.08em', fontWeight: 600 }}>{item.label}</div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: 'var(--font-mono)', color: item.color }}>{item.value}</div>
          </div>
        ))}

        <div style={{ display: 'flex', height: '100%', borderRight: '1px solid var(--border)', alignItems: 'center', padding: '0 12px', gap: '6px' }}>
          {[
            { id: 'chart', label: '📊 Grafico' },
            { id: 'analytics', label: '📈 Statistiche' },
            { id: 'playbook', label: '📘 Regole' },
            { id: 'fst_scalp', label: '⚡ FST Scalp' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => onSelectTab?.(tab.id)}
              style={{
                background: activeTab === tab.id ? 'var(--accent-blue-glow)' : 'transparent',
                border: activeTab === tab.id ? '1px solid var(--border-accent)' : '1px solid transparent',
                color: activeTab === tab.id ? 'var(--accent-blue)' : 'var(--text-secondary)',
                borderRadius: '4px',
                padding: '6px 12px',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Live session badge */}
        <div style={{
          padding: '0 18px',
          borderRight: '1px solid var(--border)',
          height: '100%',
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
        }}>
          <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.08em', fontWeight: 600 }}>SESSION</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            {isLive && <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-red)', boxShadow: '0 0 6px var(--accent-red)', flexShrink: 0, animation: 'pulse-dot 1.2s infinite' }} />}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600 }}>{sessionLabel}</span>
          </div>
        </div>
      </div>

      {/* ET Clock */}
      <div style={{
        padding: '0 20px',
        height: '100%',
        display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'flex-end',
        borderLeft: '1px solid var(--border)',
      }}>
        <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.08em', fontWeight: 600 }}>NEW YORK TIME</div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.04em' }}>{time}</div>
        <div style={{ fontSize: 9, color: 'var(--text-muted)' }}>{date}</div>
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  )
}
