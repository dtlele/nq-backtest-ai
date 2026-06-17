import React, { useState } from 'react';
import { Terminal, Crosshair } from 'lucide-react';
import './RightPanel.css';

const MOCK_TRADES = [
  { id: 'T102', time: '14:30:00', type: 'LONG', price: 15120.50, pnl: '+$120.00' },
  { id: 'T101', time: '11:15:22', type: 'SHORT', price: 15080.25, pnl: '-$45.50' },
];

const MOCK_LOGS = [
  { time: '14:31:02', level: 'INFO', msg: 'Trailing stop moved to 15110.00' },
  { time: '14:30:00', level: 'TRADE', msg: 'Executed LONG at 15120.50' },
  { time: '14:29:55', level: 'SIGNAL', msg: 'Momentum divergence detected on 15M' },
  { time: '14:25:00', level: 'INFO', msg: 'Agent evaluating market conditions...' },
];

const RightPanel = () => {
  const [activeTab, setActiveTab] = useState('trades');

  return (
    <div className="right-panel glass-panel animate-fade-in" style={{ animationDelay: '0.3s' }}>
      <div className="panel-tabs">
        <button 
          className={`tab-btn ${activeTab === 'trades' ? 'active' : ''}`}
          onClick={() => setActiveTab('trades')}
        >
          <Crosshair size={16} />
          Trades
        </button>
        <button 
          className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <Terminal size={16} />
          APM Logs
        </button>
      </div>

      <div className="panel-content">
        {activeTab === 'trades' && (
          <div className="trades-view">
            <h4 className="view-title">Recent Executions</h4>
            <div className="trade-list">
              {MOCK_TRADES.map(trade => (
                <div key={trade.id} className="trade-card">
                  <div className="trade-header">
                    <span className={`trade-type ${trade.type.toLowerCase()}`}>{trade.type}</span>
                    <span className="trade-time">{trade.time}</span>
                  </div>
                  <div className="trade-details">
                    <span className="trade-price">@{trade.price.toFixed(2)}</span>
                    <span className={`trade-pnl ${trade.pnl.startsWith('+') ? 'profit' : 'loss'}`}>
                      {trade.pnl}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="logs-view">
            <div className="log-container">
              {MOCK_LOGS.map((log, i) => (
                <div key={i} className={`log-entry ${log.level.toLowerCase()}`}>
                  <span className="log-time">[{log.time}]</span>
                  <span className="log-level">{log.level}</span>
                  <span className="log-msg">{log.msg}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RightPanel;
