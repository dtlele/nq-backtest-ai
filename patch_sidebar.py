import os

file_path = "dashboard/src/components/AgentSidebar.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Imports
content = content.replace(
    "import TradePanel from './TradePanel'",
    "import TradePanel from './TradePanel'\nimport NarrativePanel from './NarrativePanel'"
)

# 2. RoadmapCard definition
roadmap_card = """
// ── Pre-Session Roadmap ────────────────────────────────────────────────────
function RoadmapCard({ latestReasoning }) {
  const roadmap = latestReasoning?.daily_roadmap;
  if (!roadmap || !roadmap.context_analysis) return null;
  
  const currentBias = latestReasoning?.bias || latestReasoning?.fabio_direction || latestReasoning?.direction || 'none';
  const isBullish = currentBias === 'long';
  const isBearish = currentBias === 'short';
  const isChop = currentBias === 'none';

  return (
    <AgentCard icon="🗺️" title="PRE-SESSION HYPOTHESES" subtitle="Roadmap Iniziale & Scenari" accent="#f56565" isActive={true}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '8px 10px', borderRadius: 6, fontSize: 11, color: 'var(--text-secondary)', fontStyle: 'italic', borderLeft: '2px solid #f56565' }}>
          {roadmap.context_analysis}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ padding: '8px 10px', borderRadius: 6, background: isBullish ? 'rgba(72,187,120,0.15)' : 'rgba(0,0,0,0.2)', border: isBullish ? '1px solid rgba(72,187,120,0.4)' : '1px solid transparent', transition: 'all 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent-green)', letterSpacing: '0.04em' }}>1. BULLISH SCENARIO</div>
              {isBullish && <div style={{ fontSize: 9, color: 'var(--accent-green)', fontWeight: 700, padding: '2px 6px', background: 'rgba(72,187,120,0.2)', borderRadius: 10 }}>PLAYING OUT</div>}
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--text-primary)', lineHeight: 1.4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Trigger:</span> {roadmap.bullish_scenario?.trigger_description}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>Target: {roadmap.bullish_scenario?.target_level}</div>
          </div>
          <div style={{ padding: '8px 10px', borderRadius: 6, background: isBearish ? 'rgba(245,101,101,0.15)' : 'rgba(0,0,0,0.2)', border: isBearish ? '1px solid rgba(245,101,101,0.4)' : '1px solid transparent', transition: 'all 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent-red)', letterSpacing: '0.04em' }}>2. BEARISH SCENARIO</div>
              {isBearish && <div style={{ fontSize: 9, color: 'var(--accent-red)', fontWeight: 700, padding: '2px 6px', background: 'rgba(245,101,101,0.2)', borderRadius: 10 }}>PLAYING OUT</div>}
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--text-primary)', lineHeight: 1.4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Trigger:</span> {roadmap.bearish_scenario?.trigger_description}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>Target: {roadmap.bearish_scenario?.target_level}</div>
          </div>
          <div style={{ padding: '8px 10px', borderRadius: 6, background: isChop ? 'rgba(237,137,54,0.15)' : 'rgba(0,0,0,0.2)', border: isChop ? '1px solid rgba(237,137,54,0.4)' : '1px solid transparent', transition: 'all 0.3s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: 'var(--accent-orange)', letterSpacing: '0.04em' }}>3. CHOP SCENARIO</div>
              {isChop && <div style={{ fontSize: 9, color: 'var(--accent-orange)', fontWeight: 700, padding: '2px 6px', background: 'rgba(237,137,54,0.2)', borderRadius: 10 }}>PLAYING OUT</div>}
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--text-primary)', lineHeight: 1.4 }}>
              Range atteso tra <span style={{ fontFamily: 'var(--font-mono)' }}>{roadmap.chop_scenario?.range_low}</span> e <span style={{ fontFamily: 'var(--font-mono)' }}>{roadmap.chop_scenario?.range_high}</span>.
            </div>
          </div>
        </div>
      </div>
    </AgentCard>
  )
}

// ── Parsing Audit Scores ───────────────────────────────────────────────────"""

