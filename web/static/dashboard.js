/* ═══════════════════════════════════════════════════════════════
   dashboard.js — FLUXQuant v2.0
   Motor de la UI: TradingView Lightweight Charts + FastAPI backend
═══════════════════════════════════════════════════════════════ */
'use strict';

const API = '';          // mismo origen que FastAPI sirve
const fmt = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtSmall = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 4, maximumFractionDigits: 4 });

// ── Estado global ───────────────────────────────────────────────
const state = {
  symbol:    'BTC-USD',
  timeframe: '1d',
  period:    '1y',
  capital:   10000,
  risk:      1,
  watchlist: JSON.parse(localStorage.getItem('watchlist') || '["BTC-USD","ETH-USD"]'),
  indicators: { ema: true, bb: true, vwap: true, sr: true, fib: true },
  charts: {
    main:    null,
    rsi:     null,
    macd:    null,
    series:  {},          // seriesID → series object (para limpiar)
    lines:   [],          // pricelines S/R, Fib
  },
};

// ── Colores de chart ────────────────────────────────────────────
const C = {
  up:     '#10b981',
  down:   '#ef4444',
  wick:   '#64748b',
  ema9:   '#22d3ee',
  ema21:  '#f59e0b',
  ema50:  '#8b5cf6',
  ema200: '#6366f1',
  bbUp:   'rgba(99,102,241,0.35)',
  bbMid:  'rgba(99,102,241,0.55)',
  bbLow:  'rgba(99,102,241,0.35)',
  vwap:   '#f97316',
  rsi:    '#22d3ee',
  macd:   '#8b5cf6',
  signal: '#f59e0b',
  histUp: 'rgba(16,185,129,0.7)',
  histDn: 'rgba(239,68,68,0.7)',
  sr_res: 'rgba(239,68,68,0.8)',
  sr_sup: 'rgba(16,185,129,0.8)',
  fib:    'rgba(99,102,241,0.7)',
  bg:     '#050810',
  grid:   'rgba(255,255,255,0.04)',
  text:   '#94a3b8',
};

// ── Opciones base de chart ──────────────────────────────────────
function baseChartOpts(height) {
  return {
    layout: {
      background: { color: C.bg },
      textColor: C.text,
      fontSize: 11,
      fontFamily: "'JetBrains Mono', monospace",
    },
    grid: {
      vertLines: { color: C.grid },
      horzLines: { color: C.grid },
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { color: 'rgba(99,102,241,0.4)', labelBackgroundColor: '#6366f1' },
      horzLine: { color: 'rgba(99,102,241,0.4)', labelBackgroundColor: '#6366f1' },
    },
    rightPriceScale: {
      borderColor: 'rgba(255,255,255,0.06)',
      textColor:   C.text,
    },
    timeScale: {
      borderColor:     'rgba(255,255,255,0.06)',
      timeVisible:     true,
      secondsVisible:  false,
    },
    handleScroll: true,
    handleScale:  true,
  };
}

