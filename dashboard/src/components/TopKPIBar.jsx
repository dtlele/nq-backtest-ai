import React from 'react';
import { Activity, TrendingUp, DollarSign, Percent } from 'lucide-react';
import './TopKPIBar.css';

const TopKPIBar = () => {
  return (
    <div className="top-kpi-bar glass-panel animate-fade-in">
      <div className="logo-section">
        <Activity className="logo-icon" size={28} />
        <h2>Agent Forge</h2>
      </div>
      
      <div className="kpi-container">
        <div className="kpi-card">
          <div className="kpi-icon-wrapper win">
            <TrendingUp size={20} />
          </div>
          <div className="kpi-data">
            <span className="kpi-label">Win Rate</span>
            <span className="kpi-value">{kpi?.winRate?.toFixed(1) || '0.0'}%</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrapper profit">
            <DollarSign size={20} />
          </div>
          <div className="kpi-data">
            <span className="kpi-label">Total PnL</span>
            <span className={`kpi-value ${kpi?.totalPnL >= 0 ? 'profit-value' : 'drawdown-value'}`}>
              {kpi?.totalPnL >= 0 ? '+' : ''}${kpi?.totalPnL?.toFixed(2) || '0.00'}
            </span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrapper drawdown">
            <Percent size={20} />
          </div>
          <div className="kpi-data">
            <span className="kpi-label">Max Drawdown</span>
            <span className="kpi-value drawdown-value">
              -{kpi?.maxDrawdown?.toFixed(1) || '0.0'}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TopKPIBar;
