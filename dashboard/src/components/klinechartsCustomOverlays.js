import { registerOverlay } from 'klinecharts'

// Register Custom Rectangle Overlay
try {
  registerOverlay({
    name: 'customRectangle',
    totalStep: 3, // Start, End, Complete
    needDefaultPointFigure: true,
    createPointFigures: ({ coordinates, overlay }) => {
      if (coordinates.length < 2) return []

      const start = coordinates[0]
      const end = coordinates[1]
      const style = overlay.styles || {}

      return [
        {
          type: 'rect',
          attrs: {
            x: Math.min(start.x, end.x),
            y: Math.min(start.y, end.y),
            width: Math.abs(end.x - start.x),
            height: Math.abs(end.y - start.y)
          },
          styles: {
            style: 'fill',
            color: style.fillColor || 'rgba(99,179,237,0.12)'
          }
        },
        {
          type: 'rect',
          attrs: {
            x: Math.min(start.x, end.x),
            y: Math.min(start.y, end.y),
            width: Math.abs(end.x - start.x),
            height: Math.abs(end.y - start.y)
          },
          styles: {
            style: 'stroke',
            color: style.lineColor || '#63b3ed',
            size: style.lineWidth || 2
          }
        }
      ]
    }
  })
} catch (e) {
  console.log('customRectangle registration:', e.message)
}

// Register Custom Long Position (Risk/Reward) Overlay
try {
  registerOverlay({
    name: 'longPosition',
    totalStep: 4, // 1: Entry, 2: Stop/Width, 3: TP, 4: Done
    needDefaultPointFigure: true,
    createPointFigures: ({ coordinates, overlay }) => {
      if (coordinates.length < 2) return []

      const start = coordinates[0]
      const c1 = coordinates[1]
      const c2 = coordinates[2] || start

      const entryPrice = overlay.points[0]?.value || 0
      const p1Price = overlay.points[1]?.value || entryPrice
      const p2Price = overlay.points[2]?.value || entryPrice

      const stopPrice = Math.min(p1Price, p2Price)
      const tpPrice = Math.max(p1Price, p2Price)

      const riskVal = entryPrice - stopPrice
      const risk = Math.max(0.01, riskVal)
      const reward = Math.max(0.01, tpPrice - entryPrice)
      const ratio = riskVal <= 0 ? '∞ (BE)' : (reward / risk).toFixed(2)

      const startX = start.x
      const endX = c1.x
      const entryY = start.y
      const stopY = Math.max(c1.y, c2.y)
      const tpY = Math.min(c1.y, c2.y)

      const qty = overlay.styles?.quantity || 1

      return [
        // Target/Reward Rectangle (Green)
        {
          type: 'rect',
          attrs: {
            x: Math.min(startX, endX),
            y: Math.min(entryY, tpY),
            width: Math.abs(endX - startX),
            height: Math.abs(tpY - entryY)
          },
          styles: {
            style: 'fill',
            color: 'rgba(72,187,120,0.22)' // Brighter green
          }
        },
        // Stop/Risk Rectangle (Red)
        {
          type: 'rect',
          attrs: {
            x: Math.min(startX, endX),
            y: Math.min(entryY, stopY),
            width: Math.abs(endX - startX),
            height: Math.abs(stopY - entryY)
          },
          styles: {
            style: 'fill',
            color: 'rgba(252,129,129,0.22)' // Brighter red
          }
        },
        // Separation/Entry Line
        {
          type: 'line',
          attrs: {
            coordinates: [
              { x: startX, y: entryY },
              { x: endX, y: entryY }
            ]
          },
          styles: {
            color: '#ffffff',
            size: 1,
            style: 'dashed'
          }
        },
        // Stats Text
        {
          type: 'text',
          attrs: {
            x: (startX + endX) / 2,
            y: entryY - 6,
            text: `R/R: ${ratio} | Qty: ${qty}`
          },
          styles: {
            color: '#ffffff',
            size: 11,
            align: 'center'
          }
        }
      ]
    }
  })
} catch (e) {
  console.log('longPosition registration:', e.message)
}