content = content.replace("// ── Parsing Audit Scores ───────────────────────────────────────────────────", roadmap_card)

# 3. AgentCard padding and width
content = content.replace("width: 380,", "width: 'clamp(420px, 35vw, 550px)',")
content = content.replace("padding: '8px 12px'", "padding: '12px 14px'")
content = content.replace("padding: '10px 12px'", "padding: '14px'")
content = content.replace("fontSize: 10, fontWeight: 700", "fontSize: 11, fontWeight: 800")
content = content.replace("gap: 8\n      }}>", "gap: 12\n      }}>")

# 4. Remove Trade and Log tabs, add Narrative
old_tabs = """        {[
          { id: 'agents', label: '🚀 Dashboard Live' },
          { id: 'trade', label: '📊 Trade' },
          { id: 'log', label: '📋 Log' },
        ].map(t => ("""
new_tabs = """        {[
          { id: 'agents', label: '🚀 Dashboard Live' },
          { id: 'narrative', label: '📖 Narrazione' },
        ].map(t => ("""
content = content.replace(old_tabs, new_tabs)

# 5. Remove useEffects for trade
old_effects = """  useEffect(() => {
    if (activeTrade) {
      setTab('trade');
      setSelectedTrade(activeTrade);
    }
  }, [activeTrade])

  useEffect(() => {
    if (openTrade && openTrade.entry_time && openTrade.entry_time !== prevOpenTradeTime.current) {
      setTab('trade');
      prevOpenTradeTime.current = openTrade.entry_time;
    } else if (!openTrade && prevOpenTradeTime.current) {
      prevOpenTradeTime.current = null;
    }
  }, [openTrade])

  useEffect(() => {
    setSelectedTrade(null)
  }, [activeDate])"""
content = content.replace(old_effects, "")

# 6. Render new components
old_render = """            <ContextAgentCard latestReasoning={latestReasoning} />
            <ExecutionAgentCard latestReasoning={latestReasoning} />
            <AuditAndReasoningCard latestReasoning={latestReasoning} />
          </>
        )}
        {tab === 'trade' && (
          selectedTrade ? (
            <TradePanel trade={selectedTrade} allTrades={dayTrades} proposals={dayProposals} onSelect={(t) => { setSelectedTrade(t); onSelectTrade(t); }} timeZone={timeZone} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflow: 'hidden' }}>
              <ActiveTradeCard openTrade={openTrade} liveReasoning={latestReasoning} />
              <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
                <TradePanel trade={null} allTrades={dayTrades} proposals={dayProposals} onSelect={(t) => { setSelectedTrade(t); onSelectTrade(t); }} timeZone={timeZone} />
              </div>
            </div>
          )
        )}
        {tab === 'log' && (
          <ReasoningTimeline reasonings={reasonings} onJump={onJump} timeZone={timeZone} />
        )}"""
new_render = """            {openTrade && <ActiveTradeCard openTrade={openTrade} liveReasoning={latestReasoning} />}
            <RoadmapCard latestReasoning={latestReasoning} />
            <ContextAgentCard latestReasoning={latestReasoning} />
            <ExecutionAgentCard latestReasoning={latestReasoning} />
            <AuditAndReasoningCard latestReasoning={latestReasoning} />
          </>
        )}
        {tab === 'narrative' && (
          <NarrativePanel reasonings={reasonings} onJump={onJump} timeZone={timeZone} />
        )}"""
content = content.replace(old_render, new_render)

# 7. AuditCard text truncate fix
content = content.replace("maxHeight: 250, overflowY: 'auto',", "maxHeight: 'none',")

# 8. Options Flow & Context Agent layout fixes (replace 'flexWrap: \"wrap\"' and 'flex: 1, minWidth: \"40%\"' with grid)
content = content.replace("display: 'flex', flexDirection: 'column', gap: 10", "display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10")
content = content.replace("display: 'flex', gap: 6, flexWrap: 'wrap'", "display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10")
content = content.replace("flex: 1, minWidth: '40%', ", "")
content = content.replace("width: '100%', ", "gridColumn: '1 / -1', ")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("AgentSidebar.jsx successfully patched via script.")