// ═══════════════════════════════════════════════════════════════
// INICIALIZACIÓN DE CHARTS
// ═══════════════════════════════════════════════════════════════
function initCharts() {
  const elMain = document.getElementById('chart-main');
  const elRsi  = document.getElementById('chart-rsi');
  const elMacd = document.getElementById('chart-macd');

  // Destruir charts previos
  if (state.charts.main) { state.charts.main.remove(); }
  if (state.charts.rsi)  { state.charts.rsi.remove();  }
  if (state.charts.macd) { state.charts.macd.remove(); }

  state.charts.series = {};
  state.charts.lines  = [];

  // ── Chart principal (candlestick + volumen + indicadores) ──
  state.charts.main = LightweightCharts.createChart(elMain, {
    ...baseChartOpts(),
    width:  elMain.offsetWidth,
    height: elMain.offsetHeight,
  });

  // ── Chart RSI ──
  state.charts.rsi = LightweightCharts.createChart(elRsi, {
    ...baseChartOpts(),
    width:  elRsi.offsetWidth,
    height: elRsi.offsetHeight,
    rightPriceScale: { scaleMargins: { top: 0.05, bottom: 0.05 } },
  });

  // ── Chart MACD ──
  state.charts.macd = LightweightCharts.createChart(elMacd, {
    ...baseChartOpts(),
    width:  elMacd.offsetWidth,
    height: elMacd.offsetHeight,
    rightPriceScale: { scaleMargins: { top: 0.1, bottom: 0.1 } },
  });

  // Sincronizar crosshairs en los 3 charts
  [state.charts.main, state.charts.rsi, state.charts.macd].forEach(srcChart => {
    srcChart.subscribeCrosshairMove(param => {
      [state.charts.main, state.charts.rsi, state.charts.macd].forEach(dstChart => {
        if (srcChart !== dstChart) {
          if (param.time) dstChart.setCrosshairPosition(param.time, 0, null);
          else dstChart.clearCrosshairPosition();
        }
      });
    });
  });

  // Sincronizar scroll/zoom
  let syncBusy = false;
  state.charts.main.timeScale().subscribeVisibleLogicalRangeChange(range => {
    if (syncBusy || !range) return;
    syncBusy = true;
    state.charts.rsi.timeScale().setVisibleLogicalRange(range);
    state.charts.macd.timeScale().setVisibleLogicalRange(range);
    syncBusy = false;
  });

  // Resize observer
  const ro = new ResizeObserver(() => {
    state.charts.main.applyOptions({ width: elMain.offsetWidth, height: elMain.offsetHeight });
    state.charts.rsi.applyOptions({ width: elRsi.offsetWidth, height: elRsi.offsetHeight });
    state.charts.macd.applyOptions({ width: elMacd.offsetWidth, height: elMacd.offsetHeight });
  });
  ro.observe(elMain);
  ro.observe(elRsi);
  ro.observe(elMacd);
}

// ═══════════════════════════════════════════════════════════════
// CARGA DE DATOS
// ═══════════════════════════════════════════════════════════════
async function loadAll() {
  const { symbol, timeframe, period, capital, risk } = state;

  setStatus('loading', 'Descargando…');

  try {
    // Paralelo: OHLCV + indicadores + análisis
    const [ohlcvRes, indRes, analRes] = await Promise.all([
      fetchJSON(`/api/ohlcv/${symbol}?timeframe=${timeframe}&period=${period}`),
      fetchJSON(`/api/indicators/${symbol}?timeframe=${timeframe}&period=${period}`),
      fetchJSON(`/api/analysis/${symbol}?timeframe=${timeframe}&period=${period}&capital=${capital}&risk=${risk}`),
    ]);

    renderCandles(ohlcvRes);
    renderIndicators(indRes);
    renderAnalysis(analRes);
    renderPriceBar(ohlcvRes, analRes);
    updateFooterTs();
    setStatus('ok', `${symbol} ✓`);

  } catch (err) {
    setStatus('error', 'Error de carga');
    showToast(`Error: ${err.message}`);
    console.error(err);
  }
}

// ── Fetch helper ────────────────────────────────────────────────
async function fetchJSON(url) {
  const res = await fetch(API + url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}

// ═══════════════════════════════════════════════════════════════
// RENDER: VELAS + VOLUMEN
// ═══════════════════════════════════════════════════════════════
function renderCandles(data) {
  const chart = state.charts.main;

  // Limpiar series anteriores
  Object.values(state.charts.series).forEach(s => { try { chart.removeSeries(s); } catch {} });
  state.charts.lines.forEach(l => { try { chart.removePriceLine(l); } catch {} });
  state.charts.series = {};
  state.charts.lines  = [];

  const candles = data.candles.filter(c => c.open && c.close);

  // ── Candlestick ──
  const candleSeries = chart.addCandlestickSeries({
    upColor:          C.up,
    downColor:        C.down,
    borderUpColor:    C.up,
    borderDownColor:  C.down,
    wickUpColor:      C.up,
    wickDownColor:    C.down,
  });
  candleSeries.setData(candles.map(c => ({
    time: c.time, open: c.open, high: c.high, low: c.low, close: c.close,
  })));
  state.charts.series.candle = candleSeries;

  // ── Volumen (histograma en escala separada) ──
  const volSeries = chart.addHistogramSeries({
    color: 'rgba(99,102,241,0.3)',
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
  });
  chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
  volSeries.setData(candles.map(c => ({
    time:  c.time,
    value: c.volume,
    color: c.close >= c.open ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.2)',
  })));
  state.charts.series.volume = volSeries;

  // Ajustar vista al final
  chart.timeScale().scrollToRealTime();
}

