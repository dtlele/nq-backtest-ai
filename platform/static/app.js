let appData = null;
let allBars = null;
let mainChartObj = null;
let candleSeries = null;
let deltaChartObj = null;
let deltaSeries = null;
let currentPriceLines = [];
let currentSessionDate = null;
let bubbleElements = [];

async function init() {
    try {
        const ts = new Date().getTime();
        const [resData, resBars] = await Promise.all([
            fetch(`data.json?v=${ts}`),
            fetch(`all_bars.json?v=${ts}`)
        ]);
        appData = await resData.json();
        allBars = await resBars.json();
        
        renderSummary();
        renderSidebar();
        initCharts();
        
        if (appData.days.length > 0) {
            const sorted = [...appData.days].sort((a, b) => b.date.localeCompare(a.date));
            selectSession(sorted[0].date);
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

function renderSummary() {
    const s = appData.summary;
    document.getElementById('kpiCandidates').textContent = s.total_candidates;
    document.getElementById('kpiDays').textContent = appData.days.length;
    document.getElementById('kpiWinRate').textContent = s.win_rate.toFixed(1) + '%';
    document.getElementById('kpiPnL').textContent = '$' + s.pnl.toLocaleString();
}

function renderSidebar() {
    const list = document.getElementById('sessionList');
    list.innerHTML = '';
    const sorted = [...appData.days].sort((a, b) => b.date.localeCompare(a.date));
    sorted.forEach(day => {
        const item = document.createElement('div');
        item.className = 'session-item';
        item.onclick = () => selectSession(day.date);
        item.dataset.date = day.date;
        item.innerHTML = `
            <span class="session-date">${day.date}</span>
            <span class="session-meta">${day.candidates.length} Candidates · ${day.trades.length} Trades</span>
        `;
        list.appendChild(item);
    });
}

function initCharts() {
    const mainContainer = document.getElementById('mainChart');
    const deltaContainer = document.getElementById('deltaChart');
    
    mainContainer.innerHTML = '';
    deltaContainer.innerHTML = '';

    const chartOptions = {
        layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#888' },
        grid: { vertLines: { color: 'rgba(255,255,255,0.05)' }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
        crosshair: { mode: 0 },
        timeScale: { timeVisible: true, secondsVisible: false }
    };

    mainChartObj = LightweightCharts.createChart(mainContainer, chartOptions);
    candleSeries = mainChartObj.addCandlestickSeries({
        upColor: '#00ff88', downColor: '#ff4d4d', borderVisible: false,
        wickUpColor: '#00ff88', wickDownColor: '#ff4d4d'
    });

    deltaChartObj = LightweightCharts.createChart(deltaContainer, chartOptions);
    deltaSeries = deltaChartObj.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: ''
    });

    // Populate series with all_bars
    const cData = [];
    const dData = [];
    allBars.forEach(b => {
        cData.push({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close });
        dData.push({ time: b.time, value: b.delta, color: b.delta >= 0 ? 'rgba(0, 255, 136, 0.5)' : 'rgba(255, 77, 77, 0.5)' });
    });
    
    candleSeries.setData(cData);
    deltaSeries.setData(dData);

    // Set markers for all historical trades and candidates
    const allMarkers = [];
    appData.days.forEach(d => {
        d.candidates.forEach(c => {
            const isLong = (c.trade_direction === 'long' || c.fabio_direction === 'long');
            if (c.decision === 'trade') {
                const isWin = c.trade_pnl_usd && c.trade_pnl_usd > 0;
                const color = isWin ? '#00ff88' : (c.trade_pnl_usd === null ? '#00f2fe' : '#ff4d4d');
                allMarkers.push({
                    time: new Date(c.bar_time_utc).getTime() / 1000,
                    position: isLong ? 'belowBar' : 'aboveBar',
                    color: color,
                    shape: isLong ? 'arrowUp' : 'arrowDown',
                    text: isLong ? 'LONG' : 'SHORT'
                });
            } else {
                allMarkers.push({
                    time: new Date(c.bar_time_utc).getTime() / 1000,
                    position: isLong ? 'belowBar' : 'aboveBar',
                    color: '#555555',
                    shape: 'circle',
                    text: 'CANDIDATE'
                });
            }
        });
    });
    allMarkers.sort((a, b) => a.time - b.time);
    candleSeries.setMarkers(allMarkers);

    // Sync charts
    mainChartObj.timeScale().subscribeVisibleLogicalRangeChange(range => {
        if (range) {
            deltaChartObj.timeScale().setVisibleLogicalRange(range);
            updateBubblePositions();
        }
    });
    // Note: lightweight-charts v3 doesn't have a direct vertical pan event.
    // HTML overlays will update on resize or timeScale change instead.
    deltaChartObj.timeScale().subscribeVisibleLogicalRangeChange(range => {
        if (range) mainChartObj.timeScale().setVisibleLogicalRange(range);
    });
    // Removed click event, reasoning is now driven by a list in the right panel
}

function selectSession(date) {
    currentSessionDate = date;
    document.querySelectorAll('.session-item').forEach(i => i.classList.remove('active'));
    const el = document.querySelector(`.session-item[data-date="${date}"]`);
    if (el) el.classList.add('active');
    document.getElementById('currentDay').textContent = date;
    
    const day = appData.days.find(d => d.date === date);
    if (!day) return;
    
    const sorted = [...day.candidates].sort((a, b) => new Date(a.bar_time_utc) - new Date(b.bar_time_utc));
    const first = sorted[0];
    
    // Clear old price lines
    currentPriceLines.forEach(l => candleSeries.removePriceLine(l));
    currentPriceLines = [];
    
    if (first) {
        if (first.poc) currentPriceLines.push(candleSeries.createPriceLine({ price: first.poc, color: '#7000ff', lineStyle: 2, title: 'POC' }));
        if (first.va_high) currentPriceLines.push(candleSeries.createPriceLine({ price: first.va_high, color: '#00f2fe', lineStyle: 2, title: 'VAH' }));
        if (first.va_low) currentPriceLines.push(candleSeries.createPriceLine({ price: first.va_low, color: '#00f2fe', lineStyle: 2, title: 'VAL' }));
        if (first.ib_high) currentPriceLines.push(candleSeries.createPriceLine({ price: first.ib_high, color: '#ffaa00', lineStyle: 4, title: 'IBH' }));
        if (first.ib_low) currentPriceLines.push(candleSeries.createPriceLine({ price: first.ib_low, color: '#ffaa00', lineStyle: 4, title: 'IBL' }));
    }
    
    // Scroll to this session
    const sessionStart = new Date(`${date}T13:30:00Z`).getTime() / 1000;
    const sessionEnd = new Date(`${date}T20:15:00Z`).getTime() / 1000;
    mainChartObj.timeScale().setVisibleRange({
        from: sessionStart,
        to: sessionEnd
    });
    
    renderBubbles();
    renderVolumeProfile(date);
    
    renderCandidateList(sorted);
}

let animationFrameId = null;

function renderBubbles() {
    bubbleElements.forEach(el => el.remove());
    bubbleElements = [];
    
    if (!currentSessionDate) return;
    const sessionStart = new Date(`${currentSessionDate}T00:00:00Z`).getTime() / 1000;
    const sessionEnd = new Date(`${currentSessionDate}T23:59:59Z`).getTime() / 1000;
    
    const sessionBars = allBars.filter(b => b.time >= sessionStart && b.time <= sessionEnd);
    const sessionBigTrades = sessionBars.flatMap(b => (b.big_trades || []).map(t => ({...t, time: b.time})));
    
    const container = document.getElementById('mainChart');
    
    sessionBigTrades.forEach(t => {
        const el = document.createElement('div');
        el.className = `big-trade-bubble ${t.side === 'A' ? 'bubble-buy' : 'bubble-sell'}`;
        
        // Logarithmic scaling for bubble size
        const minVol = 30;
        const maxVol = 800;
        const normalized = Math.min(Math.max((Math.log10(t.size) - Math.log10(minVol)) / (Math.log10(maxVol) - Math.log10(minVol)), 0), 1);
        const radius = 8 + (normalized * 30); // 8px to 38px
        
        el.style.width = `${radius}px`;
        el.style.height = `${radius}px`;
        
        // Store data on element for updating position
        el.dataset.time = t.time;
        el.dataset.price = t.price;
        el.title = `${t.side === 'A' ? 'BUY' : 'SELL'} ${t.size} @ ${t.price}`;
        
        // Appear animation
        el.style.opacity = '0';
        el.style.transform = 'scale(0.5)';
        setTimeout(() => {
            el.style.transition = 'opacity 0.4s ease, transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
            el.style.opacity = '1';
            el.style.transform = 'scale(1)';
        }, 50);
        
        container.appendChild(el);
        bubbleElements.push(el);
    });
    
    startRenderLoop();
}

function startRenderLoop() {
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    
    function loop() {
        updateOverlays();
        animationFrameId = requestAnimationFrame(loop);
    }
    loop();
}

function updateOverlays() {
    if (!mainChartObj || !candleSeries) return;
    
    const chartHeight = document.getElementById('mainChart').clientHeight;
    const chartWidth = document.getElementById('mainChart').clientWidth;
    
    // Update Bubbles
    bubbleElements.forEach(el => {
        const time = parseInt(el.dataset.time);
        const price = parseFloat(el.dataset.price);
        
        const x = mainChartObj.timeScale().timeToCoordinate(time);
        const y = candleSeries.priceToCoordinate(price);
        
        if (x === null || y === null || x < 0 || x > chartWidth || y < -50 || y > chartHeight + 50) {
            el.style.display = 'none';
        } else {
            el.style.display = 'block';
            const r = parseFloat(el.style.width) / 2;
            el.style.left = `${x - r}px`;
            el.style.top = `${y - r}px`;
        }
    });
    
    // Update Volume Profile
    const vpContainer = document.getElementById('volumeProfile');
    if (vpContainer) {
        const rows = vpContainer.querySelectorAll('.vp-row');
        rows.forEach(row => {
            const price = parseFloat(row.dataset.price);
            const y = candleSeries.priceToCoordinate(price);
            if (y === null || y < -20 || y > chartHeight + 20) {
                row.style.display = 'none';
            } else {
                row.style.display = 'flex';
                row.style.top = `${y - 2}px`; // center the 4px bar
            }
        });
    }
}

function renderVolumeProfile(date) {
    const vpContainer = document.getElementById('volumeProfile');
    vpContainer.innerHTML = '';
    
    // In DeepCharts style, the VP is a histogram attached to the right side of the screen.
    // We can calculate the VP from the M5 bars of the day. It's an approximation, but useful.
    const sessionStart = new Date(`${date}T00:00:00Z`).getTime() / 1000;
    const sessionEnd = new Date(`${date}T23:59:59Z`).getTime() / 1000;
    const sessionBars = allBars.filter(b => b.time >= sessionStart && b.time <= sessionEnd);
    
    if(sessionBars.length === 0) return;
    
    // We only have Open, High, Low, Close, Volume.
    // Approximate VP by distributing volume evenly across the price range of each bar.
    const profile = {};
    const tickSize = 0.25; // NQ tick size
    
    sessionBars.forEach(b => {
        const range = Math.max(0.25, b.high - b.low);
        const ticks = range / tickSize;
        const volPerTick = b.volume / (ticks || 1);
        
        for(let p = b.low; p <= b.high; p += tickSize) {
            const priceLevel = p.toFixed(2);
            if(!profile[priceLevel]) profile[priceLevel] = { buy: 0, sell: 0, total: 0 };
            profile[priceLevel].total += volPerTick;
            // Since we don't have true buy/sell volume per tick here, we use delta to bias it
            const deltaRatio = b.delta / (b.volume || 1); // -1 to 1
            const buyVol = volPerTick * (0.5 + (deltaRatio / 2));
            profile[priceLevel].buy += buyVol;
            profile[priceLevel].sell += (volPerTick - buyVol);
        }
    });
    
    let maxVol = 0;
    const levels = [];
    for(let p in profile) {
        maxVol = Math.max(maxVol, profile[p].total);
        levels.push({ price: parseFloat(p), ...profile[p] });
    }
    levels.sort((a,b) => b.price - a.price); // Descending
    
    // Create HTML elements for the profile
    levels.forEach(l => {
        const row = document.createElement('div');
        row.className = 'vp-row';
        row.dataset.price = l.price;
        
        const widthPct = Math.min(100, (l.total / maxVol) * 100);
        const buyPct = (l.buy / l.total) * 100;
        
        row.innerHTML = `
            <div class="vp-bar" style="width: ${widthPct}%">
                <div class="vp-buy" style="width: ${buyPct}%"></div>
                <div class="vp-sell" style="width: ${100 - buyPct}%"></div>
            </div>
        `;
        vpContainer.appendChild(row);
    });
    
    // We need to position these rows using absolute positioning so they align with the Y-axis
    // But since the chart can pan vertically, we must update them.
    updateVPPositions();
}

function updateVPPositions() {
    const vpContainer = document.getElementById('volumeProfile');
    if(!vpContainer) return;
    
    const rows = vpContainer.querySelectorAll('.vp-row');
    rows.forEach(row => {
        const price = parseFloat(row.dataset.price);
        const y = candleSeries.priceToCoordinate(price);
        const chartHeight = document.getElementById('mainChart').clientHeight;
        if (y === null || y < 0 || y > chartHeight) {
            row.style.display = 'none';
        } else {
            row.style.display = 'block';
            row.style.top = `${y}px`;
        }
    });
}


function renderCandidateList(candidates) {
    const container = document.getElementById('reasoningContent');
    container.innerHTML = '';
    document.getElementById('selectedBarTime').textContent = 'Timeline';
    
    if (candidates.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No candidates for this session.</p></div>';
        return;
    }

    candidates.forEach(cand => {
        let decisionStr = cand.decision;
        if (!decisionStr && cand.fabio_setup) {
            decisionStr = 'trade'; // Fallback for old logs
        }
        
        let dirStr = 'PASS';
        let decisionColor = 'var(--text-muted)';
        
        if (decisionStr === 'trade') {
            if (cand.trade_pnl_ticks !== undefined && cand.trade_pnl_ticks !== null) {
                if (cand.trade_pnl_ticks > 0) {
                    dirStr = `WIN (+${cand.trade_pnl_ticks})`;
                    decisionColor = 'var(--accent-green)';
                } else if (cand.trade_pnl_ticks < 0) {
                    dirStr = `LOSS (${cand.trade_pnl_ticks})`;
                    decisionColor = 'var(--accent-red)';
                } else {
                    dirStr = 'SCRATCH';
                    decisionColor = 'var(--text-muted)';
                }
            } else {
                const isLong = (cand.trade_direction === 'long' || cand.fabio_direction === 'long');
                dirStr = isLong ? 'LONG' : 'SHORT';
                decisionColor = 'var(--accent-green)';
            }
        }
        
        const card = document.createElement('div');
        card.className = 'candidate-card';
        card.style.border = `1px solid ${decisionColor}`;
        card.style.marginBottom = '12px';
        card.style.padding = '16px';
        card.style.borderRadius = '8px';
        card.style.cursor = 'pointer';
        card.style.background = 'rgba(255,255,255,0.02)';
        card.style.transition = 'all 0.2s';
        
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="font-size:16px;">${cand.bar_time_et} ET</strong>
                <div style="display:flex; gap:8px; align-items:center;">
                    <span style="font-size:12px; color:var(--accent-purple); border:1px solid var(--accent-purple); padding:2px 6px; border-radius:4px;">${(cand.fabio_setup || 'none').replace(/_/g,' ').toUpperCase()}</span>
                    <span style="font-size:12px; color:var(--text-muted);">${cand.day_type.replace(/_/g,' ').toUpperCase()}</span>
                    <span style="color:${decisionColor}; font-weight:bold; padding:4px 8px; border-radius:4px; background:rgba(255,255,255,0.05);">${dirStr}</span>
                </div>
            </div>
            <div class="candidate-details" style="display:none; margin-top:16px; font-size: 14px; border-top:1px solid rgba(255,255,255,0.1); padding-top:16px;">
                <div class="metrics-grid" style="margin-bottom:16px;">
                    <div class="metric-item"><span class="m-label">Volume</span><span class="m-value">${cand.bar_volume.toLocaleString()}</span></div>
                    <div class="metric-item"><span class="m-label">Delta</span>
                        <span class="m-value" style="color:${cand.bar_delta >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                            ${cand.bar_delta > 0 ? '+' : ''}${cand.bar_delta}</span></div>
                    <div class="metric-item"><span class="m-label">Proximity</span>
                        <span class="m-value" style="color:var(--accent-cyan)">${cand.proximity_to.replace(/_/g,' ').toUpperCase()}</span></div>
                    <div class="metric-item"><span class="m-label">Wall</span>
                        <span class="m-value">${cand.wall_max_size} @ ${cand.wall_level}</span></div>
                    ${cand.trade_entry ? `
                    <div class="metric-item"><span class="m-label">Entry</span><span class="m-value" style="color:white">${cand.trade_entry}</span></div>
                    <div class="metric-item"><span class="m-label">Stop Loss</span><span class="m-value" style="color:var(--accent-red)">${cand.trade_stop}</span></div>
                    <div class="metric-item"><span class="m-label">Take Profit</span><span class="m-value" style="color:var(--accent-green)">${cand.trade_target}</span></div>
                    ` : cand.fabio_entry ? `
                    <div class="metric-item"><span class="m-label">Agent Entry</span><span class="m-value" style="color:var(--text-muted)">${cand.fabio_entry}</span></div>
                    <div class="metric-item"><span class="m-label">Agent SL</span><span class="m-value" style="color:var(--text-muted)">${cand.fabio_stop}</span></div>
                    <div class="metric-item"><span class="m-label">Agent TP</span><span class="m-value" style="color:var(--text-muted)">${cand.fabio_target}</span></div>
                    ` : ''}
                </div>

                <div class="agent-block">
                    <div class="agent-header">
                        <div class="agent-avatar fabio-avatar">F</div>
                        <span class="agent-name">Fabio Valentini</span>
                        <span class="confidence-tag">${cand.fabio_confidence}%</span>
                    </div>
                    <div class="reasoning-text"><strong>${cand.fabio_setup}</strong><br><br>${cand.fabio_reasoning}</div>
                    ${cand.market_narrative ? `
                    <div class="narrative-text" style="margin-top:12px; font-size: 13px; color: var(--accent-cyan); border-left: 2px solid var(--accent-cyan); padding-left: 8px;">
                        <strong>Market Narrative Update:</strong><br>${cand.market_narrative.replace(/\\n/g, '<br>')}
                    </div>` : ''}
                </div>

                ${cand.andrea_reasoning ? `
                <div class="agent-block" style="margin-top:12px;">
                    <div class="agent-header">
                        <div class="agent-avatar andrea-avatar">A</div>
                        <span class="agent-name">Andrea Cimi</span>
                        <span class="confidence-tag">${cand.andrea_confidence || '--'}%</span>
                    </div>
                    <div class="reasoning-text">${cand.andrea_reasoning}</div>
                </div>` : ''}
                
                ${cand.no_trade_reason && cand.decision !== 'trade' ? `
                <div style="margin-top:12px; font-size:13px; color:var(--text-muted); font-style:italic;">
                    Veto: ${cand.no_trade_reason}
                </div>` : ''}
                
                <div class="feedback-block" style="margin-top:16px; border-top:1px solid rgba(255,255,255,0.1); padding-top:12px;">
                    <strong style="font-size:13px; color:var(--text-muted);">HUMAN FEEDBACK (FOR RETRAINING)</strong>
                    <textarea class="feedback-input" placeholder="Type your feedback here..." style="width:100%; height:60px; margin-top:8px; background:rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.1); color:white; padding:8px; border-radius:4px; font-family:inherit; resize:vertical;"></textarea>
                    <div style="display:flex; justify-content:space-between; margin-top:8px; align-items:center;">
                        <span class="feedback-status" style="font-size:12px;"></span>
                        <button class="save-feedback-btn" style="background:#00f2fe; color:#0f172a; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:bold;">Save Feedback</button>
                    </div>
                </div>
            </div>
        `;
        
        const details = card.querySelector('.candidate-details');
        
        // Setup feedback saving
        const btn = card.querySelector('.save-feedback-btn');
        const input = card.querySelector('.feedback-input');
        const status = card.querySelector('.feedback-status');
        
        btn.onclick = async (e) => {
            e.stopPropagation(); // prevent card collapse
            const text = input.value.trim();
            if(!text) return;
            
            status.textContent = 'Saving...';
            status.style.color = 'var(--text-muted)';
            
            try {
                const res = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        date: cand.date,
                        bar_time_utc: cand.bar_time_utc,
                        fabio_setup: cand.fabio_setup,
                        decision: cand.decision,
                        feedback_text: text,
                        timestamp: new Date().toISOString()
                    })
                });
                if(res.ok) {
                    status.textContent = 'Saved successfully!';
                    status.style.color = 'var(--accent-green)';
                    setTimeout(() => status.textContent = '', 3000);
                } else {
                    throw new Error('Server error');
                }
            } catch(err) {
                status.textContent = 'Error saving.';
                status.style.color = 'var(--accent-red)';
            }
        };
        
        input.onclick = (e) => e.stopPropagation();
        
        card.onclick = () => {
            const isVisible = details.style.display === 'block';
            
            // Close all others
            container.querySelectorAll('.candidate-details').forEach(el => el.style.display = 'none');
            container.querySelectorAll('.candidate-card').forEach(el => el.style.background = 'rgba(255,255,255,0.02)');
            
            if (!isVisible) {
                details.style.display = 'block';
                card.style.background = 'rgba(255,255,255,0.08)';
                
                // Navigate chart to this bar
                const barTime = new Date(cand.bar_time_utc).getTime() / 1000;
                mainChartObj.timeScale().setVisibleRange({
                    from: barTime - 1800, // 30 mins before
                    to: barTime + 1800    // 30 mins after
                });
            }
        };
        
        container.appendChild(card);
    });
}

// Window resize
window.addEventListener('resize', () => {
    if (mainChartObj) mainChartObj.resize(document.getElementById('mainChart').clientWidth, document.getElementById('mainChart').clientHeight);
    if (deltaChartObj) deltaChartObj.resize(document.getElementById('deltaChart').clientWidth, document.getElementById('deltaChart').clientHeight);
    updateBubblePositions();
    updateVPPositions();
});

// Run init
window.onload = init;
