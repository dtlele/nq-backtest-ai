export default function Sidebar({ sessions, activeDate, onSelect, collapsed, onToggle, onOpenStrategy }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon">⚡</div>
        {!collapsed && (
          <div>
            <div className="logo-text">Agent Forge</div>
            <div className="logo-sub">NQ Backtest</div>
          </div>
        )}
        <button className="collapse-btn" onClick={onToggle} title="Toggle sidebar">
          {collapsed ? '›' : '‹'}
        </button>
      </div>
      <div className="session-scroll">
        {!collapsed && <div className="session-label">Sessions</div>}
        {sessions.map(s => {
          const isProfit = s.pnl >= 0
          return (
            <button
              key={s.date}
              className={`session-item ${s.date === activeDate ? 'active' : ''}`}
              onClick={() => onSelect(s.date)}
              title={s.date}
            >
              <span className={`session-dot ${isProfit ? 'profit' : 'loss'}`} />
              {!collapsed && (
                <>
                  <div className="session-info">
                    <div className="session-date">{s.date}</div>
                    <div className="session-meta">{s.trades}T · {s.wins}W/{s.losses}L</div>
                  </div>
                  <span className={`session-pnl ${isProfit ? 'pos' : 'neg'}`}>
                    {isProfit ? '+' : ''}{s.pnl < 0 ? '-' : ''}${Math.abs(s.pnl)}
                  </span>
                </>
              )}
            </button>
          )
        })}
      </div>
      <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
        <button 
          onClick={onOpenStrategy}
          style={{
            width: '100%', background: 'var(--bg-glass)', border: '1px solid var(--border)',
            color: 'var(--text-primary)', padding: '10px', borderRadius: '6px',
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            transition: 'background 0.2s'
          }}
          onMouseOver={(e) => e.currentTarget.style.background = 'var(--bg-glass-hover)'}
          onMouseOut={(e) => e.currentTarget.style.background = 'var(--bg-glass)'}
        >
          📘 {!collapsed && <span>Regole Strategia</span>}
        </button>
      </div>
    </aside>
  )
}