// ═══════════════════════════════════════════════════════════════
// RENDER: INDICADORES
// ═══════════════════════════════════════════════════════════════
function renderIndicators(data) {
  const chart = state.charts.main;

  // ── EMAs ──
  if (state.indicators.ema) {
    const emaCfg = [
      { key: 'EMA_9',   color: C.ema9,   lw: 1   },
      { key: 'EMA_21',  color: C.ema21,  lw: 1   },
      { key: 'EMA_50',  color: C.ema50,  lw: 1.5 },
      { key: 'EMA_200', color: C.ema200, lw: 2   },
    ];
    emaCfg.forEach(({ key, color, lw }) => {
      const s = chart.addLineSeries({ color, lineWidth: lw, priceLineVisible: false, lastValueVisible: false });
      s.setData(data.emas[key] || []);
      state.charts.series[key] = s;
    });
    buildLegend([
      { label: 'EMA9',  color: C.ema9 }, { label: 'EMA21', color: C.ema21 },
      { label: 'EMA50', color: C.ema50 }, { label: 'EMA200', color: C.ema200 },
    ]);
  }

  // ── Bollinger Bands ──
  if (state.indicators.bb) {
    const bbUp  = chart.addLineSeries({ color: C.bbUp,  lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
    const bbMid = chart.addLineSeries({ color: C.bbMid, lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
    const bbLow = chart.addLineSeries({ color: C.bbLow, lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false });
    bbUp.setData(data.bollinger.upper);
    bbMid.setData(data.bollinger.middle);
    bbLow.setData(data.bollinger.lower);
    state.charts.series.bbUp  = bbUp;
    state.charts.series.bbMid = bbMid;
    state.charts.series.bbLow = bbLow;
  }

  // ── VWAP ──
  if (state.indicators.vwap) {
    const vwapS = chart.addLineSeries({ color: C.vwap, lineWidth: 2, lineStyle: 0, priceLineVisible: false, lastValueVisible: true, title: 'VWAP' });
    vwapS.setData(data.vwap);
    state.charts.series.vwap = vwapS;
  }

  // ── RSI ──
  const rsiChart = state.charts.rsi;
  Object.values(state.charts.series).filter(s => s._rsi).forEach(s => rsiChart.removeSeries(s));

  const rsiSeries = rsiChart.addLineSeries({ color: C.rsi, lineWidth: 2, priceLineVisible: false });
  rsiSeries.setData(data.rsi);
  rsiSeries._rsi = true;
  state.charts.series.rsi = rsiSeries;

  // Líneas de sobrecompra/sobreventa en RSI
  [70, 50, 30].forEach(lvl => {
    rsiSeries.createPriceLine({ price: lvl, color: lvl === 50 ? '#4a5568' : (lvl === 70 ? C.down : C.up), lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `${lvl}` });
  });

  // ── MACD ──
  const macdChart = state.charts.macd;
  const macdLine   = macdChart.addLineSeries({ color: C.macd,   lineWidth: 2, priceLineVisible: false, title: 'MACD' });
  const sigLine    = macdChart.addLineSeries({ color: C.signal,  lineWidth: 2, priceLineVisible: false, title: 'Signal' });
  const histSeries = macdChart.addHistogramSeries({ priceLineVisible: false, title: 'Hist' });
  macdLine.setData(data.macd.macd);
  sigLine.setData(data.macd.signal);
  histSeries.setData(data.macd.histogram.map(d => ({
    ...d, color: (d.value >= 0) ? C.histUp : C.histDn,
  })));
  state.charts.series.macdLine = macdLine;
  state.charts.series.sigLine  = sigLine;
  state.charts.series.hist     = histSeries;
}

// ═══════════════════════════════════════════════════════════════
// RENDER: ANÁLISIS (S/R, Fibonacci, FVG, etc.)
// ═══════════════════════════════════════════════════════════════
function renderAnalysis(data) {
  const chart = state.charts.main;

  // ── Soportes & Resistencias como price lines ──
  if (state.indicators.sr) {
    (data.sr_levels || []).slice(0, 12).forEach(lvl => {
      if (!lvl.price) return;
      const isRes = lvl.type === 'resistance';
      const pl = state.charts.series.candle?.createPriceLine({
        price:              lvl.price,
        color:              isRes ? C.sr_res : C.sr_sup,
        lineWidth:          1,
        lineStyle:          LightweightCharts.LineStyle.Dashed,
        axisLabelVisible:   true,
        title:              isRes ? `R ${fmt.format(lvl.price)}` : `S ${fmt.format(lvl.price)}`,
      });
      if (pl) state.charts.lines.push(pl);
    });
  }

  // ── Fibonacci ──
  if (state.indicators.fib) {
    (data.fib_levels || []).slice(0, 8).forEach(lvl => {
      if (!lvl.price) return;
      const pl = state.charts.series.candle?.createPriceLine({
        price:            lvl.price,
        color:            C.fib,
        lineWidth:        1,
        lineStyle:        LightweightCharts.LineStyle.SparseDotted,
        axisLabelVisible: true,
        title:            `Fib ${lvl.label}`,
      });
      if (pl) state.charts.lines.push(pl);
    });
  }

  // ── Cards del sidebar ──
  renderQuantCard(data);
  renderReversionCard(data);
  renderSetupCard(data);
  renderIndicatorsCard(data);
  renderVolatilityCard(data);
  renderStructureCard(data);
  renderSRCard(data);
  renderFibCard(data);
}

// ═══════════════════════════════════════════════════════════════
// RENDER: PRICE BAR
// ═══════════════════════════════════════════════════════════════
function renderPriceBar(ohlcv, analysis) {
  const candles = ohlcv.candles.filter(c => c.close);
  if (!candles.length) return;

  const last  = candles[candles.length - 1];
  const prev  = candles[candles.length - 2] || last;
  const chg   = ((last.close - prev.close) / prev.close) * 100;
  const up    = last.close >= prev.close;

  document.getElementById('pb-symbol').textContent = ohlcv.symbol;
  document.getElementById('pb-price').textContent  = `$${fmt.format(last.close)}`;

  const pbChange = document.getElementById('pb-change');
  pbChange.textContent = `${up ? '▲' : '▼'} ${fmt.format(Math.abs(chg))}%`;
  pbChange.className   = `price-bar__change ${up ? 'up' : 'down'}`;

  // Señal
  const dir    = analysis.direction || 'NEUTRAL';
  const buyS   = analysis.score_buy  || 0;
  const sellS  = analysis.score_sell || 0;
  const sigEl  = document.getElementById('pb-signal');
  sigEl.innerHTML = `<span class="signal-badge ${dir === 'COMPRA' ? 'buy' : dir === 'VENTA' ? 'sell' : 'neutral'}">${dir} · ${Math.round(Math.max(buyS, sellS))}/100</span>`;

  document.getElementById('pb-meta').textContent =
    `${ohlcv.timeframe.toUpperCase()} · ${analysis.date || ''} · ATR ${analysis.volatility?.atr_pct?.toFixed(2) || '—'}%`;
}

// ═══════════════════════════════════════════════════════════════
// CARDS DEL SIDEBAR
// ═══════════════════════════════════════════════════════════════
function renderSetupCard(data) {
  const s = data.setup || {};
  const buyScore  = data.score_buy  || 0;
  const sellScore = data.score_sell || 0;
  const isBuy = buyScore >= sellScore;

  document.getElementById('setup-body').innerHTML = `
    <div class="data-row">
      <span class="data-row__label">Dirección</span>
      <span class="data-row__value">
        <span class="signal-badge ${data.direction === 'COMPRA' ? 'buy' : data.direction === 'VENTA' ? 'sell' : 'neutral'}">${data.direction || '—'}</span>
      </span>
    </div>
    <div class="score-bar-wrap">
      <div class="score-bar-label"><span>Compra</span><span>${buyScore.toFixed(1)}/100</span></div>
      <div class="score-bar-track"><div class="score-bar-fill buy" style="width:${buyScore}%"></div></div>
    </div>
    <div class="score-bar-wrap" style="margin-top:4px">
      <div class="score-bar-label"><span>Venta</span><span>${sellScore.toFixed(1)}/100</span></div>
      <div class="score-bar-track"><div class="score-bar-fill sell" style="width:${sellScore}%"></div></div>
    </div>
    ${row('Entrada', fmt2(s.entry))}
    ${row('Stop Loss', fmt2(s.stop_loss), 'down')}
    ${row('TP 1', fmt2(s.take_profit_1), 'up')}
    ${row('TP 2', fmt2(s.take_profit_2), 'up')}
    ${row('Tamaño pos.', s.position_size ?? '—')}
    ${row('Pérdida máx.', s.max_loss_usd ? '$'+fmt.format(s.max_loss_usd) : '—', 'down')}
    ${row('R:R', s.rr_tp1 ? `${s.rr_tp1} / ${s.rr_tp2}` : '—', 'accent')}
  `;
}

function renderQuantCard(data) {
  const q = data.quant || {};
  if (!q.direction || q.error) {
    document.getElementById('quant-body').innerHTML = '<div style="color:var(--text-muted);font-size:11px">Datos insuficientes o error en Quant</div>';
    return;
  }
  
  const f = q.fourier || {};
  const of = q.order_flow || {};
  const ml = q.ml_data || {};
  
  document.getElementById('quant-body').innerHTML = `
    <div class="data-row" style="margin-bottom:8px">
      <span class="data-row__label">Dirección AI</span>
      <span class="data-row__value">
        <span class="signal-badge ${q.direction.includes('COMPRA') ? 'buy' : q.direction.includes('VENTA') ? 'sell' : 'neutral'}">${q.direction}</span>
      </span>
    </div>
    <div class="score-bar-wrap" style="margin-bottom:12px">
      <div class="score-bar-label"><span>Probabilidad Win</span><span style="color:var(--cyan)">${q.win_probability.toFixed(1)}%</span></div>
      <div class="score-bar-track"><div class="score-bar-fill" style="width:${q.win_probability}%; background:linear-gradient(90deg, #22d3ee, #8b5cf6)"></div></div>
    </div>
    ${row('Fase Fourier', f.phase || '—', f.phase?.includes('Alcista') ? 'up' : f.phase?.includes('Bajista') ? 'down' : 'neutral')}
    ${row('Order Flow', of.state || '—', of.score > 0 ? 'up' : of.score < 0 ? 'down' : 'neutral')}
    ${row('Machine Learning (RF)', ml.status || '—', ml.ml_score > 0 ? 'up' : ml.ml_score < 0 ? 'down' : 'neutral')}
    <div style="margin-top:10px; padding-top:10px; border-top:1px dashed rgba(255,255,255,0.1)"></div>
    ${row('Entrada', fmt2(q.entry), 'accent')}
    ${row('Stop Loss', fmt2(q.stop_loss), 'down')}
    ${row('Take Profit 1', fmt2(q.take_profit_1), 'up')}
    ${row('Take Profit 2', fmt2(q.take_profit_2), 'up')}
    ${row('Posición Sugerida', q.position_size ? q.position_size.toFixed(4) : '—')}
  `;
}

function renderReversionCard(data) {
  const r = data.mean_reversion || {};
  if (!r.signal_type || r.error) {
    document.getElementById('reversion-body').innerHTML = '<div style="color:var(--text-muted);font-size:11px">Datos insuficientes o error en Reversión</div>';
    return;
  }
  
  document.getElementById('reversion-body').innerHTML = `
    <div class="data-row" style="margin-bottom:8px">
      <span class="data-row__label">Señal Reversión</span>
      <span class="data-row__value">
        <span class="signal-badge ${r.signal_type.includes('Largo') ? 'buy' : r.signal_type.includes('Corto') ? 'sell' : 'neutral'}">${r.signal_type}</span>
      </span>
    </div>
    ${row('Z-Score (VWAP)', r.z_score !== undefined ? r.z_score.toFixed(2) : '—', r.z_score > 2 ? 'up' : r.z_score < -2 ? 'down' : 'neutral')}
    ${row('VWAP', r.vwap ? '$'+fmt.format(r.vwap) : '—')}
    ${row('Half-Life (Barras)', r.half_life_bars || '—')}
    ${row('Régimen', r.is_mean_reverting_regime ? 'Reversión a la media' : 'Tendencial', r.is_mean_reverting_regime ? 'accent' : 'neutral')}
    ${row('Objetivo (VWAP)', r.target_price ? '$'+fmt.format(r.target_price) : '—')}
  `;
}

function renderIndicatorsCard(data) {
  const ind = data.indicators || {};
  const rsi = ind.rsi;
  document.getElementById('indicators-body').innerHTML = `
    ${row('RSI (14)', rsi ? rsi.toFixed(2) : '—', rsiColor(rsi))}
    ${row('MACD', ind.macd ? fmtSmall.format(ind.macd) : '—')}
    ${row('ADX', ind.adx ? ind.adx.toFixed(1) : '—')}
    ${row('Stoch %K', ind.stoch_k ? ind.stoch_k.toFixed(1) : '—', rsiColor(ind.stoch_k))}
  `;
}

function renderVolatilityCard(data) {
  const v = data.volatility || {};
  document.getElementById('volatility-body').innerHTML = `
    ${row('ATR', v.atr ? '$'+fmt.format(v.atr) : '—')}
    ${row('ATR %', v.atr_pct ? v.atr_pct.toFixed(2)+'%' : '—')}
    ${row('Régimen', v.regime || '—', v.regime === 'ALTA' ? 'down' : v.regime === 'BAJA' ? 'up' : 'neutral')}
  `;
}

function renderStructureCard(data) {
  const ms = data.market_structure || {};
  const trend = ms.trend?.toUpperCase() || '—';
  document.getElementById('structure-body').innerHTML = `
    ${row('Tendencia', trend, trend === 'ALCISTA' ? 'up' : trend === 'BAJISTA' ? 'down' : 'neutral')}
    ${row('Último BOS', ms.last_bos ?? '—')}
    ${row('Último CHoCH', ms.last_choch ?? '—')}
  `;
}

function renderSRCard(data) {
  const levels = (data.sr_levels || []).slice(0, 10);
  if (!levels.length) { document.getElementById('sr-body').innerHTML = '<div style="color:var(--text-muted);font-size:11px">Sin datos</div>'; return; }
  document.getElementById('sr-body').innerHTML = `
    <div class="level-list">
      ${levels.map(l => `
        <div class="level-item ${l.type === 'resistance' ? 'resistance' : 'support'}">
          <span>${l.type === 'resistance' ? '↑ R' : '↓ S'}</span>
          <span>$${fmt.format(l.price)}</span>
        </div>`).join('')}
    </div>`;
}

function renderFibCard(data) {
  const levels = (data.fib_levels || []).slice(0, 8);
  if (!levels.length) { document.getElementById('fib-body').innerHTML = '<div style="color:var(--text-muted);font-size:11px">Sin datos</div>'; return; }
  document.getElementById('fib-body').innerHTML = `
    <div class="level-list">
      ${levels.map(l => `
        <div class="level-item fib">
          <span>${l.label}</span>
          <span>$${fmt.format(l.price)}</span>
        </div>`).join('')}
    </div>`;
}

// ── Helpers de render ────────────────────────────────────────────
function row(label, value, cls = '') {
  return `<div class="data-row">
    <span class="data-row__label">${label}</span>
    <span class="data-row__value ${cls}">${value ?? '—'}</span>
  </div>`;
}
function fmt2(v) { return v ? '$'+fmt.format(v) : '—'; }
function rsiColor(v) { if (!v) return ''; return v > 70 ? 'down' : v < 30 ? 'up' : 'neutral'; }

function buildLegend(items) {
  const el = document.getElementById('chart-overlay-legend');
  el.innerHTML = items.map(i =>
    `<div class="legend-item">
       <div class="legend-dot" style="background:${i.color}"></div>
       <span>${i.label}</span>
     </div>`
  ).join('');
}

// ═══════════════════════════════════════════════════════════════
// WATCHLIST
// ═══════════════════════════════════════════════════════════════
function renderWatchlist() {
  const ul = document.getElementById('watchlist');
  ul.innerHTML = state.watchlist.map(sym => `
    <li class="watchlist-item ${sym === state.symbol ? 'active' : ''}" data-sym="${sym}">
      <span class="watchlist-item__symbol">${sym}</span>
      <span class="watchlist-item__change" id="wl-${sym}">…</span>
    </li>`).join('');

  ul.querySelectorAll('.watchlist-item').forEach(li => {
    li.addEventListener('click', () => {
      state.symbol = li.dataset.sym;
      document.getElementById('inp-symbol').value = state.symbol;
      renderWatchlist();
      loadAll();
    });
  });

  // Cargar datos de watchlist en segundo plano
  state.watchlist.forEach(async sym => {
    try {
      const d = await fetchJSON(`/api/ohlcv/${sym}?timeframe=1d&period=5d`);
      const c = d.candles.filter(x => x.close);
      if (c.length >= 2) {
        const chg = ((c[c.length-1].close - c[c.length-2].close) / c[c.length-2].close) * 100;
        const el  = document.getElementById(`wl-${sym}`);
        if (el) {
          el.textContent = `${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`;
          el.className   = `watchlist-item__change ${chg >= 0 ? 'up' : 'down'}`;
        }
      }
    } catch {}
  });
}

function saveWatchlist() {
  localStorage.setItem('watchlist', JSON.stringify(state.watchlist));
}

// ═══════════════════════════════════════════════════════════════
// UTILIDADES UI
// ═══════════════════════════════════════════════════════════════
function setStatus(kind, text) {
  document.getElementById('status-dot').className  = `status-dot status-dot--${kind}`;
  document.getElementById('status-text').textContent = text;
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), 4000);
}

function updateFooterTs() {
  document.getElementById('footer-ts').textContent =
    `Última actualización: ${new Date().toLocaleTimeString('es-MX')}`;
}

// ═══════════════════════════════════════════════════════════════
// EVENTOS
// ═══════════════════════════════════════════════════════════════
function bindEvents() {
  // Botón cargar
  document.getElementById('btn-load').addEventListener('click', () => {
    state.symbol    = document.getElementById('inp-symbol').value.trim().toUpperCase();
    state.timeframe = document.getElementById('sel-tf').value;
    state.period    = document.getElementById('sel-period').value;
    state.capital   = parseFloat(document.getElementById('inp-capital').value) || 10000;
    state.risk      = parseFloat(document.getElementById('inp-risk').value)    || 1;
    renderWatchlist();
    loadAll();
  });

  // Auto-recargar al cambiar comboboxes
  ['sel-tf', 'sel-period'].forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
      document.getElementById('btn-load').click();
    });
  });

  // Enter en input de símbolo
  document.getElementById('inp-symbol').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-load').click();
  });

  // Toggles de indicadores
  document.querySelectorAll('.ind-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const ind = btn.dataset.ind;
      state.indicators[ind] = !state.indicators[ind];
      btn.classList.toggle('active', state.indicators[ind]);
      loadAll();   // recargar con el indicador on/off
    });
  });

  // Watchlist add
  document.getElementById('btn-add-watch').addEventListener('click', () => {
    document.getElementById('watchlist-add').classList.toggle('hidden');
    document.getElementById('inp-watch').focus();
  });
  document.getElementById('btn-watch-confirm').addEventListener('click', () => {
    const sym = document.getElementById('inp-watch').value.trim().toUpperCase();
    if (sym && !state.watchlist.includes(sym)) {
      state.watchlist.push(sym);
      saveWatchlist();
      renderWatchlist();
    }
    document.getElementById('watchlist-add').classList.add('hidden');
    document.getElementById('inp-watch').value = '';
  });
  document.getElementById('inp-watch').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-watch-confirm').click();
  });

  // Auto-refresh cada 60 segundos
  setInterval(() => {
    if (document.visibilityState === 'visible') loadAll();
  }, 60_000);
}

// ═══════════════════════════════════════════════════════════════
// ARRANQUE
// ═══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  bindEvents();
  renderWatchlist();
  loadAll();
});
