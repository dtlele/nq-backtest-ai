/**
 * Custom series primitive for Lightweight Charts v5.
 * Computes and renders an Anchored Volume Profile from a given starting time.
 */
export class AnchoredVolumeProfilePrimitive {
  constructor(anchorTime, candles, options = {}) {
    this._anchorTime = anchorTime
    this._candles = candles
    this._options = {
      widthPercent: 25, // Percentage of chart width for the histogram
      tickSize: 0.25, // Tick bucket size for NQ
      vaPercentage: 0.70, // 70% Value Area
      pocColor: '#ef4444', // Red POC
      vahColor: '#3b82f6', // Blue VAH
      valColor: '#3b82f6', // Blue VAL
      profileColorInside: 'rgba(99,179,237,0.3)', // Inside VA
      profileColorOutside: 'rgba(255,255,255,0.08)', // Outside VA
      showLabels: true,
      align: 'right', // 'right' or 'left' (relative to anchor point)
      ...options
    }
    this._chart = null
    this._series = null
    this._requestUpdate = null
    this._paneViews = [new VolumeProfilePaneView(this)]
  }

  // --- ISeriesPrimitive implementation ---

  attached({ chart, series, requestUpdate }) {
    this._chart = chart
    this._series = series
    this._requestUpdate = requestUpdate
  }

  detached() {
    this._chart = null
    this._series = null
    this._requestUpdate = null
  }

  paneViews() {
    return this._paneViews
  }

  updateAnchor(anchorTime) {
    if (this._anchorTime !== anchorTime) {
      this._anchorTime = anchorTime
      if (this._requestUpdate) this._requestUpdate()
    }
  }

  updateOptions(options) {
    this._options = { ...this._options, ...options }
    if (this._requestUpdate) this._requestUpdate()
  }

  // --- Computational Logic ---

  computeProfile() {
    if (!this._candles || this._candles.length === 0 || !this._anchorTime) {
      return null
    }

    // Find the starting candle index matching or nearest to anchorTime
    let startIndex = -1
    for (let i = 0; i < this._candles.length; i++) {
      if (this._candles[i].time >= this._anchorTime) {
        startIndex = i
        break
      }
    }

    if (startIndex === -1) return null

    const rangeCandles = this._candles.slice(startIndex)
    if (rangeCandles.length === 0) return null

    // Compute volume profile buckets
    const priceVol = {}
    const tickSize = this._options.tickSize

    for (const c of rangeCandles) {
      const low = c.low
      const high = c.high
      const volume = c.volume || 0

      const pLow = Math.round(low / tickSize) * tickSize
      const pHigh = Math.round(high / tickSize) * tickSize
      const ticks = Math.max(1, Math.round((pHigh - pLow) / tickSize) + 1)
      const volPerTick = volume / ticks

      let price = pLow
      while (price <= pHigh + 1e-9) {
        const key = Math.round(price / tickSize) * tickSize
        priceVol[key] = (priceVol[key] || 0) + volPerTick
        price += tickSize
      }
    }

    const sortedPrices = Object.keys(priceVol)
      .map(Number)
      .sort((a, b) => a - b)

    if (sortedPrices.length === 0) return null

    const volumes = sortedPrices.map(p => priceVol[p])
    const totalVolume = volumes.reduce((a, b) => a + b, 0)

    // Find POC (Point of Control)
    let maxVolIdx = 0
    let maxVol = 0
    for (let i = 0; i < volumes.length; i++) {
      if (volumes[i] > maxVol) {
        maxVol = volumes[i]
        maxVolIdx = i
      }
    }
    const poc = sortedPrices[maxVolIdx]

    // Find Value Area (70% Volume around POC)
    let vaVolume = volumes[maxVolIdx]
    let loIdx = maxVolIdx
    let hiIdx = maxVolIdx
    const vaPercentage = this._options.vaPercentage

    while (vaVolume / totalVolume < vaPercentage) {
      const addLo = loIdx > 0 ? volumes[loIdx - 1] : 0
      const addHi = hiIdx < volumes.length - 1 ? volumes[hiIdx + 1] : 0

      if (addHi === 0 && addLo === 0) break

      if (addHi >= addLo && hiIdx < volumes.length - 1) {
        hiIdx++
        vaVolume += addHi
      } else if (loIdx > 0) {
        loIdx--
        vaVolume += addLo
      } else {
        break
      }
    }

    const vah = sortedPrices[hiIdx]
    const val = sortedPrices[loIdx]

    return {
      poc,
      vah,
      val,
      priceVol,
      sortedPrices,
      volumes,
      maxVol,
      totalVolume,
      startIndex
    }
  }
}

class VolumeProfilePaneView {
  constructor(primitive) {
    this._primitive = primitive
  }

  zOrder() {
    return 'normal' // Draw above grid, below text annotations
  }

  renderer() {
    return new VolumeProfileRenderer(this._primitive)
  }
}

