import { useState, useEffect } from 'react'
import { Lock, Unlock, Check } from 'lucide-react'
import './DrawingSettingsModal.css'

export default function DrawingSettingsModal({
  selectedDrawing,
  onUpdateDrawing,
  onClose
}) {
  const [lineColor, setLineColor] = useState('#63b3ed')
  const [lineWidth, setLineWidth] = useState(2)
  const [lineStyle, setLineStyle] = useState('solid')
  const [fillColor, setFillColor] = useState('')
  const [isLocked, setIsLocked] = useState(false)
  const [riskRewardQty, setRiskRewardQty] = useState(1)

  useEffect(() => {
    if (!selectedDrawing) return

    const styles = selectedDrawing.styles || {}
    const isLock = !!selectedDrawing.lock

    // Determine line color (custom or built-in segment)
    const currentLineColor = styles.lineColor || (styles.line && styles.line.color) || '#63b3ed'
    const currentLineWidth = styles.lineWidth || (styles.line && styles.line.size) || 2
    const currentFillColor = styles.fillColor || ''
    const currentQty = styles.quantity || 1

    let currentLineStyle = 'solid'
    const dashPattern = styles.line && styles.line.dashPattern
    if (dashPattern && dashPattern.length > 0) {
      currentLineStyle = 'dashed'
    }

    setLineColor(currentLineColor)
    setLineWidth(currentLineWidth)
    setLineStyle(currentLineStyle)
    setFillColor(currentFillColor)
    setIsLocked(isLock)
    setRiskRewardQty(currentQty)
  }, [selectedDrawing])

  if (!selectedDrawing) return null

  const colors = [
    '#63b3ed', // Blue
    '#48bb78', // Green
    '#fc8181', // Red
    '#f6e05e', // Yellow
    '#f6ad55', // Orange
    '#9f7aea', // Purple
    '#ffffff', // White
    '#a0aec0'  // Gray
  ]

  const fillColors = [
    'transparent',
    'rgba(99,179,237,0.15)',
    'rgba(72,187,120,0.15)',
    'rgba(252,129,129,0.15)',
    'rgba(246,224,94,0.15)',
    'rgba(246,173,85,0.15)',
    'rgba(159,122,234,0.15)',
  ]

  const applyUpdate = (updatedStyles, updatedOptions = {}) => {
    if (onUpdateDrawing) {
      onUpdateDrawing({
        styles: {
          ...selectedDrawing.styles,
          ...updatedStyles
        },
        ...updatedOptions
      })
    }
  }

  const handleColorChange = (color) => {
    setLineColor(color)
    applyUpdate({
      lineColor: color,
      line: {
        ...(selectedDrawing.styles?.line || {}),
        color: color
      }
    })
  }

  const handleWidthChange = (width) => {
    setLineWidth(width)
    applyUpdate({
      lineWidth: width,
      line: {
        ...(selectedDrawing.styles?.line || {}),
        size: width
      }
    })
  }

  const handleStyleChange = (styleType) => {
    setLineStyle(styleType)
    const dash = styleType === 'dashed' ? [6, 6] : []
    applyUpdate({
      line: {
        ...(selectedDrawing.styles?.line || {}),
        dashPattern: dash
      }
    })
  }

  const handleFillChange = (fill) => {
    setFillColor(fill)
    applyUpdate({
      fillColor: fill === 'transparent' ? 'transparent' : fill
    })
  }

  const handleLockToggle = () => {
    const nextLocked = !isLocked
    setIsLocked(nextLocked)
    applyUpdate({}, { lock: nextLocked })
  }

  const handleQtyChange = (val) => {
    const qty = Math.max(1, parseInt(val) || 1)
    setRiskRewardQty(qty)
    applyUpdate({
      quantity: qty
    })
  }

  const supportsFill = ['customRectangle', 'longPosition', 'shortPosition', 'anchoredVolumeProfile'].includes(selectedDrawing.name)

  return (
    <div className="drawing-properties-bar glass">
      {/* Label/Type */}
      <span className="prop-badge">
        {selectedDrawing.name.replace('custom', '').replace('Position', ' Position').toUpperCase()}
      </span>

      <div className="prop-divider" />

      {/* Line Color Selector */}
      <div className="prop-group">
        <label>Colore</label>
        <div className="color-swatches">
          {colors.map(c => (
            <button
              key={c}
              className={`color-swatch ${lineColor === c ? 'active' : ''}`}
              style={{ backgroundColor: c }}
              onClick={() => handleColorChange(c)}
              title={c}
            />
          ))}
        </div>
      </div>

      <div className="prop-divider" />

      {/* Line Width */}
      <div className="prop-group">
        <label>Spessore</label>
        <div className="size-selector">
          {[1, 2, 3, 4].map(w => (
            <button
              key={w}
              className={`size-btn ${lineWidth === w ? 'active' : ''}`}
              onClick={() => handleWidthChange(w)}
            >
              {w}px
            </button>
          ))}
        </div>
      </div>

      <div className="prop-divider" />

      {/* Line Dash Style */}
      <div className="prop-group">
        <label>Stile</label>
        <div className="style-selector">
          <button
            className={`style-btn ${lineStyle === 'solid' ? 'active' : ''}`}
            onClick={() => handleStyleChange('solid')}
          >
            ━
          </button>
          <button
            className={`style-btn ${lineStyle === 'dashed' ? 'active' : ''}`}
            onClick={() => handleStyleChange('dashed')}
          >
            ╌╌
          </button>
        </div>
      </div>

      {supportsFill && (
        <>
          <div className="prop-divider" />
          {/* Fill Color */}
          <div className="prop-group">
            <label>Sfondo</label>
            <div className="color-swatches">
              {fillColors.map(c => (
                <button
                  key={c}
                  className={`color-swatch fill-swatch ${fillColor === c || (c === 'transparent' && !fillColor) ? 'active' : ''}`}
                  style={{ backgroundColor: c === 'transparent' ? '#161b26' : c }}
                  onClick={() => handleFillChange(c)}
                  title={c === 'transparent' ? 'No Fill' : 'Fill'}
                >
                  {c === 'transparent' && <span className="no-fill-slash" />}
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Quantity settings for Risk/Reward Long/Short positions */}
      {(selectedDrawing.name === 'longPosition' || selectedDrawing.name === 'shortPosition') && (
        <>
          <div className="prop-divider" />
          <div className="prop-group prop-qty">
            <label>Quantità</label>
            <input
              type="number"
              min="1"
              value={riskRewardQty}
              onChange={(e) => handleQtyChange(e.target.value)}
              className="qty-input"
            />
          </div>
        </>
      )}

      <div className="prop-divider" />

      {/* Actions */}
      <div className="prop-actions">
        <button
          className={`prop-action-btn ${isLocked ? 'locked' : ''}`}
          onClick={handleLockToggle}
          title={isLocked ? 'Sblocca elemento' : 'Blocca elemento (impedisce trascinamento)'}
        >
          {isLocked ? <Lock size={14} /> : <Unlock size={14} />}
        </button>
        <button
          className="prop-action-btn close-btn"
          onClick={onClose}
          title="Chiudi proprietà"
        >
          <Check size={14} />
        </button>
      </div>
    </div>
  )
}