// Register Custom Short Position Overlay
try {
  registerOverlay({
    name: 'shortPosition',
    totalStep: 4,
    needDefaultPointFigure: true,
    createPointFigures: ({ coordinates, overlay }) => {
      if (coordinates.length < 2) return []

      const start = coordinates[0]
      const c1 = coordinates[1]
      const c2 = coordinates[2] || start

      const entryPrice = overlay.points[0]?.value || 0
      const p1Price = overlay.points[1]?.value || entryPrice
      const p2Price = overlay.points[2]?.value || entryPrice

      const stopPrice = Math.max(p1Price, p2Price)
      const tpPrice = Math.min(p1Price, p2Price)

      const riskVal = stopPrice - entryPrice
      const risk = Math.max(0.01, riskVal)
      const reward = Math.max(0.01, entryPrice - tpPrice)
      const ratio = riskVal <= 0 ? '∞ (BE)' : (reward / risk).toFixed(2)

      const startX = start.x
      const endX = c1.x
      const entryY = start.y
      const stopY = Math.min(c1.y, c2.y)
      const tpY = Math.max(c1.y, c2.y)

      const qty = overlay.styles?.quantity || 1

      return [
        // Target/Reward Rectangle (Green)
        {
          type: 'rect',
          attrs: {
            x: Math.min(startX, endX),
            y: Math.min(entryY, tpY),
            width: Math.abs(endX - startX),
            height: Math.abs(tpY - entryY)
          },
          styles: {
            style: 'fill',
            color: 'rgba(72,187,120,0.22)'
          }
        },
        // Stop/Risk Rectangle (Red)
        {
          type: 'rect',
          attrs: {
            x: Math.min(startX, endX),
            y: Math.min(entryY, stopY),
            width: Math.abs(endX - startX),
            height: Math.abs(stopY - entryY)
          },
          styles: {
            style: 'fill',
            color: 'rgba(252,129,129,0.22)'
          }
        },
        // Separation/Entry Line
        {
          type: 'line',
          attrs: {
            coordinates: [
              { x: startX, y: entryY },
              { x: endX, y: entryY }
            ]
          },
          styles: {
            color: '#ffffff',
            size: 1,
            style: 'dashed'
          }
        },
        // Stats Text
        {
          type: 'text',
          attrs: {
            x: (startX + endX) / 2,
            y: entryY - 6,
            text: `R/R: ${ratio} | Qty: ${qty}`
          },
          styles: {
            color: '#ffffff',
            size: 11,
            align: 'center'
          }
        }
      ]
    }
  })
} catch (e) {
  console.log('shortPosition registration:', e.message)
}

