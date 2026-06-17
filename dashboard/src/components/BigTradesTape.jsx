import { useEffect, useState, useRef } from 'react'

export default function BigTradesTape({ bigTrades, currentTimeMs, timeZone }) {
  const containerRef = useRef(null)
  const [displayedTrades, setDisplayedTrades] = useState([])

  useEffect(() => {
    if (!bigTrades || !bigTrades.length) {
      setDisplayedTrades([])
      return
    }
    
    // Filter trades that happened before or exactly at the current chart time
    // If no currentTimeMs is provided, show the last 50
    const relevant = currentTimeMs 
      ? bigTrades.filter(bt => bt.time * 1000 <= currentTimeMs)
      : bigTrades

    // Get the most recent 20 big trades
    const recent = [...relevant].sort((a, b) => a.time - b.time).slice(-30)
    setDisplayedTrades(recent)
  }, [bigTrades, currentTimeMs])

  useEffect(() => {
    // Auto-scroll to right (latest)
    if (containerRef.current) {
      containerRef.current.scrollLeft = containerRef.current.scrollWidth
    }
  }, [displayedTrades])

  if (!displayedTrades.length) return null

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '4px 10px',
      background: '#0d1117',
      borderTop: '1px solid var(--border)',
      borderBottom: '1px solid var(--border)',
      height: 36,
      overflowX: 'hidden',
      flexShrink: 0
    }}>
      <div style={{
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '0.1em',
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 6
      }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-orange)', animation: 'pulse-dot 1.5s infinite' }} />
        TAPE
      </div>
      
      <div ref={containerRef} style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        overflowX: 'auto',
        flex: 1,
        scrollbarWidth: 'none', // Firefox
        msOverflowStyle: 'none' // IE 10+
      }}>
        {displayedTrades.map((bt, i) => {
          const isBuy = bt.side === 'buy'
          const color = isBuy ? 'var(--accent-green)' : 'var(--accent-red)'
          const bg = isBuy ? 'rgba(72,187,120,0.1)' : 'rgba(252,129,129,0.1)'
          const timeLabel = new Date(bt.time * 1000).toLocaleTimeString('en-US', {
            hour: '2-digit', minute: '2-digit', second: '2-digit',
            timeZone, hour12: false
          })

          return (
            <div key={`${bt.time}-${bt.price}-${i}`} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: bg,
              border: `1px solid ${color}40`,
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 11,
              flexShrink: 0,
              fontFamily: 'var(--font-mono)'
            }}>
              <span style={{ color: 'var(--text-muted)', fontSize: 9 }}>{timeLabel}</span>
              <span style={{ color, fontWeight: 800 }}>{bt.size}</span>
              <span style={{ color: 'var(--text-secondary)' }}>@</span>
              <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{bt.price.toFixed(2)}</span>
            </div>
          )
        })}
      </div>
      <style>{`
        /* Hide scrollbar for Chrome, Safari and Opera */
        div::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  )
}
