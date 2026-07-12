import React from 'react';

export default function EdgeStatsModal({ onClose, kpi }) {
  const edgeKpis = kpi?.edgeKpis || {};
  const setups = Object.keys(edgeKpis).sort((a, b) => edgeKpis[b].expectancy - edgeKpis[a].expectancy);

  return (
    <div className="drawing-modal-overlay animate-fade-in" onClick={onClose} style={{ zIndex: 10000 }}>
      <div className="drawing-modal-content" onClick={e => e.stopPropagation()} style={{ width: '800px', maxWidth: '90vw', maxHeight: '80vh', overflowY: 'auto' }}>
        <div className="drawing-modal-header">
          <h3>Edge Analytics (Per Setup)</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="drawing-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', background: 'var(--bg-elevated)', padding: '15px', borderRadius: '8px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Max Consecutive Wins</div>
              <div style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--accent-green)' }}>{kpi?.maxWinStreak || 0}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Max Consecutive Losses</div>
              <div style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--accent-red)' }}>{kpi?.maxLossStreak || 0}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Global Profit Factor</div>
              <div style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--text-primary)' }}>{kpi?.profitFactor || 0}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Global Expectancy</div>
              <div style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--text-primary)' }}>${kpi?.expectancy || 0} / trade</div>
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '10px' }}>Setup (Edge)</th>
                <th style={{ padding: '10px' }}>Trades</th>
                <th style={{ padding: '10px' }}>Win Rate</th>
                <th style={{ padding: '10px' }}>P&L</th>
                <th style={{ padding: '10px' }}>Profit Factor</th>
                <th style={{ padding: '10px' }}>Expectancy</th>
              </tr>
            </thead>
            <tbody>
              {setups.map(s => {
                const data = edgeKpis[s];
                return (
                  <tr key={s} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '10px', fontWeight: 'bold', color: 'var(--accent-blue)' }}>{s.toUpperCase()}</td>
                    <td style={{ padding: '10px' }}>{data.totalTrades}</td>
                    <td style={{ padding: '10px', color: data.winRate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)' }}>{data.winRate}%</td>
                    <td style={{ padding: '10px', color: data.totalPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>${data.totalPnL.toFixed(0)}</td>
                    <td style={{ padding: '10px' }}>{data.profitFactor}</td>
                    <td style={{ padding: '10px', color: data.expectancy > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>${data.expectancy}</td>
                  </tr>
                );
              })}
              {setups.length === 0 && (
                <tr><td colSpan="6" style={{ padding: '10px', textAlign: 'center', color: 'var(--text-muted)' }}>No setup data available.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