// Register Custom Anchored Volume Profile Overlay
try {
  registerOverlay({
    name: 'anchoredVolumeProfile',
    totalStep: 2, // 1 click to place, 2: Done
    needDefaultPointFigure: true,
    createPointFigures: ({ coordinates }) => {
      if (coordinates.length === 0) return []
      return [
        {
          type: 'circle',
          attrs: {
            x: coordinates[0].x,
            y: coordinates[0].y,
            r: 4
          },
          styles: {
            style: 'fill',
            color: '#63b3ed'
          }
        }
      ]
    },
    drawExtend: ({ ctx, chart, overlay }) => {
      const candles = chart.getDataList()
      if (!candles || candles.length === 0) return

      const points = overlay.points
      if (!points || points.length === 0) return

      const anchorTime = points[0].timestamp

      let startIndex = -1
      for (let i = 0; i < candles.length; i++) {
        if (candles[i].timestamp >= anchorTime) {
          startIndex = i
          break
        }
      }
      if (startIndex === -1) return

      const rangeCandles = candles.slice(startIndex)
      if (rangeCandles.length === 0) return

      const overlayStyle = overlay.styles || {}
      const tickSize = overlayStyle.tickSize || 0.25
      const priceVol = {}

      for (const c of rangeCandles) {
        const pLow = Math.round(c.low / tickSize) * tickSize
        const pHigh = Math.round(c.high / tickSize) * tickSize
        const ticks = Math.max(1, Math.round((pHigh - pLow) / tickSize) + 1)
        const volPerTick = (c.volume || 0) / ticks

        let p = pLow
        while (p <= pHigh + 1e-9) {
          const key = Math.round(p / tickSize) * tickSize
          priceVol[key] = (priceVol[key] || 0) + volPerTick
          p += tickSize
        }
      }

      const sortedPrices = Object.keys(priceVol)
        .map(Number)
        .sort((a, b) => a - b)

      if (sortedPrices.length === 0) return

      const volumes = sortedPrices.map(p => priceVol[p])
      const maxVol = Math.max(...volumes)
      const totalVol = volumes.reduce((a, b) => a + b, 0)

      const maxIdx = volumes.indexOf(maxVol)
      const poc = sortedPrices[maxIdx]

      let vaVol = volumes[maxIdx]
      let lo = maxIdx
      let hi = maxIdx
      const vaPercentage = 0.70

      while (vaVol / totalVol < vaPercentage) {
        const addLo = lo > 0 ? volumes[lo - 1] : 0
        const addHi = hi < volumes.length - 1 ? volumes[hi + 1] : 0

        if (addLo === 0 && addHi === 0) break

        if (addHi >= addLo && hi < volumes.length - 1) {
          hi++
          vaVol += addHi
        } else if (lo > 0) {
          lo--
          vaVol += addLo
        } else {
          break
        }
      }

      const val = sortedPrices[lo]
      const vah = sortedPrices[hi]

      const anchorCoord = chart.convertToPixel({
        timestamp: anchorTime,
        value: candles[startIndex].close
      })
      if (!anchorCoord) return
      const anchorX = anchorCoord.x

      const chartWidth = ctx.canvas.clientWidth
      const chartHeight = ctx.canvas.clientHeight
      const maxProfileWidth = chartWidth * (overlayStyle.widthPercent ? overlayStyle.widthPercent / 100 : 0.25)

      ctx.save()

      const colorInside = overlayStyle.profileColorInside || 'rgba(99,179,237,0.25)'
      const colorOutside = overlayStyle.profileColorOutside || 'rgba(255,255,255,0.06)'
      const pocColor = overlayStyle.pocColor || '#ef4444'
      const vaLineColor = overlayStyle.vaColor || '#3b82f6'

      for (let i = 0; i < sortedPrices.length; i++) {
        const price = sortedPrices[i]
        const vol = priceVol[price]

        const coord = chart.convertToPixel({
          timestamp: anchorTime,
          value: price
        })
        if (!coord || coord.y < 0 || coord.y > chartHeight) continue

        const nextCoord = chart.convertToPixel({
          timestamp: anchorTime,
          value: price + tickSize
        })
        let barHeight = 1
        if (nextCoord) {
          barHeight = Math.max(1, Math.abs(nextCoord.y - coord.y))
        }

        const barWidth = (vol / maxVol) * maxProfileWidth
        const isInside = price >= val && price <= vah

        ctx.fillStyle = isInside ? colorInside : colorOutside
        ctx.fillRect(anchorX, coord.y - barHeight / 2, barWidth, barHeight)
      }

      const drawLine = (price, color, labelText, isDashed = false) => {
        const coord = chart.convertToPixel({ timestamp: anchorTime, value: price })
        if (!coord || coord.y < 0 || coord.y > chartHeight) return

        ctx.strokeStyle = color
        ctx.lineWidth = price === poc ? 2 : 1
        if (isDashed) ctx.setLineDash([4, 4])

        ctx.beginPath()
        ctx.moveTo(anchorX, coord.y)
        ctx.lineTo(chartWidth, coord.y)
        ctx.stroke()

        if (isDashed) ctx.setLineDash([])

        ctx.fillStyle = color
        ctx.font = '10px monospace'
        ctx.fillText(`${labelText}: ${price.toFixed(2)}`, anchorX + 6, coord.y - 4)
      }

      drawLine(poc, pocColor, 'POC')
      drawLine(vah, vaLineColor, 'VAH', true)
      drawLine(val, vaLineColor, 'VAL', true)

      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)'
      ctx.lineWidth = 1
      ctx.setLineDash([2, 2])
      ctx.beginPath()
      ctx.moveTo(anchorX, 0)
      ctx.lineTo(anchorX, chartHeight)
      ctx.stroke()
      ctx.setLineDash([])

      ctx.fillStyle = 'rgba(255,255,255,0.4)'
      ctx.font = '9px sans-serif'
      ctx.fillText('VP ANCHOR', anchorX + 4, 12)

      ctx.restore()
    }
  })
} catch (e) {
  console.log('anchoredVolumeProfile registration:', e.message)
}

