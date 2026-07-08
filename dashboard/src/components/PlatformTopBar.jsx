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

export default function PlatformTopBar({ kpi, sessions, activeDate, onDateSelect, openTrade, liveReasoning, runFilter, onRunFilterChange }) {
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

  // Session totals — use camelCase keys matching MOCK_KPI structure from App.jsx
  const totalPnl    = kpi?.totalPnL    ?? kpi?.total_pnl_usd ?? 0
  const rawWinRate  = kpi?.winRate     ?? kpi?.win_rate      ?? 0
  const totalTrades = kpi?.totalTrades ?? kpi?.total_trades  ?? 0
  const maxDD       = kpi?.maxDrawdown ?? null
  const asimmetria  = kpi?.asimmetria  ?? null
  const sharpe      = kpi?.sharpe      ?? null
  // winRate in MOCK_KPI is already 0–100; normalize if 0–1
  const winRate = rawWinRate > 1 ? rawWinRate / 100 : rawWinRate

  const isBacktest = runFilter && runFilter !== 'all'

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
          <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>TRADING PLATFORM</div>
        </div>
        <select 
          value={runFilter || 'all'}
          onChange={(e) => onRunFilterChange?.(e.target.value)}
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--text-primary)',
            fontSize: 11,
            padding: '4px 8px',
            borderRadius: 6,
            outline: 'none',
            cursor: 'pointer'
          }}
        >
          <option value="all">Live / All Trades</option>
          <option value="vwap_nav">Backtest: VWAP + NAV</option>
        </select>
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
        {/* Backtest mode badge */}
        {isBacktest && (
          <div style={{
            padding: '0 14px',
            borderRight: '1px solid var(--border)',
            height: '100%',
            display: 'flex', flexDirection: 'column', justifyContent: 'center',
            background: 'rgba(159,122,234,0.08)',
          }}>
            <div style={{ fontSize: 9, color: 'rgba(159,122,234,0.7)', letterSpacing: '0.08em', fontWeight: 700 }}>MODE</div>
            <div style={{
              fontSize: 10, fontWeight: 800, color: '#9f7aea',
              background: 'rgba(159,122,234,0.15)',
              border: '1px solid rgba(159,122,234,0.35)',
              borderRadius: 4, padding: '1px 6px', letterSpacing: '0.05em'
            }}>⚙ BACKTEST</div>
          </div>
        )}
        {[
          { label: 'NET P&L',   value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(0)}`, color: totalPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' },
          { label: 'WIN RATE',  value: `${(winRate * 100 > 1 ? winRate : winRate * 100).toFixed(0)}%`, color: winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)' },
          { label: 'TRADES',    value: totalTrades, color: 'var(--accent-blue)' },
          asimmetria != null ? { label: 'R:R ASIMM', value: asimmetria.toFixed(2), color: asimmetria >= 1.5 ? 'var(--accent-green)' : 'var(--text-secondary)' } : null,
          maxDD      != null ? { label: 'MAX DD',    value: `${maxDD.toFixed(1)}%`,   color: maxDD < 5 ? 'var(--accent-green)' : maxDD < 10 ? 'var(--accent-orange)' : 'var(--accent-red)' } : null,
          sharpe     != null ? { label: 'SHARPE',    value: sharpe.toFixed(2),         color: sharpe >= 1 ? 'var(--accent-green)' : 'var(--text-secondary)' } : null,
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
