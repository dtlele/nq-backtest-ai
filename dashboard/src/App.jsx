import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import PlatformTopBar from './components/PlatformTopBar'
import TradingChart from './components/TradingChart'
import TradePanel from './components/TradePanel'
import MacroContext from './components/MacroContext'
import AgentSidebar from './components/AgentSidebar'
import StrategyRules from './components/StrategyRules'
import EdgeStatsModal from './components/EdgeStatsModal'
import AdvancedAnalytics from './components/AdvancedAnalytics'
import PlaybookView from './components/PlaybookView'
import FstScalpView from './components/FstScalpView'
import './App.css'

export default function App() {
  const [dashboardData, setDashboardData] = useState({
    ALL_TRADES: [],
    ALL_PROPOSALS: [],
    ALL_REASONINGS: [],
    ANALYZED_DATES: [],
    OPEN_TRADE: null,
    LIVE_SESSION_STATE: {},
    LATEST_REASONING: {},
    MOCK_SESSIONS: [],
    MOCK_KPI: { totalTrades: 0, totalDays: 0, winRate: 0, totalPnL: 0, wins: 0, losses: 0, asimmetria: 0, maxDrawdown: 0, navAlerts: 0, middayRejections: 0 },
    KPI_VWAP_NAV: { totalTrades: 0, totalDays: 0, winRate: 0, totalPnL: 0, wins: 0, losses: 0, asimmetria: 0, maxDrawdown: 0, navAlerts: 0, middayRejections: 0 }
  })

  const [activeDate, setActiveDate] = useState('2025-01-07')
  const [activeTrade, setActiveTrade] = useState(null)
  const [userSelectedDate, setUserSelectedDate] = useState(false)
  const [activeReasoning, setActiveReasoning] = useState(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [runFilter, setRunFilter] = useState('all')
  const [jumpTimestamp, setJumpTimestamp] = useState(null)
  const [showStrategyRules, setShowStrategyRules] = useState(false)
  const [showEdgeStats, setShowEdgeStats] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [timeZone, setTimeZone] = useState('America/New_York')
  const [activeTab, setActiveTab] = useState('chart')

  // Polling data instead of Vite HMR
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('/data/status.json?t=' + Date.now())
        if (res.ok) {
          const data = await res.json()
          setDashboardData(data)
        }
      } catch (err) {
        console.error("Error fetching status.json", err)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 2000)
    return () => clearInterval(interval)
  }, [])

  // Auto-select date: solo al cambio reale di liveDate, e solo se l'utente non ha selezionato manualmente
  const prevLiveDateRef = useState(() => dashboardData.LIVE_SESSION_STATE?.date)[0]
  useEffect(() => {
    const availableDates = dashboardData.MOCK_SESSIONS.map(s => s.date)
    const liveDate = dashboardData.LIVE_SESSION_STATE?.date

    // Se la liveDate è cambiata (nuovo giorno di backtest), resetta la selezione manuale e segui
    if (liveDate && liveDate !== activeDate && !userSelectedDate) {
      setActiveDate(liveDate);
    }
    // Primo caricamento: se la data attiva non esiste ancora, prendi l'ultima disponibile
    else if (availableDates.length > 0 && !availableDates.includes(activeDate) && !liveDate && !userSelectedDate) {
      setActiveDate(availableDates[availableDates.length - 1])
    }
  }, [dashboardData.MOCK_SESSIONS, dashboardData.LIVE_SESSION_STATE?.date])

  const handleToggleTimeZone = () => {
    const localTZ = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Europe/Rome'
    setTimeZone(prev => prev === 'America/New_York' ? localTZ : 'America/New_York')
  }

  const handleSetActiveTrade = (t) => {
    setActiveTrade(t)
  }

  const allDayTrades = dashboardData.ALL_TRADES.filter(t => t.date === activeDate)
  const dayTrades = runFilter === 'all' ? allDayTrades : allDayTrades.filter(t => t.run === runFilter)
  const dayProposals = dashboardData.ALL_PROPOSALS.filter(p => p.date === activeDate)
  const dayReasonings = dashboardData.ALL_REASONINGS.filter(r => r.date === activeDate)
  const kpi = runFilter === 'vwap_nav' ? dashboardData.KPI_VWAP_NAV : dashboardData.MOCK_KPI
  const multiDayCtx = { trend: 'UP', volumeAvg: 12000, atr: 150 }

  return (
    <div className="platform-shell">
      {/* TOP BAR — full width */}
      <PlatformTopBar
        kpi={kpi}
        sessions={dashboardData.MOCK_SESSIONS}
        activeDate={activeDate}
        openTrade={dashboardData.OPEN_TRADE}
        liveReasoning={dashboardData.LATEST_REASONING}
        runFilter={runFilter}
        onRunFilterChange={setRunFilter}
        onOpenEdgeStats={() => setShowEdgeStats(true)}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      {/* MAIN CONTENT */}
      <div className="platform-body">
        {activeTab === 'chart' && (
          <>
            {/* LEFT — Session Navigator */}
            <Sidebar
              sessions={dashboardData.MOCK_SESSIONS}
              activeDate={activeDate}
              onSelect={(d) => { setActiveDate(d); setUserSelectedDate(true); handleSetActiveTrade(null) }}
              collapsed={sidebarCollapsed}
              onToggle={() => setSidebarCollapsed(c => !c)}
              onOpenStrategy={() => setShowStrategyRules(true)}
            />

            {/* CENTER — Chart Area */}
            <div className="platform-center">
              <MacroContext ctx={multiDayCtx} date={activeDate} trades={dayTrades} reasonings={dayReasonings} />
              <TradingChart
                key={`${activeDate}-${runFilter}-${timeZone}`}
                trades={dayTrades}
                proposals={dayProposals}
                reasonings={dayReasonings}
                date={activeDate}
                activeTrade={activeTrade}
                activeReasoning={activeReasoning}
                onTradeClick={handleSetActiveTrade}
                openTrade={dashboardData.OPEN_TRADE}
                latestReasoning={dashboardData.LATEST_REASONING}
                jumpTimestamp={jumpTimestamp}
                runFilter={runFilter}
                autoScroll={autoScroll}
                onAutoScrollChange={setAutoScroll}
                timeZone={timeZone}
                onToggleTimeZone={handleToggleTimeZone}
              />
            </div>

            {/* RIGHT — Agent Sidebar */}
            <AgentSidebar
              latestReasoning={dashboardData.LATEST_REASONING}
              openTrade={dashboardData.OPEN_TRADE}
              reasonings={dayReasonings}
              onJump={(r) => {
                setActiveReasoning(r)
                setJumpTimestamp(Date.now() + Math.random())
              }}
              timeZone={timeZone}
              dayTrades={dayTrades}
              dayProposals={dayProposals}
              activeTrade={activeTrade}
              onSelectTrade={handleSetActiveTrade}
              activeDate={activeDate}
            />
          </>
        )}

        {activeTab === 'analytics' && (
          <AdvancedAnalytics 
            trades={runFilter === 'all' ? dashboardData.ALL_TRADES : dashboardData.ALL_TRADES.filter(t => t.run === runFilter)} 
            kpi={kpi} 
          />
        )}

        {activeTab === 'playbook' && (
          <PlaybookView />
        )}

        {activeTab === 'fst_scalp' && (
          <FstScalpView />
        )}
      </div>

      {showStrategyRules && <StrategyRules onClose={() => setShowStrategyRules(false)} />}
      {showEdgeStats && <EdgeStatsModal onClose={() => setShowEdgeStats(false)} kpi={kpi} />}
    </div>
  )
}
