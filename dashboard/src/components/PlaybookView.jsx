import React, { useState } from 'react';

export default function PlaybookView() {
  const [activeSection, setActiveSection] = useState('summary');

  const sections = [
    { id: 'summary', label: '📋 Riassunto Strategia', icon: '📝' },
    { id: 'time', label: '⏱️ Finestre Temporali', icon: '🕰️' },
    { id: 'setups', label: '📐 Parametri Setup 1 & 3', icon: '📏' },
    { id: 'filters', label: '🚫 Filtri & Big Trades', icon: '🛡️' },
    { id: 'live', label: '🤖 Architettura Bot Live', icon: '⚡' }
  ];

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      background: 'var(--bg-void)',
      color: 'var(--text-primary)',
      height: '100%',
      overflow: 'hidden'
    }}>
      {/* Playbook Sidebar Menu */}
      <div style={{
        width: '240px',
        background: 'var(--bg-base)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 8px',
        flexShrink: 0
      }}>
        <div style={{ padding: '0 12px 16px 12px', borderBottom: '1px solid var(--border)', marginBottom: '16px' }}>
          <h4 style={{ margin: 0, fontSize: '13px', letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Playbook Nav</h4>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>Regole e Logica Operativa</div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
          {sections.map(s => (
            <button
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '10px 12px',
                borderRadius: '6px',
                background: activeSection === s.id ? 'var(--accent-blue-glow)' : 'transparent',
                border: activeSection === s.id ? '1px solid var(--border-accent)' : '1px solid transparent',
                color: activeSection === s.id ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: activeSection === s.id ? 600 : 500,
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'all 0.15s'
              }}
            >
              <span>{s.icon}</span>
              <span>{s.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Playbook Content Area */}
      <div style={{
        flex: 1,
        padding: '24px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        
        {/* SUMMARY SECTION */}
        {activeSection === 'summary' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>📘 Manifesto Strategia "Agent Forge"</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', margin: '4px 0 0 0' }}>
                Panoramica dei principi cardine e della filosofia del trading algoritmico basato su flussi volumetrici.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  🧠 Approccio ad Agenti Concorrenti
                </h4>
                <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-secondary)', margin: 0 }}>
                  Il sistema sfrutta un doppio filtro decisionale. <strong>Fabio</strong> agisce da detector dei segnali analizzando
                  lo sviluppo dei nodi, l'orario e le distanze. <strong>Andrea</strong> funge da controllore strutturale e risk manager, 
                  avallando l'ordine solo se la confluenza volumetrica complessiva è favorevole.
                </p>
              </div>

              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 8px 0', color: 'var(--accent-purple)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  🧱 Edge Volumetrico (Order Book & Big Trades)
                </h4>
                <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-secondary)', margin: 0 }}>
                  Non utilizziamo oscillatori classici (RSI, MACD, etc.). La strategia si focalizza esclusivamente sulle tracce degli
                  operatori istituzionali (muri di contratti, transazioni anomale &gt; 30 contratti) in confluenza con i livelli strutturali
                  giornalieri (VWAP, VAH, VAL, POC) per identificare assorbimenti o accelerazioni.
                </p>
              </div>
            </div>

            <div style={{ background: 'rgba(99, 179, 237, 0.05)', border: '1px solid var(--accent-blue)', borderRadius: '8px', padding: '16px' }}>
              <h4 style={{ margin: '0 0 8px 0', color: 'var(--accent-blue)', fontSize: '13px' }}>🎯 Regole Fondamentali in Breve</h4>
              <ul style={{ fontSize: '12px', lineHeight: 1.6, margin: 0, paddingLeft: '20px', color: 'var(--text-secondary)' }}>
                <li><strong>No Overtrading:</strong> Massimo 1 o 2 operazioni al giorno. Se una posizione viene chiusa, non si cercano ulteriori setup.</li>
                <li><strong>Fine Sessione (EOD):</strong> Se un trade non tocca SL o TP entro le 16:00 ET (22:00 in Italia), la posizione viene liquidata d'ufficio a mercato.</li>
                <li><strong>Filtro Notizie:</strong> Nessun trade viene avviato nei 5 minuti che precedono rilasci macroeconomici di primo piano (CPI, NFP, decisioni FOMC).</li>
              </ul>
            </div>
          </div>
        )}

        {/* TIME WINDOWS SECTION */}
        {activeSection === 'time' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>⏱️ Finestre Temporali di Trading</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', margin: '4px 0 0 0' }}>
                Limitare il trading a orari ad alta liquidità e partecipazione istituzionale riduce i falsi segnali.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', borderLeft: '4px solid var(--accent-green)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, color: 'var(--accent-green)' }}>🌅 Sessione Mattutina (Morning Window)</h4>
                  <span style={{ fontSize: '11px', fontWeight: 'bold', fontFamily: 'var(--font-mono)', background: 'var(--accent-green-glow)', color: 'var(--accent-green)', padding: '2px 8px', borderRadius: '4px' }}>
                    09:30 - 11:00 ET (15:30 - 17:00 IT)
                  </span>
                </div>
                <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-secondary)', margin: 0 }}>
                  È la finestra principale di trading. La volatilità iniziale e l'apertura delle borse americane creano il momentum 
                  necessario per lo sviluppo e il break-out dei nostri setup volumetrici a 3 nodi. 
                  Nota: <i>Evitiamo i primi 5 minuti (09:30-09:35) per sfuggire al rumore iniziale incontrollato.</i>
                </p>
              </div>

              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', borderLeft: '4px solid var(--accent-blue)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0, color: 'var(--accent-blue)' }}>🌆 Sessione Pomeridiana (Midday Window)</h4>
                  <span style={{ fontSize: '11px', fontWeight: 'bold', fontFamily: 'var(--font-mono)', background: 'var(--accent-blue-glow)', color: 'var(--accent-blue)', padding: '2px 8px', borderRadius: '4px' }}>
                    12:30 - 13:30 ET (18:30 - 19:30 IT)
                  </span>
                </div>
                <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-secondary)', margin: 0 }}>
                  Finestra secondaria. Viene sfruttata solo per il <strong>Setup 3</strong> in giornate con un trend direzionale chiaro stabilitosi 
                  nella mattinata. Se i volumi della giornata sono eccezionalmente bassi, gli agenti ignorano questa finestra.
                </p>
              </div>

              <div style={{ background: 'rgba(239, 68, 68, 0.05)', border: '1px solid var(--accent-red)', borderRadius: '8px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 6px 0', color: 'var(--accent-red)', fontSize: '13px' }}>🚫 Divieto di Operazione Pomeridiano (Chop Zone)</h4>
                <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-secondary)', margin: 0 }}>
                  Nessun ordine può essere inviato tra le <strong>11:00 e le 12:30 ET</strong> (pausa pranzo a New York, i volumi calano drasticamente 
                  e il mercato tende a lateralizzare intrappolando i retail trader) e dopo le <strong>13:30 ET</strong> fino alla chiusura.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* SETUPS PARAMETERS SECTION */}
        {activeSection === 'setups' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>📐 Specifiche dei Setup 1 e 3</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', margin: '4px 0 0 0' }}>
                Confronto dei parametri di Take Profit (TP), Stop Loss (SL) e logica di ingresso per ciascuna configurazione.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              
              {/* Setup 1 Card */}
              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '10px', marginBottom: '12px' }}>
                  <h3 style={{ margin: 0, fontSize: '16px', color: 'var(--accent-blue)' }}>🔥 Setup 1: Volatility Expansion</h3>
                  <span style={{ fontSize: '10px', padding: '2px 6px', background: 'rgba(99,179,237,0.1)', color: 'var(--accent-blue)', borderRadius: '4px', fontWeight: 'bold' }}>AMPLITUDINE</span>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Target Profit (TP):</span>
                    <span style={{ fontWeight: 'bold', color: 'var(--accent-green)' }}>55 - 65 Punti</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Stop Loss (SL):</span>
                    <span style={{ fontWeight: 'bold', color: 'var(--accent-red)' }}>40 Punti</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Distanza Nodi:</span>
                    <span style={{ fontWeight: '500' }}>Ampia (&gt; 15 minuti)</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Rapporto R:R:</span>
                    <span style={{ fontWeight: 'bold' }}>~ 1.4x - 1.6x</span>
                  </div>
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '10px', marginTop: '4px', lineHeight: 1.4, color: 'var(--text-secondary)' }}>
                    Cerca una rottura direzionale decisa dopo una fase di accumulazione volumetrica ben definita. 
                    Richiede che tutti e 3 i nodi abbiano lo stesso sbilanciamento e che la distanza temporale tra i nodi indichi persistenza istituzionale.
                  </div>
                </div>
              </div>

              {/* Setup 3 Card */}
              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '10px', marginBottom: '12px' }}>
                  <h3 style={{ margin: 0, fontSize: '16px', color: 'var(--accent-purple)' }}>⚡ Setup 3: Micro-Range Breakout</h3>
                  <span style={{ fontSize: '10px', padding: '2px 6px', background: 'rgba(159,122,234,0.1)', color: 'var(--accent-purple)', borderRadius: '4px', fontWeight: 'bold' }}>STRETTO & VELOCE</span>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Target Profit (TP):</span>
                    <span style={{ fontWeight: 'bold', color: 'var(--accent-green)' }}>55 - 65 Punti</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Stop Loss (SL):</span>
                    <span style={{ fontWeight: 'bold', color: 'var(--accent-red)' }}>18 Punti</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Distanza Nodi:</span>
                    <span style={{ fontWeight: '500' }}>Stretta (&lt; 5 minuti)</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Rapporto R:R:</span>
                    <span style={{ fontWeight: 'bold' }}>~ 3.0x - 3.6x</span>
                  </div>
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '10px', marginTop: '4px', lineHeight: 1.4, color: 'var(--text-secondary)' }}>
                    Cerca compressioni rapide di prezzo e volume (nodi ravvicinati nel tempo e nello spazio). 
                    Lo stop molto stretto (18 punti) massimizza l'efficienza ma rende il setup sensibile allo slippage, 
                    motivo per cui si applica il filtro del Big Trade contrario in modo stringente.
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* FILTERS SECTION */}
        {activeSection === 'filters' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>🛡️ Filtri Volumetrici e Regole di Esclusione</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', margin: '4px 0 0 0' }}>
                I filtri determinano la qualità del trade escludendo contesti di mercato ostili o assorbimenti istituzionali contrari.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', borderLeft: '4px solid var(--accent-red)' }}>
                <h4 style={{ margin: '0 0 6px 0', color: 'var(--accent-red)' }}>🔴 Filtro Big Trade Contrario (Soglia &gt;= 150)</h4>
                <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-secondary)', margin: 0 }}>
                  Se durante lo sviluppo della sequenza (dallo Step 1 in poi) si registra sull'orderbook un **Big Trade contrario di taglia 
                  uguale o superiore a 150 contratti**, il trade viene bloccato. Questo indica assorbimento istituzionale del movimento 
                  e riduce drasticamente il win-rate del breakout.
                </p>
              </div>

              <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', borderLeft: '4px solid var(--accent-yellow)' }}>
                <h4 style={{ margin: '0 0 6px 0', color: 'var(--accent-yellow)' }}>🟡 Filtro Cumulative Volume Delta (CVD)</h4>
                <p style={{ fontSize: '12px', lineHeight: 1.5, color: 'var(--text-secondary)', margin: 0 }}>
                  Il Cumulative Delta della sessione al momento dell'ingresso deve essere inferiore a **1.200 contratti** (in valore assoluto).
                  Se il delta è eccessivamente sbilanciato in un senso, indica un mercato esteso che rischia inversioni repentine (exhaustion). 
                  Il bot preferisce mercati in cui la liquidità bid/ask è più bilanciata.
                </p>
              </div>
            </div>

            <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px' }}>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px' }}>🔍 Riepilogo Regole di Ingresso Quantitative</h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '6px' }}>Filtro</th>
                    <th style={{ padding: '6px' }}>Valore Soglia</th>
                    <th style={{ padding: '6px' }}>Azione in caso di Violazione</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '6px', fontWeight: 600 }}>Big Trade contrario</td>
                    <td style={{ padding: '6px', fontFamily: 'var(--font-mono)' }}>&gt;= 150 contratti</td>
                    <td style={{ padding: '6px', color: 'var(--accent-red)' }}>Blocco del segnale (Skippato)</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '6px', fontWeight: 600 }}>CVD Assoluto</td>
                    <td style={{ padding: '6px', fontFamily: 'var(--font-mono)' }}>&lt; 1200 contratti</td>
                    <td style={{ padding: '6px', color: 'var(--accent-red)' }}>Blocco del segnale (Skippato)</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '6px', fontWeight: 600 }}>Volume Barra (M5)</td>
                    <td style={{ padding: '6px', fontFamily: 'var(--font-mono)' }}>&gt;= 1500 contratti</td>
                    <td style={{ padding: '6px', color: 'var(--accent-red)' }}>Ignora la barra (Liquidità insufficiente)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* LIVE ARCHITECTURE SECTION */}
        {activeSection === 'live' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 800 }}>🤖 Architettura di Connessione al Mercato Reale (Live Bot)</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '12px', margin: '4px 0 0 0' }}>
                Come la pipeline del backtest viene tradotta in un sistema a eventi in tempo reale a bassissima latenza.
              </p>
            </div>

            <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: '8px', padding: '20px' }}>
              <h4 style={{ margin: '0 0 16px 0', color: 'var(--accent-purple)' }}>⚙️ Flusso ad Eventi (Pipeline Real-Time)</h4>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '12px' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ width: '24px', height: '24px', background: 'var(--accent-blue-glow)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', fontWeight: 'bold', flexShrink: 0 }}>1</div>
                  <div>
                    <strong style={{ color: 'var(--text-primary)' }}>Feed Dati real-time (Databento / IBKR WebSocket)</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-secondary)' }}>
                      Invece dei file CSV, il bot ascolta i singoli trade (tick-by-tick) via socket ad altissima velocità.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ width: '24px', height: '24px', background: 'var(--accent-blue-glow)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', fontWeight: 'bold', flexShrink: 0 }}>2</div>
                  <div>
                    <strong style={{ color: 'var(--text-primary)' }}>Aggregatore delle barre M1 & Stato CVD</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-secondary)' }}>
                      Un processo in background calcola la candela corrente, aggiornando dinamicamente il delta accumulato della giornata.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ width: '24px', height: '24px', background: 'var(--accent-blue-glow)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', fontWeight: 'bold', flexShrink: 0 }}>3</div>
                  <div>
                    <strong style={{ color: 'var(--text-primary)' }}>Verifica Regole & Filtro Contrario in tempo reale</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-secondary)' }}>
                      Ad ogni chiusura di candela a 1 minuto, la macchina a stati controlla se i 3 step sono completati e se ci sono stati Big Trades contrari nell'orderbook.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  <div style={{ width: '24px', height: '24px', background: 'var(--accent-blue-glow)', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', fontWeight: 'bold', flexShrink: 0 }}>4</div>
                  <div>
                    <strong style={{ color: 'var(--text-primary)' }}>Esecuzione Ordine OCO (Bracket Order) via MetaTrader 5</strong>
                    <p style={{ margin: '2px 0 0 0', color: 'var(--text-secondary)' }}>
                      Per proteggerci da problemi di latenza o rete, inviamo al server MT5 un ordine Bracket OCO (Entry + Stop Loss + Take Profit) 
                      simultaneamente. Il broker gestisce lo SL/TP a livello server, minimizzando il rischio di esecuzione.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ background: 'rgba(159,122,234,0.05)', border: '1px solid var(--accent-purple)', borderRadius: '8px', padding: '16px', fontSize: '11px', color: 'var(--text-secondary)' }}>
              ⚠️ <strong>Nota sulla Connessione Live</strong>: 
              L'API MetaTrader5 di Python richiede una piattaforma MT5 Windows in esecuzione sulla stessa macchina del bot per instradare gli ordini. 
              Il bot utilizzerà la libreria ufficiale `MetaTrader5` per scambiare ordini e monitorare lo stato del conto in demo/real.
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
