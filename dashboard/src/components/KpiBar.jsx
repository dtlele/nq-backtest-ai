import { MOCK_KPI } from '../data/mockData'

export default function KpiBar({ kpi = MOCK_KPI }) {
  const wr = kpi.winRate.toFixed(1)
  const pnl = kpi.totalPnL
  return (
    <div className="kpi-bar">
      <div className="kpi-card">
        <span className="kpi-label">Total P&amp;L</span>
        <span className={`kpi-value ${pnl >= 0 ? 'pos' : 'neg'}`}>
          {pnl >= 0 ? '+' : ''}${pnl.toFixed(0)}
        </span>
        <span className="kpi-sub">{kpi.totalTrades} trades · {kpi.totalDays} days</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">Win Rate</span>
        <span className="kpi-value blue">{wr}%</span>
        <span className="kpi-sub">{kpi.wins}W / {kpi.losses}L</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">Profit Factor</span>
        <span className="kpi-value pos">{kpi.profitFactor || 0}</span>
        <span className="kpi-sub">gross win / loss</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">Expectancy</span>
        <span className="kpi-value pos">${kpi.expectancy || 0}</span>
        <span className="kpi-sub">edge per trade</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">Max Drawdown</span>
        <span className="kpi-value neg">{kpi.maxDrawdown}%</span>
        <span className="kpi-sub">peak to trough</span>
      </div>
      <div className="kpi-card">
        <span className="kpi-label">NAV Alerts</span>
        <span className="kpi-value" style={{ color: 'var(--accent-purple)' }}>{kpi.navAlerts}</span>
        <span className="kpi-sub">{kpi.middayRejections} midday rejected</span>
      </div>
    </div>
  )
}