// Register Big Trade Marker Overlay
try {
  registerOverlay({
    name: 'bigTradeMarker',
    totalStep: 1,
    createPointFigures: ({ coordinates, overlay }) => {
      if (coordinates.length === 0) return []
      const point = coordinates[0]
      const isBuy = overlay.styles?.side === 'A'
      const tradeSize = overlay.styles?.size || 30
      
      // Calculate radius based on square root of volume to keep it proportional
      // scale factor: 30 contracts -> ~4px, 100 contracts -> ~7.5px, 300 contracts -> ~13px
      const radius = Math.max(2, Math.min(15, Math.sqrt(tradeSize) * 0.75))
      
      // Un rosso leggermente più scuro per le vendite
      const color = isBuy ? 'rgba(72,187,120,0.5)' : 'rgba(239,83,80,0.5)'

      return [
        {
          type: 'circle',
          attrs: {
            x: point.x,
            y: point.y,
            r: radius
          },
          styles: {
            style: 'fill',
            color: color
          }
        }
      ]
    }
  })
} catch (e) {
  console.log('bigTradeMarker registration:', e.message)
}

// Register Labeled Horizontal Line Overlay
// Usage: createOverlay({ name: 'labeledHLine', points: [{value}],
//   styles: { lineColor, label, lineStyle, lineWidth } })
try {
  registerOverlay({
    name: 'labeledHLine',
    needDefaultPointFigure: false,
    totalStep: 1,
    createPointFigures: ({ overlay, coordinates, bounding }) => {
      if (!coordinates || coordinates.length === 0) return []
      const y = coordinates[0].y
      const color = overlay.styles?.lineColor || 'rgba(255,255,255,0.5)'
      const label = overlay.styles?.label || ''
      const lineStyle = overlay.styles?.lineStyle || 'dashed'
      const lineWidth = overlay.styles?.lineWidth || 1
      const chartWidth = bounding?.width || 3000

      return [
        // Full-width horizontal line
        {
          type: 'line',
          attrs: {
            coordinates: [
              { x: 0, y },
              { x: chartWidth, y }
            ]
          },
          styles: {
            color,
            size: lineWidth,
            style: lineStyle,
            dashedValue: [5, 4]
          }
        },
        // Label pill on the left
        {
          type: 'text',
          attrs: { x: 6, y: y - 3, text: label },
          styles: {
            color,
            size: 9,
            align: 'left',
            baseline: 'bottom',
            backgroundColor: 'rgba(13, 14, 21, 0.75)',
            borderColor: color,
            paddingLeft: 3,
            paddingRight: 3,
            paddingTop: 1,
            paddingBottom: 1,
            borderRadius: 2,
            borderSize: 0.5
          }
        }
      ]
    }
  })
} catch (e) {
  console.log('labeledHLine registration:', e.message)
}