class VolumeProfileRenderer {
  constructor(primitive) {
    this._primitive = primitive
  }

  draw(ctx) {
    const p = this._primitive
    if (!p._chart || !p._series) return

    const profileData = p.computeProfile()
    if (!profileData) return

    const { poc, vah, val, priceVol, sortedPrices, maxVol } = profileData

    // Get time scale & price scale coordinates
    const timeScale = p._chart.timeScale()
    const priceScale = p._series

    const anchorX = timeScale.timeToCoordinate(p._anchorTime)
    if (anchorX === null) return

    const chartWidth = ctx.canvas.clientWidth
    const chartHeight = ctx.canvas.clientHeight

    // Width limit of the histogram
    const maxHistWidth = (chartWidth * p._options.widthPercent) / 100

    ctx.save()

    // Determine drawing bounds
    // We will draw from the anchorX coordinates rightward, but cap at chart width
    // Draw each price level as a horizontal bar
    for (let i = 0; i < sortedPrices.length; i++) {
      const price = sortedPrices[i]
      const vol = priceVol[price]

      // Convert price to Y coordinate
      // Lightweight charts returns coordinate as priceToCoordinate (can be negative or beyond height if offscreen)
      const y = priceScale.priceToCoordinate(price)
      if (y === null || y < 0 || y > chartHeight) continue

      // Height of each bar is determined by the tick size
      // We can compute the Y coordinate of the next tick to get the exact height in pixels
      const yNext = priceScale.priceToCoordinate(price + p._options.tickSize)
      let barHeight = 1
      if (yNext !== null) {
        barHeight = Math.max(1, Math.abs(yNext - y))
      }

      const barWidth = (vol / maxVol) * maxHistWidth
      const isInsideValueArea = price >= val && price <= vah

      // Color based on value area
      ctx.fillStyle = isInsideValueArea
        ? p._options.profileColorInside
        : p._options.profileColorOutside

      // Render horizontal bar
      // Starting from anchorX (or right side if aligned to right edge)
      if (p._options.align === 'right') {
        ctx.fillRect(anchorX, y - barHeight / 2, barWidth, barHeight)
      } else {
        // Aligned to the left of anchor
        ctx.fillRect(anchorX - barWidth, y - barHeight / 2, barWidth, barHeight)
      }
    }

    // --- Draw POC Line ---
    const pocY = priceScale.priceToCoordinate(poc)
    if (pocY !== null && pocY >= 0 && pocY <= chartHeight) {
      ctx.strokeStyle = p._options.pocColor
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(anchorX, pocY)
      ctx.lineTo(chartWidth, pocY)
      ctx.stroke()

      if (p._options.showLabels) {
        ctx.fillStyle = p._options.pocColor
        ctx.font = '10px monospace'
        ctx.fillText(`POC: ${poc.toFixed(2)}`, anchorX + 5, pocY - 4)
      }
    }

    // --- Draw VAH Line ---
    const vahY = priceScale.priceToCoordinate(vah)
    if (vahY !== null && vahY >= 0 && vahY <= chartHeight) {
      ctx.strokeStyle = p._options.vahColor
      ctx.lineWidth = 1
      ctx.setLineDash([4, 4])
      ctx.beginPath()
      ctx.moveTo(anchorX, vahY)
      ctx.lineTo(chartWidth, vahY)
      ctx.stroke()
      ctx.setLineDash([])

      if (p._options.showLabels) {
        ctx.fillStyle = p._options.vahColor
        ctx.font = '10px monospace'
        ctx.fillText(`VAH: ${vah.toFixed(2)}`, anchorX + 5, vahY - 4)
      }
    }

    // --- Draw VAL Line ---
    const valY = priceScale.priceToCoordinate(val)
    if (valY !== null && valY >= 0 && valY <= chartHeight) {
      ctx.strokeStyle = p._options.valColor
      ctx.lineWidth = 1
      ctx.setLineDash([4, 4])
      ctx.beginPath()
      ctx.moveTo(anchorX, valY)
      ctx.lineTo(chartWidth, valY)
      ctx.stroke()
      ctx.setLineDash([])

      if (p._options.showLabels) {
        ctx.fillStyle = p._options.valColor
        ctx.font = '10px monospace'
        ctx.fillText(`VAL: ${val.toFixed(2)}`, anchorX + 5, valY - 4)
      }
    }

    // --- Draw Anchor Line Indicator ---
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)'
    ctx.lineWidth = 1
    ctx.setLineDash([2, 2])
    ctx.beginPath()
    ctx.moveTo(anchorX, 0)
    ctx.lineTo(anchorX, chartHeight)
    ctx.stroke()
    ctx.setLineDash([])

    // Anchor text marker
    ctx.fillStyle = 'rgba(255, 255, 255, 0.5)'
    ctx.font = '9px sans-serif'
    ctx.fillText('VP ANCHOR', anchorX + 4, 12)

    ctx.restore()
  }
}
