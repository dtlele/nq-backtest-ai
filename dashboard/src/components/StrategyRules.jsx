import React, { useState } from 'react';

export default function StrategyRules({ onClose }) {
  const [activeTab, setActiveTab] = useState('rules');

  const tabs = [
    { id: 'rules', label: 'Cosa Seguiamo' },
    { id: 'avoid', label: 'Cosa NON Seguiamo' },
    { id: 'proscons', label: 'Vantaggi & Dubbi' },
    { id: 'stats', label: 'Dati Statistici' }
  ];

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)'
    }}>
      <div style={{
        background: 'var(--bg-elevated)', width: '800px', maxWidth: '90%', maxHeight: '85vh',
        borderRadius: '12px', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 40px rgba(0,0,0,0.4)', overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ margin: 0, fontSize: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
            📘 Manifesto Strategia "Agent Forge"
          </h2>
          <button onClick={onClose} style={{
            background: 'transparent', border: 'none', color: 'var(--text-muted)', fontSize: 20, cursor: 'pointer'
          }}>✕</button>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', padding: '0 24px' }}>
          {tabs.map(t => (
            <div 
              key={t.id} 
              onClick={() => setActiveTab(t.id)}
              style={{
                padding: '12px 16px', cursor: 'pointer', fontWeight: activeTab === t.id ? 'bold' : 'normal',
                color: activeTab === t.id ? 'var(--accent-blue)' : 'var(--text-muted)',
                borderBottom: activeTab === t.id ? '2px solid var(--accent-blue)' : '2px solid transparent'
              }}
            >
              {t.label}
            </div>
          ))}
        </div>

        {/* Content */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {activeTab === 'rules' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="detail-section">
                <div className="detail-section-header">⏱ Orari & Giorni (Master V3 - V2 Caso A)</div>
                <div className="detail-section-body">Usiamo i filtri "V2 Caso A" per mappare le sessioni orarie e giornaliere valide (evitando i giorni/orari peggiori per limitare il drawdown).</div>
              </div>
              <div className="detail-section">
                <div className="detail-section-header">💰 Position Sizing</div>
                <div className="detail-section-body">Il size standard è di 25 Micro NQ per minimizzare il rischio di rovina (2%).</div>
              </div>
              <div className="detail-section">
                <div className="detail-section-header">🔍 Filtri Operativi</div>
                <div className="detail-section-body">Applicati rigorosamente: Buildup di 10 minuti, Estensione di 30 minuti, e Ritardo Short di 1 minuto per le inversioni.</div>
              </div>
              <div className="detail-section">
                <div className="detail-section-header">🧠 Doppio Consenso (Fabio + Andrea)</div>
                <div className="detail-section-body">Fabio cerca il setup (confidenza min: 75%). Andrea fa da garante strutturale.</div>
              </div>
              <div className="detail-section">
                <div className="detail-section-header">🧱 Tracce Istituzionali (NAV & VWAP)</div>
                <div className="detail-section-body">Ricerca di "muri" nell'orderbook con un threshold minimo di 30 contratti.</div>
              </div>
            </div>
          )}

          {activeTab === 'avoid' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="detail-section" style={{ borderLeftColor: 'var(--accent-red)' }}>
                <div className="detail-section-header" style={{ color: 'var(--accent-red)' }}>🚫 No Overtrading Pomeridiano</div>
                <div className="detail-section-body">Nessun trade dopo le 12:30 ET (chiusura anticipata) per evitare chop market e finte rotture pomeridiane.</div>
              </div>
              <div className="detail-section" style={{ borderLeftColor: 'var(--accent-red)' }}>
                <div className="detail-section-header" style={{ color: 'var(--accent-red)' }}>🚫 No Indicatori Lagging</div>
                <div className="detail-section-body">Non usiamo RSI, MACD o medie mobili classiche. L'unica media ampiamente utilizzata è il VWAP cumulativo istituzionale.</div>
              </div>
              <div className="detail-section" style={{ borderLeftColor: 'var(--accent-red)' }}>
                <div className="detail-section-header" style={{ color: 'var(--accent-red)' }}>🚫 Assenza di "Big Players"</div>
                <div className="detail-section-body">Se i delta sono bassi o assenti i muri nell'orderbook, gli agenti skippano la barra automaticamente.</div>
              </div>
            </div>
          )}

          {activeTab === 'proscons' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <h3 style={{ color: 'var(--accent-green)', margin: '0 0 8px 0' }}>Vantaggi (Pros)</h3>
              <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--text-secondary)' }}>
                <li style={{ marginBottom: 8 }}><strong>Filtro Emotivo Assoluto:</strong> La rigidità del doppio agente (Fabio + Andrea) garantisce ingressi solo su Setup "A+".</li>
                <li><strong>Difesa Intrinseca:</strong> Lo stop loss dinamico basato sui blocchi reali dell'orderbook (buffer di 4 ticks) evita le classiche caccie agli stop.</li>
              </ul>
              
              <h3 style={{ color: 'var(--accent-yellow)', margin: '16px 0 8px 0' }}>Dubbi / Punti Aperti (Cons)</h3>
              <div style={{ background: 'rgba(255, 171, 0, 0.1)', border: '1px solid var(--accent-yellow)', padding: 16, borderRadius: 8, color: 'var(--accent-yellow)' }}>
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li style={{ marginBottom: 8 }}><strong>News ad Alto Impatto:</strong> Come vogliamo gestire i trade 5 minuti prima di rilasci come CPI o NFP? Il sistema ha una `news_flag` ma non disattiva Fabio.</li>
                  <li><strong>Take Profit Fissi vs Trailing:</strong> L'agente usa RR fissi o target strutturali. In giornate in forte trend potremmo star lasciando profitti sul tavolo?</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'stats' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 16 }}>
              <div style={{ fontSize: 40 }}>📈</div>
              <div style={{ fontSize: 18, color: 'var(--text-secondary)' }}>Performance Master V3 (25 Micro NQ)</div>
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', maxWidth: 400 }}>
                <strong>Profitto Reale:</strong> $15.280<br/>
                <strong>Max Drawdown:</strong> $1.535<br/>
                <strong>Rischio Rovina:</strong> 2%
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