// Register Live Analysis Marker Overlay
try {
  registerOverlay({
    name: 'liveAnalysisMarker',
    needDefaultPointFigure: false,
    totalStep: 1,
    createPointFigures: ({ coordinates }) => {
      if (coordinates.length === 0) return []
      const point = coordinates[0]

      return [
        {
          type: 'text',
          attrs: {
            x: point.x,
            y: point.y - 8,
            text: '▼'
          },
          styles: {
            color: '#FFD700', // Gold
            size: 24,
            align: 'center',
            baseline: 'bottom',
            backgroundColor: 'rgba(0, 0, 0, 0)',
            borderColor: 'rgba(0, 0, 0, 0)',
            paddingLeft: 0,
            paddingRight: 0,
            paddingTop: 0,
            paddingBottom: 0,
            borderRadius: 0
          }
        }
      ]
    }
  })
} catch (e) {
  console.log('liveAnalysisMarker registration:', e.message)
}

// Register Phase Band Overlay
try {
  registerOverlay({
    name: 'phaseBand',
    needDefaultPointFigure: false,
    totalStep: 1,
    drawExtend: ({ ctx, chart, overlay }) => {
      const points = overlay.points
      if (!points || points.length === 0) return
      
      const timestamp = points[0].timestamp
      const coord = chart.convertToPixel({ timestamp })
      if (!coord) return
      
      const barSpace = chart.getBarSpace().bar
      const width = barSpace * 5 // M5 width
      const chartHeight = ctx.canvas.clientHeight
      const phase = overlay.styles?.phase || 'none'
      
      let color = 'rgba(0,0,0,0)'
      if (phase === 'accumulation') {
        color = 'rgba(52, 152, 219, 0.08)' // faint blue
      } else if (phase === 'expansive') {
        color = 'rgba(230, 126, 34, 0.08)' // faint orange
      }
      
      if (color === 'rgba(0,0,0,0)') return
      
      ctx.save()
      ctx.fillStyle = color
      ctx.fillRect(coord.x - width / 2, 0, width, chartHeight)
      ctx.restore()
    }
  })
} catch (e) {
  console.log('phaseBand registration:', e.message)
}

// Register Relation Node Marker Overlay
try {
  registerOverlay({
    name: 'relationNodeMarker',
    totalStep: 1,
    needDefaultPointFigure: false,
    createPointFigures: ({ coordinates, overlay }) => {
      if (coordinates.length === 0) return []
      const point = coordinates[0]
      const isBuy = overlay.styles?.side === 'A'
      const index = overlay.styles?.index || '?'
      const vol = overlay.styles?.volume || ''

      const color = isBuy ? 'rgba(46, 204, 113, 0.85)' : 'rgba(231, 76, 60, 0.85)'
      const borderColor = '#ffffff'

      return [
        // Inner Circle
        {
          type: 'circle',
          attrs: {
            x: point.x,
            y: point.y,
            r: 10
          },
          styles: {
            style: 'fill',
            color: color
          }
        },
        // Border Circle
        {
          type: 'circle',
          attrs: {
            x: point.x,
            y: point.y,
            r: 10
          },
          styles: {
            style: 'stroke',
            color: borderColor,
            size: 1.5
          }
        },
        // Step number Text inside the circle
        {
          type: 'text',
          attrs: {
            x: point.x,
            y: point.y,
            text: String(index)
          },
          styles: {
            color: '#ffffff',
            size: 10,
            align: 'center',
            baseline: 'middle'
          }
        },
        // Volume Badge above the circle
        {
          type: 'text',
          attrs: {
            x: point.x,
            y: point.y - 14,
            text: vol ? `${vol}c` : ''
          },
          styles: {
            color: '#ffffff',
            size: 8,
            align: 'center',
            baseline: 'bottom',
            backgroundColor: 'rgba(15, 23, 42, 0.8)',
            paddingLeft: 3,
            paddingRight: 3,
            paddingTop: 1,
            paddingBottom: 1,
            borderRadius: 2
          }
        }
      ]
    }
  })
} catch (e) {
  console.log('relationNodeMarker registration:', e.message)
}

