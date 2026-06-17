import { MousePointer, Milestone, Square, Award, BarChart3, Trash2, XCircle } from 'lucide-react'
import './DrawingToolbar.css'

export default function DrawingToolbar({
  activeTool,
  setActiveTool,
  onDeleteSelected,
  onClearAll,
  hasSelected
}) {
  const tools = [
    { id: 'select', label: 'Cursore / Selezione', icon: MousePointer, toolType: null },
    { id: 'trend-line', label: 'Linea di Trend', icon: Milestone, toolType: 'segment' },
    { id: 'rectangle', label: 'Rettangolo / Zona', icon: Square, toolType: 'customRectangle' },
    { id: 'long-position', label: 'Posizione Long (Risk/Reward)', icon: Award, toolType: 'longPosition' },
    { id: 'anchored-volume-profile', label: 'Volume Profile Ancorato', icon: BarChart3, toolType: 'anchoredVolumeProfile' },
  ]

  return (
    <div className="drawing-toolbar">
      <div className="toolbar-section">
        {tools.map((t) => {
          const Icon = t.icon
          const isActive = activeTool === t.toolType && (t.id !== 'select' || activeTool === null)
          return (
            <button
              key={t.id}
              className={`toolbar-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTool(t.toolType)}
              title={t.label}
            >
              <Icon size={18} />
            </button>
          )
        })}
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-section">
        <button
          className="toolbar-btn delete-btn"
          onClick={onDeleteSelected}
          disabled={!hasSelected}
          title="Elimina elemento selezionato (Canc)"
        >
          <Trash2 size={18} />
        </button>
        <button
          className="toolbar-btn clear-btn"
          onClick={onClearAll}
          title="Cancella tutti i disegni"
        >
          <XCircle size={18} />
        </button>
      </div>
    </div>
  )
}
