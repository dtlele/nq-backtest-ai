import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';
import './MainChart.css';

const MainChart = () => {
  const chartContainerRef = useRef();
  const chartRef = useRef();

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Initialize chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: 'rgba(255, 255, 255, 0.7)',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      crosshair: {
        mode: 0,
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
    });

    chartRef.current = chart;

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    // Mock Data
    const mockData = [];
    let time = Math.floor(Date.now() / 1000) - 86400 * 30; // 30 days ago
    let lastClose = 15000;

    for (let i = 0; i < 100; i++) {
      const open = lastClose + (Math.random() - 0.5) * 50;
      const close = open + (Math.random() - 0.5) * 100;
      const high = Math.max(open, close) + Math.random() * 50;
      const low = Math.min(open, close) - Math.random() * 50;
      
      mockData.push({ time, open, high, low, close });
      
      lastClose = close;
      time += 86400; // next day
    }

    candlestickSeries.setData(mockData);

    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);
    
    // Initial resize
    setTimeout(handleResize, 0);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  return (
    <div className="main-chart-wrapper glass-panel animate-fade-in" style={{ animationDelay: '0.2s' }}>
      <div className="chart-header">
        <div className="asset-info">
          <h3>NQ1!</h3>
          <span className="asset-desc">Nasdaq 100 E-mini</span>
        </div>
        <div className="chart-controls">
          <button className="timeframe-btn">1M</button>
          <button className="timeframe-btn">5M</button>
          <button className="timeframe-btn active">15M</button>
          <button className="timeframe-btn">1H</button>
          <button className="timeframe-btn">4H</button>
          <button className="timeframe-btn">D</button>
        </div>
      </div>
      <div className="chart-container" ref={chartContainerRef}></div>
    </div>
  );
};

export default MainChart;
