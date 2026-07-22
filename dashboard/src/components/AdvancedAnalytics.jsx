import React, { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell, AreaChart, Area, CartesianGrid, ReferenceLine } from 'recharts';

export default function AdvancedAnalytics({ trades = [], kpi = {} }) {
  const [hoveredPoint, setHoveredPoint] = useState(null);

  // 1. Process Trades chronologically to build Cumulative PnL & Drawdown
  const sortedTrades = useMemo(() => {
    return [...trades].sort((a, b) => new Date(a.entry_time) - new Date(b.entry_time));
  }, [trades]);

  const equityData = useMemo(() => {
    let running = 0;
    let peak = 0;
    const initialCapital = 50000;
    return sortedTrades.map((t, index) => {
      running += t.pnl_usd;
      if (running > peak) peak = running;
      const drawdownPct = ((peak - running) / initialCapital) * 100;
      return {
        tradeIndex: index + 1,
        date: t.date,
        pnl: t.pnl_usd,
        cumulative: running,
        drawdown: -drawdownPct,
        setup: t.setup_type || 'N/A',
        direction: t.direction,
        outcome: t.pnl_usd > 0 ? 'win' : 'loss'
      };
    });
  }, [sortedTrades]);

  // SVG dimensions
  const svgWidth = 800;
  const svgHeight = 280;
  const padding = { top: 20, right: 30, bottom: 40, left: 60 };

  const svgCoords = useMemo(() => {
    if (equityData.length === 0) return { pathD: '', areaD: '', points: [] };

    const minX = 0;
    const maxX = equityData.length;
    const yValues = equityData.map(d => d.cumulative);
    const minY = Math.min(0, ...yValues) * 1.15; // padding for negative drawdown
    const maxY = Math.max(100, ...yValues) * 1.15; // padding for profit peak

    const getX = (xVal) => padding.left + (xVal / maxX) * (svgWidth - padding.left - padding.right);
    const getY = (yVal) => {
      const scale = (svgHeight - padding.top - padding.bottom);
      const relativeVal = (yVal - minY) / (maxY - minY);
      return svgHeight - padding.bottom - relativeVal * scale;
    };

    const points = equityData.map((d) => ({
      x: getX(d.tradeIndex),
      y: getY(d.cumulative),
      data: d
    }));

    // Start path at zero equity
    const startX = getX(0);
    const startY = getY(0);

    let pathD = `M ${startX} ${startY}`;
    points.forEach(p => {
      pathD += ` L ${p.x} ${p.y}`;
    });

    const bottomY = getY(minY);
    const areaD = `${pathD} L ${points[points.length - 1].x} ${bottomY} L ${startX} ${bottomY} Z`;

    const zeroLineY = getY(0);

    return { pathD, areaD, points, zeroLineY, getX, getY };
  }, [equityData]);

  // 2. Monthly Performance Matrix
  const monthlyData = useMemo(() => {
    const months = {};
    sortedTrades.forEach(t => {
      const monthKey = t.date.substring(0, 7); // "YYYY-MM"
      if (!months[monthKey]) {
        months[monthKey] = { pnl: 0, trades: 0, wins: 0, losses: 0 };
      }
      months[monthKey].trades += 1;
      months[monthKey].pnl += t.pnl_usd;
      if (t.pnl_usd > 0) months[monthKey].wins += 1;
      else months[monthKey].losses += 1;
    });

    return Object.keys(months).sort().map(m => ({
      month: m,
      pnl: months[m].pnl,
      trades: months[m].trades,
      winRate: months[m].trades ? ((months[m].wins / months[m].trades) * 100).toFixed(1) : 0
    }));
  }, [sortedTrades]);

  // 3. Setup Metrics Breakdown
  const setupBreakdown = useMemo(() => {
    const stats = {};
    sortedTrades.forEach(t => {
      const sType = t.setup_type || 'N/A';
      if (!stats[sType]) {
        stats[sType] = { pnl: 0, trades: 0, wins: 0, losses: 0, grossWin: 0, grossLoss: 0 };
      }
      stats[sType].trades += 1;
      stats[sType].pnl += t.pnl_usd;
      if (t.pnl_usd > 0) {
        stats[sType].wins += 1;
        stats[sType].grossWin += t.pnl_usd;
      } else {
        stats[sType].losses += 1;
        stats[sType].grossLoss += Math.abs(t.pnl_usd);
      }
    });

    return Object.keys(stats).map(s => {
      const data = stats[s];
      const wr = data.trades ? (data.wins / data.trades) * 100 : 0;
      const pf = data.grossLoss > 0 ? (data.grossWin / data.grossLoss) : 99.9;
      const expectancy = data.trades ? (data.pnl / data.trades) : 0;
      return {
        name: s.toUpperCase().replace('_', ' '),
        pnl: data.pnl,
        trades: data.trades,
        winRate: wr.toFixed(1),
        profitFactor: pf.toFixed(2),
        expectancy: expectancy.toFixed(0)
      };
    });
  }, [sortedTrades]);

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '24px',
      background: 'var(--bg-void)',
      color: 'var(--text-primary)',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
      height: '100%'
    }}>
      
      {/* SECTION 1: Cumulative Equity Curve */}
      <div style={{
        background: 'var(--bg-base)',
        border: '1px solid var(--border)',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        position: 'relative'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)' }}>📈 Curva dell'Equity Interattiva (PnL Cumulativo)</h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: 'var(--text-muted)' }}>
              Tracciamento trade-by-trade del capitale. Passa il mouse sopra la linea per i dettagli del singolo trade.
            </p>
          </div>
          <div style={{
            fontSize: '12px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontFamily: 'var(--font-mono)'
          }}>
            Estensione Dati: {trades.length} Trades
          </div>
        </div>

        {equityData.length === 0 ? (
          <div style={{ height: svgHeight, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
            Nessun trade disponibile per visualizzare la curva dell'equity.
          </div>
        ) : (
          <div style={{ position: 'relative' }}>
            <svg 
              viewBox={`0 0 ${svgWidth} ${svgHeight}`} 
              style={{ width: '100%', height: 'auto', overflow: 'visible' }}
            >
              <defs>
                <linearGradient id="equity-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4299e1" stopOpacity="0.25"/>
                  <stop offset="100%" stopColor="#9f7aea" stopOpacity="0.0"/>
                </linearGradient>
              </defs>

              {/* Grid Lines Y */}
              {[0.25, 0.5, 0.75].map((ratio, i) => {
                const yVal = padding.top + ratio * (svgHeight - padding.top - padding.bottom);
                return (
                  <line 
                    key={i} 
                    x1={padding.left} 
                    y1={yVal} 
                    x2={svgWidth - padding.right} 
                    y2={yVal} 
                    stroke="var(--border)" 
                    strokeDasharray="4 4"
                    strokeWidth="0.5"
                  />
                );
              })}

              {/* Zero Line */}
              {svgCoords.zeroLineY >= padding.top && svgCoords.zeroLineY <= svgHeight - padding.bottom && (
                <line 
                  x1={padding.left} 
                  y1={svgCoords.zeroLineY} 
                  x2={svgWidth - padding.right} 
                  y2={svgCoords.zeroLineY} 
                  stroke="var(--accent-red)" 
                  strokeOpacity="0.4"
                  strokeWidth="1"
                />
              )}

              {/* Gradient Area under curve */}
              <path d={svgCoords.areaD} fill="url(#equity-grad)" />

              {/* Main Line */}
              <path 
                d={svgCoords.pathD} 
                fill="none" 
                stroke="url(#line-grad-color)" 
                strokeWidth="2.5" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
              />
              <linearGradient id="line-grad-color" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#63b3ed" />
                <stop offset="100%" stopColor="#b794f4" />
              </linearGradient>

              {/* Glowing dot for hovered point */}
              {hoveredPoint && (
                <>
                  <circle 
                    cx={hoveredPoint.x} 
                    cy={hoveredPoint.y} 
                    r="8" 
                    fill="var(--accent-blue)" 
                    opacity="0.3" 
                  />
                  <circle 
                    cx={hoveredPoint.x} 
                    cy={hoveredPoint.y} 
                    r="4" 
                    fill="white" 
                    stroke="var(--accent-blue)" 
                    strokeWidth="2" 
                  />
                  <line 
                    x1={hoveredPoint.x} 
                    y1={padding.top} 
                    x2={hoveredPoint.x} 
                    y2={svgHeight - padding.bottom} 
                    stroke="var(--accent-blue)" 
                    strokeOpacity="0.3" 
                    strokeDasharray="2 2"
                  />
                </>
              )}

              {/* Transparent columns for mouse interactions */}
              {svgCoords.points.map((p, idx) => {
                const barWidth = (svgWidth - padding.left - padding.right) / equityData.length;
                return (
                  <rect
                    key={idx}
                    x={p.x - barWidth / 2}
                    y={padding.top}
                    width={barWidth}
                    height={svgHeight - padding.top - padding.bottom}
                    fill="transparent"
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHoveredPoint(p)}
                    onMouseLeave={() => setHoveredPoint(null)}
                  />
                );
              })}
            </svg>

            {/* Hover Tooltip Overlay */}
            {hoveredPoint && (
              <div style={{
                position: 'absolute',
                top: hoveredPoint.y < 120 ? hoveredPoint.y + 20 : hoveredPoint.y - 120,
                left: hoveredPoint.x > svgWidth - 180 ? hoveredPoint.x - 170 : hoveredPoint.x + 10,
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '10px 12px',
                boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                fontSize: '11px',
                pointerEvents: 'none',
                zIndex: 100,
                width: '160px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 'bold' }}>Trade #{hoveredPoint.data.tradeIndex}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{hoveredPoint.data.date}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Setup:</span>
                  <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{hoveredPoint.data.setup.toUpperCase()}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Direzione:</span>
                  <span style={{ color: hoveredPoint.data.direction === 'long' ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 500 }}>
                    {hoveredPoint.data.direction.toUpperCase()}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>PnL Trade:</span>
                  <span style={{ color: hoveredPoint.data.pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 'bold' }}>
                    {hoveredPoint.data.pnl >= 0 ? '+' : ''}${hoveredPoint.data.pnl.toFixed(0)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: '4px', marginTop: '4px', fontWeight: 'bold' }}>
                  <span>Cumulativo:</span>
                  <span style={{ color: hoveredPoint.data.cumulative >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    ${hoveredPoint.data.cumulative.toFixed(0)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* SECTION 2: Advanced KPI Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        {[
          { label: 'Net P&L', value: `${kpi.totalPnL >= 0 ? '+' : ''}$${(kpi.totalPnL || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`, sub: `${kpi.totalTrades} Trade totali`, color: kpi.totalPnL >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', icon: '💵' },
          { label: 'Win Rate', value: `${(kpi.winRate || 0).toFixed(1)}%`, sub: `${kpi.wins} Wins / ${kpi.losses} Losses`, color: kpi.winRate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)', icon: '🎯' },
          { label: 'Profit Factor', value: (kpi.profitFactor || 0).toFixed(2), sub: 'Gross Profit / Gross Loss', color: kpi.profitFactor >= 1.5 ? 'var(--accent-green)' : 'var(--text-secondary)', icon: '⚖️' },
          { label: 'Expectancy', value: `$${(kpi.expectancy || 0).toFixed(0)}`, sub: 'Attesa per singolo trade', color: kpi.expectancy > 0 ? 'var(--accent-green)' : 'var(--accent-red)', icon: '🎲' },
          { label: 'Max Drawdown', value: `${(kpi.maxDrawdown || 0).toFixed(2)}%`, sub: 'Su conto simulato $50k', color: 'var(--accent-red)', icon: '📉' },
          { label: 'Max Streaks', value: `${kpi.maxWinStreak}W / ${kpi.maxLossStreak}L`, sub: 'Striscia consecutiva max', color: 'var(--accent-blue)', icon: '🔥' },
          { label: 'R:R Medio', value: (kpi.asimmetria || 0).toFixed(2), sub: 'Win Medio / Loss Medio', color: 'var(--text-primary)', icon: '📊' },
          { label: 'Giorni di Trading', value: kpi.totalDays || 0, sub: 'Giornate analizzate', color: 'var(--accent-purple)', icon: '📅' }
        ].map((c, i) => (
          <div key={i} style={{
            background: 'var(--bg-base)',
            border: '1px solid var(--border)',
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
            position: 'relative'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{c.label}</span>
              <span style={{ fontSize: '16px' }}>{c.icon}</span>
            </div>
            <div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: c.color, fontFamily: 'var(--font-mono)' }}>{c.value}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{c.sub}</div>
            </div>
          </div>
        ))}
      </div>

      {/* SECTION 3: Monthly Matrix, Monthly Chart & Setup Analysis */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        
        {/* Drawdown Chart */}
        <div style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '20px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
          gridColumn: '1 / -1'
        }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 700, borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
            🔻 Drawdown % (sul conto base 50k)
          </h4>
          <div style={{ height: '200px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-red)" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="var(--accent-red)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="tradeIndex" hide />
                <YAxis tick={{fill: 'var(--text-muted)', fontSize: 10}} tickFormatter={(val) => `${val}%`} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--accent-red)' }}
                  formatter={(value) => [`${value.toFixed(2)}%`, 'Drawdown']}
                  labelStyle={{ color: 'var(--text-muted)' }}
                  labelFormatter={(label) => `Trade #${label}`}
                />
                <Area type="monotone" dataKey="drawdown" stroke="var(--accent-red)" fillOpacity={1} fill="url(#colorDrawdown)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Monthly PnL Bar Chart */}
        <div style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '20px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
        }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 700, borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
            📊 P&L Mensile
          </h4>
          <div style={{ height: '250px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="month" tick={{fill: 'var(--text-muted)', fontSize: 11}} />
                <YAxis tick={{fill: 'var(--text-muted)', fontSize: 10}} tickFormatter={(val) => `$${val}`} />
                <RechartsTooltip 
                  cursor={{fill: 'var(--bg-elevated)'}}
                  contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: '8px' }}
                  formatter={(value) => [`$${value.toFixed(0)}`, 'Net P&L']}
                  labelStyle={{ color: 'var(--text-muted)' }}
                />
                <ReferenceLine y={0} stroke="var(--text-muted)" />
                <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                  {monthlyData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        
        {/* Monthly Table */}
        <div style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '20px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
        }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 700, borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
            📅 Performance Mensile Out-of-Sample
          </h4>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Mese</th>
                <th style={{ padding: '8px', textAlign: 'center' }}>Trades</th>
                <th style={{ padding: '8px', textAlign: 'center' }}>Win Rate</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>P&L Netto</th>
              </tr>
            </thead>
            <tbody>
              {monthlyData.map((m, i) => {
                const isProfit = m.pnl >= 0;
                return (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', height: '36px' }}>
                    <td style={{ padding: '8px', fontWeight: 600 }}>{m.month}</td>
                    <td style={{ padding: '8px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{m.trades}</td>
                    <td style={{ padding: '8px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{m.winRate}%</td>
                    <td style={{ 
                      padding: '8px', 
                      textAlign: 'right', 
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 'bold',
                      color: isProfit ? 'var(--accent-green)' : 'var(--accent-red)'
                    }}>
                      {isProfit ? '+' : ''}${m.pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                  </tr>
                );
              })}
              {monthlyData.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Nessun dato mensile registrato.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Setup Table */}
        <div style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '20px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
        }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 700, borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
            🎯 Edge statistico per Setup
          </h4>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Setup</th>
                <th style={{ padding: '8px', textAlign: 'center' }}>Trades</th>
                <th style={{ padding: '8px', textAlign: 'center' }}>Win Rate</th>
                <th style={{ padding: '8px', textAlign: 'center' }}>Profit Factor</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Expectancy</th>
              </tr>
            </thead>
            <tbody>
              {setupBreakdown.map((s, i) => {
                return (
                  <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', height: '36px' }}>
                    <td style={{ padding: '8px', fontWeight: 'bold', color: 'var(--accent-blue)' }}>{s.name}</td>
                    <td style={{ padding: '8px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{s.trades}</td>
                    <td style={{ padding: '8px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{s.winRate}%</td>
                    <td style={{ padding: '8px', textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{s.profitFactor}</td>
                    <td style={{ 
                      padding: '8px', 
                      textAlign: 'right', 
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 'bold',
                      color: parseInt(s.expectancy) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'
                    }}>
                      ${s.expectancy} / t
                    </td>
                  </tr>
                );
              })}
              {setupBreakdown.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Nessun dato relativo ai setup.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Historica Trade List */}
        <div style={{
          background: 'var(--bg-base)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '20px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
        }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '14px', fontWeight: 700, borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
            📜 Registro Trade (Tutti i trade)
          </h4>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', minWidth: '700px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '8px', textAlign: 'left' }}>#</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Data / Ora</th>
                  <th style={{ padding: '8px', textAlign: 'center' }}>Dir</th>
                  <th style={{ padding: '8px', textAlign: 'left' }}>Setup</th>
                  <th style={{ padding: '8px', textAlign: 'right' }}>Entry</th>
                  <th style={{ padding: '8px', textAlign: 'center' }}>Exit Reason</th>
                  <th style={{ padding: '8px', textAlign: 'right' }}>R</th>
                  <th style={{ padding: '8px', textAlign: 'right' }}>P&L Netto</th>
                </tr>
              </thead>
              <tbody>
                {sortedTrades.map((t, i) => {
                  const isProfit = t.pnl_usd >= 0;
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', height: '36px' }}>
                      <td style={{ padding: '8px', color: 'var(--text-muted)' }}>{i + 1}</td>
                      <td style={{ padding: '8px', fontFamily: 'var(--font-mono)' }}>{t.date} {new Date(t.entry_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</td>
                      <td style={{ padding: '8px', textAlign: 'center', fontWeight: 'bold', color: t.direction === 'long' ? 'var(--accent-green)' : 'var(--accent-red)' }}>{t.direction.toUpperCase()}</td>
                      <td style={{ padding: '8px', color: 'var(--accent-blue)' }}>{t.setup_type || 'N/A'}</td>
                      <td style={{ padding: '8px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{t.entry?.toFixed(2)}</td>
                      <td style={{ padding: '8px', textAlign: 'center', color: 'var(--text-muted)' }}>{t.exit_reason}</td>
                      <td style={{ padding: '8px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{t.r_ratio ? t.r_ratio.toFixed(2) : '-'}</td>
                      <td style={{ 
                        padding: '8px', 
                        textAlign: 'right', 
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 'bold',
                        color: isProfit ? 'var(--accent-green)' : 'var(--accent-red)'
                      }}>
                        {isProfit ? '+' : ''}${t.pnl_usd.toFixed(0)}
                      </td>
                    </tr>
                  );
                })}
                {sortedTrades.length === 0 && (
                  <tr>
                    <td colSpan="8" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      Nessun trade nel registro.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
