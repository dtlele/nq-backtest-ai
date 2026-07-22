import os

file_path = "dashboard/src/components/AgentSidebar.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add confidence to ContextAgentCard
old_context_start = """// ── Step 1: Context Card ───────────────────────────────────────────────────
function ContextAgentCard({ latestReasoning }) {
  const hasData = latestReasoning && latestReasoning.date

  const bias = latestReasoning?.bias || latestReasoning?.fabio_direction || latestReasoning?.direction || null"""

new_context_start = """// ── Step 1: Context Card ───────────────────────────────────────────────────
function ContextAgentCard({ latestReasoning }) {
  const hasData = latestReasoning && latestReasoning.date

  const bias = latestReasoning?.bias || latestReasoning?.fabio_direction || latestReasoning?.direction || null
  const confidence = latestReasoning?.fabio_confidence || 0
  const isNoTrade = latestReasoning?.decision?.toLowerCase() !== 'trade'
"""
content = content.replace(old_context_start, new_context_start)

# 2. Add the confidence UI inside the ContextAgentCard grid
old_context_grid_end = """          {latestReasoning?.wall_level && (
            <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '10px 12px' }}>
              <div style={{ fontSize: 9.5, color: 'var(--text-muted)', marginBottom: 4 }}>WALL</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: 'var(--accent-orange)' }}>{latestReasoning.wall_level} ({latestReasoning.wall_side})</div>
            </div>
          )}
        </div>
      )}
    </AgentCard>"""

new_context_grid_end = """          {latestReasoning?.wall_level && (
            <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '10px 12px' }}>
              <div style={{ fontSize: 9.5, color: 'var(--text-muted)', marginBottom: 4 }}>WALL</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: 'var(--accent-orange)' }}>{latestReasoning.wall_level} ({latestReasoning.wall_side})</div>
            </div>
          )}
          
          <div style={{ gridColumn: '1 / -1', height: 1, background: 'rgba(255,255,255,0.05)', margin: '2px 0' }} />
          
          {/* Confidence and Decision integrated from old Execution Agent */}
          <div style={{ gridColumn: '1 / -1', background: 'rgba(0,0,0,0.2)', borderRadius: 8, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
             <div style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>EXECUTION CONFIDENCE ⚡</div>
             <ConfidenceGauge value={confidence} />
             {isNoTrade && (
               <div style={{ color: 'var(--accent-red)', fontSize: 10, marginTop: 4, fontWeight: 600 }}>
                 ⛔ No valid setup — {latestReasoning?.no_trade_reason?.slice(0, 80) || `fabio_confidence=${confidence} < 70`}
               </div>
             )}
          </div>

        </div>
      )}
    </AgentCard>"""
content = content.replace(old_context_grid_end, new_context_grid_end)

# 3. Remove ExecutionAgentCard rendering
content = content.replace("<ExecutionAgentCard latestReasoning={latestReasoning} />", "")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("AgentSidebar.jsx execution agent removed and merged via script.")
