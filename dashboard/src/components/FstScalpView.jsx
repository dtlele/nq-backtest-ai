import React, { useState, useEffect, useMemo } from 'react';
import Papa from 'papaparse';
import { 
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, BarChart, Bar, Cell, ReferenceLine, ZAxis 
} from 'recharts';
import { Settings2, TrendingUp, BarChart3, AlertCircle, Target, Activity } from 'lucide-react';

export default function FstScalpView() {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch the Masterclass filtered pattern CSV
    fetch('/api/output/fst_masterclass_zones_pattern_2025.csv')
      .then(r => r.text())
      .then(csvText => {
        Papa.parse(csvText, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
          complete: (results) => {
            const parsedTrades = results.data.map(t => ({
              ...t,
              id: `${t.date}-${t.time}`,
              risk_pts: Math.abs(t.entry - t.stop),
            }));
            setTrades(parsedTrades);
            setLoading(false);
          }
        });
      })
      .catch(err => {
        console.error("Error loading Pure 3-Bar Pattern data:", err);
        setLoading(false);
      });
  }, []);

  const kpis = useMemo(() => {
    if (!trades.length) return null;
    const total = trades.length;
    
    let uShapeCount = 0;
    let vShapeCount = 0;
    let totalSweep = 0;
    let totalIgn = 0;
    
    trades.forEach(t => {
      if (t.pattern === '3-Bar U-Shape') uShapeCount++;
      if (t.pattern === '2-Bar V-Shape') vShapeCount++;
      totalSweep += (t.sweep_bt || 0);
      totalIgn += (t.ign_bt || 0);
    });

    return { 
      total, 
      uShapeCount, 
      vShapeCount, 
      avgSweep: totalSweep / total, 
      avgIgn: totalIgn / total 
    };
  }, [trades]);

  const scatterData = useMemo(() => {
    return trades.map(t => ({
      x: t.ign_bt || 0,
      y: t.sweep_bt || 0,
      z: t.risk_pts, 
      pattern: t.pattern,
      name: `${t.date} ${t.time}`,
      direction: t.direction
    }));
  }, [trades]);

  const patternDistributionData = useMemo(() => {
    if (!kpis) return [];
    return [
      { name: '3-Bar U-Shape', count: kpis.uShapeCount },
      { name: '2-Bar V-Shape', count: kpis.vShapeCount }
    ];
  }, [kpis]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <Activity size={32} color="var(--accent-blue)" className="animate-pulse" />
          <span>Caricamento dati Pure Pattern...</span>
        </div>
      </div>
    );
  }

  if (!trades.length) {
    return <div style={{ padding: '40px', color: 'var(--text-muted)' }}>Nessun dato trovato per la strategia FST Scalp.</div>;
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '24px', background: 'var(--bg-void)', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* HEADER ROW */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '22px', fontWeight: 800, background: 'linear-gradient(90deg, #63b3ed, #9f7aea)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Target size={24} color="#63b3ed" /> Pure Pattern Analysis
          </h2>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-muted)', fontSize: '13px' }}>
            Analisi avanzata dell'Order Flow sui Pattern 2-Bar V-Shape e 3-Bar U-Shape.
          </p>
        </div>
        <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', padding: '8px 16px', borderRadius: '8px', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          Trade analizzati: <span style={{ color: 'var(--accent-blue)', fontWeight: 'bold' }}>{kpis.total}</span>
        </div>
      </div>

      {/* KPI CARDS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        {[
          { label: '3-Bar U-Shape', value: kpis.uShapeCount, icon: <Activity size={18} color="#9f7aea" />, trend: 'Trades' },
          { label: '2-Bar V-Shape', value: kpis.vShapeCount, icon: <TrendingUp size={18} color="#63b3ed" />, trend: 'Trades' },
          { label: 'Avg Sweep Size', value: `${kpis.avgSweep.toFixed(1)} ticks`, icon: <AlertCircle size={18} color="var(--accent-red)" />, trend: 'Volume Sweep' },
          { label: 'Avg Ignition Size', value: `${kpis.avgIgn.toFixed(1)} ticks`, icon: <Settings2 size={18} color="var(--accent-green)" />, trend: 'Volume Push' },
        ].map((k, i) => (
          <div key={i} style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '12px', padding: '16px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: '-10px', right: '-10px', opacity: 0.05, transform: 'scale(3)' }}>{k.icon}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {k.icon} {k.label}
            </div>
            <div style={{ fontSize: '24px', fontWeight: 800, fontFamily: 'var(--font-mono)', margin: '8px 0', color: 'var(--text-primary)' }}>
              {k.value}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{k.trend}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        
        {/* CHART: Sweep vs Ignition */}
        <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings2 size={16} /> Sweep Ticks vs Ignition Ticks
          </h3>
          <div style={{ width: '100%', height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis type="number" dataKey="x" name="Ignition Ticks" unit=" t" stroke="var(--text-muted)" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
                <YAxis type="number" dataKey="y" name="Sweep Ticks" unit=" t" stroke="var(--text-muted)" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
                <ZAxis type="number" dataKey="z" range={[40, 400]} name="Risk" />
                <RechartsTooltip 
                  cursor={{ strokeDasharray: '3 3', stroke: 'var(--text-secondary)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', padding: '12px', borderRadius: '8px', boxShadow: '0 4px 16px rgba(0,0,0,0.4)' }}>
                          <div style={{ fontWeight: 'bold', fontSize: '13px', marginBottom: '6px' }}>{d.name} ({d.direction})</div>
                          <div style={{ fontSize: '12px', color: '#9f7aea' }}>Pattern: {d.pattern}</div>
                          <div style={{ fontSize: '12px', color: 'var(--accent-red)' }}>Sweep Ticks: {d.y}</div>
                          <div style={{ fontSize: '12px', color: 'var(--accent-green)' }}>Ignition Ticks: {d.x}</div>
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Risk: {d.z.toFixed(2)} pts</div>
                        </div>
                      )
                    }
                    return null;
                  }}
                />
                <ReferenceLine y={0} stroke="var(--border)" />
                <ReferenceLine x={0} stroke="var(--border)" />
                <Scatter name="Trades" data={scatterData}>
                  {scatterData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.pattern === '3-Bar U-Shape' ? '#9f7aea' : '#63b3ed'} opacity={0.7} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* CHART: Pattern Distribution */}
        <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart3 size={16} /> Distribuzione Pattern
          </h3>
          <div style={{ width: '100%', height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={patternDistributionData} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" stroke="var(--text-muted)" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="name" width={100} stroke="var(--text-muted)" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', padding: '8px 12px', borderRadius: '6px' }}>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{payload[0].payload.name}</div>
                          <div style={{ fontSize: '13px', fontWeight: 'bold' }}>Trades: {payload[0].value}</div>
                        </div>
                      )
                    }
                    return null;
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {patternDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.name === '3-Bar U-Shape' ? '#9f7aea' : '#63b3ed'} opacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* RECENT TRADES LIST */}
      <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '15px' }}>Dettaglio Pattern estratti (Ultimi 30)</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '12px 8px', fontWeight: 600 }}>Data / Ora</th>
                <th style={{ padding: '12px 8px', fontWeight: 600 }}>Dir</th>
                <th style={{ padding: '12px 8px', fontWeight: 600 }}>Pattern</th>
                <th style={{ padding: '12px 8px', fontWeight: 600 }}>Entry</th>
                <th style={{ padding: '12px 8px', fontWeight: 600 }}>Stop</th>
                <th style={{ padding: '12px 8px', fontWeight: 600 }}>Sweep (Ticks)</th>
                <th style={{ padding: '12px 8px', fontWeight: 600 }}>Ignition (Ticks)</th>
              </tr>
            </thead>
            <tbody>
              {trades.slice(0, 30).map((t, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)', fontFamily: 'var(--font-mono)' }}>
                  <td style={{ padding: '10px 8px', color: 'var(--text-secondary)' }}>{t.date} {t.time}</td>
                  <td style={{ padding: '10px 8px', color: t.direction === 'LONG' ? 'var(--accent-green)' : 'var(--accent-red)' }}>{t.direction}</td>
                  <td style={{ padding: '10px 8px', color: t.pattern === '3-Bar U-Shape' ? '#9f7aea' : '#63b3ed' }}>{t.pattern}</td>
                  <td style={{ padding: '10px 8px', color: 'var(--text-primary)' }}>{t.entry}</td>
                  <td style={{ padding: '10px 8px', color: 'var(--text-primary)' }}>{t.stop}</td>
                  <td style={{ padding: '10px 8px', color: 'var(--accent-red)' }}>{t.sweep_bt}</td>
                  <td style={{ padding: '10px 8px', color: 'var(--accent-green)' }}>{t.ign_bt}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {trades.length > 30 && (
            <div style={{ textAlign: 'center', padding: '12px', color: 'var(--text-muted)', fontSize: '11px' }}>
              Visualizzando gli ultimi 30 trade (su {trades.length} totali)
            </div>
          )}
        </div>
      </div>
      
    </div>
  );
}
