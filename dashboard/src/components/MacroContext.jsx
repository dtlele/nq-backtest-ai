const TREND_LABELS = {
  STRONG_DOWNTREND: { label: '▼ STRONG DOWNTREND', cls: 'strong-down' },
  STRONG_UPTREND:   { label: '▲ STRONG UPTREND',   cls: 'strong-up' },
  NEUTRAL:          { label: '— NEUTRAL',            cls: 'neutral' },
}

export default function MacroContext({ ctx, reasonings }) {
  const trend = TREND_LABELS[ctx?.trend] || TREND_LABELS.NEUTRAL
  const hasDays = ctx?.t1_poc || ctx?.t2_poc

  // Extract overnight stats from the first reasoning of the day
  const firstReasoning = reasonings && reasonings.length > 0 ? reasonings[0] : null
  const overnightPoc = firstReasoning?.poc
  const overnightVah = firstReasoning?.va_high
  const overnightVal = firstReasoning?.va_low

  return (
    <div className="macro-ctx">
      <span className="macro-title">Macro Context:</span>
      <span className={`macro-trend ${trend.cls}`}>{trend.label}</span>
      <div className="macro-levels">
        {overnightVah && (
          <div className="macro-level">
            <span className="macro-level-label">Overnight VAH</span>
            <span className="macro-level-val">{Number(overnightVah).toFixed(2)}</span>
          </div>
        )}
        {overnightPoc && (
          <div className="macro-level">
            <span className="macro-level-label">Overnight POC</span>
            <span className="macro-level-val">{Number(overnightPoc).toFixed(2)}</span>
          </div>
        )}
        {overnightVal && (
          <div className="macro-level">
            <span className="macro-level-label">Overnight VAL</span>
            <span className="macro-level-val">{Number(overnightVal).toFixed(2)}</span>
          </div>
        )}
        {ctx?.t1_poc && (
          <div className="macro-level">
            <span className="macro-level-label">T-1 POC</span>
            <span className="macro-level-val">{ctx.t1_poc}</span>
          </div>
        )}
        {ctx?.t2_poc && (
          <div className="macro-level">
            <span className="macro-level-label">T-2 POC</span>
            <span className="macro-level-val">{ctx.t2_poc}</span>
          </div>
        )}
      </div>
    </div>
  )
}
