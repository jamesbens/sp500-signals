/* S&P 500: price with 50/200-day SMAs, green entry / red exit markers, and an RSI panel. */
(function () {
  const { theme, fetchFirst, tooltipBase, onRerender, fmt } = window.PortfolioCharts;

  function option(d, t, compact) {
    const dates = d.series.date;
    const pos = new Map(dates.map((x, i) => [x, i]));
    const bySignalDate = new Map(d.signals.map((s) => [s.date, s]));
    const pts = (type) =>
      d.signals.filter((s) => s.type === type).map((s) => ({ value: [pos.get(s.date), s.close], signal: s }));
    const rsiCfg = d.meta.strategy;
    const oversold = parseFloat(rsiCfg.entry_rule.split("above ")[1]);
    const overbought = parseFloat(rsiCfg.exit_rule.split("below ")[1]);

    const axisCommon = {
      axisLine: { lineStyle: { color: t.axis } },
      axisTick: { show: false },
      axisLabel: { color: t.muted, fontFamily: t.font, fontSize: 11 },
      splitLine: { lineStyle: { color: t.grid } },
    };
    const markerCommon = (color, rotate) => ({
      type: "scatter", xAxisIndex: 0, yAxisIndex: 0, symbol: "triangle", symbolSize: compact ? 12 : 15,
      symbolRotate: rotate, z: 10,
      itemStyle: { color, borderColor: t.surface, borderWidth: 2 },
      emphasis: { scale: 1.4 },
    });

    return {
      animationDuration: 900,
      textStyle: { fontFamily: t.font },
      grid: [
        { left: 56, right: compact ? 12 : 24, top: 16, height: "58%" },
        { left: 56, right: compact ? 12 : 24, top: "72%", height: "14%" },
      ],
      axisPointer: { link: [{ xAxisIndex: "all" }], label: { backgroundColor: t.ink2 } },
      tooltip: {
        ...tooltipBase(t),
        trigger: "axis",
        axisPointer: { type: "cross", lineStyle: { color: t.muted, type: "dashed" }, crossStyle: { color: t.muted } },
        formatter(params) {
          const i = params[0].dataIndex;
          const date = dates[i];
          const s = bySignalDate.get(date);
          const row = (label, value, color) =>
            `<div style="display:flex;justify-content:space-between;gap:18px"><span style="color:${t.ink2}">${
              color ? `<i style="display:inline-block;width:10px;height:2px;background:${color};vertical-align:middle;margin-right:6px"></i>` : ""
            }${label}</span><b>${value}</b></div>`;
          let html = `<div style="font-weight:700;margin-bottom:6px">${fmt.date(date)}</div>`;
          html += row("Close", fmt.num(d.series.close[i], 2), t.s1);
          html += row("50-day SMA", fmt.num(d.series.sma_fast[i], 0), t.smaFast);
          html += row("200-day SMA", fmt.num(d.series.sma_slow[i], 0), t.smaSlow);
          html += row("RSI(14)", fmt.num(d.series.rsi[i], 1));
          if (s) {
            const c = s.type === "entry" ? t.entry : t.exit;
            html += `<div style="margin-top:8px;padding-top:8px;border-top:1px solid ${t.axis};color:${c};font-weight:700">${
              s.type === "entry" ? "▲ ENTRY" : "▼ EXIT"
            }</div><div style="color:${t.ink2};font-size:12px">${s.reason}</div>`;
          }
          return html;
        },
      },
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
        {
          type: "slider", xAxisIndex: [0, 1], bottom: 6, height: 22, borderColor: t.axis,
          backgroundColor: "transparent", fillerColor: "rgba(79,143,247,0.15)",
          dataBackground: { lineStyle: { color: t.muted }, areaStyle: { color: t.grid } },
          handleStyle: { color: t.s1 }, textStyle: { color: t.muted },
          labelFormatter: (i) => (dates[i] ? dates[i].slice(0, 7) : ""),
        },
      ],
      xAxis: [
        { ...axisCommon, type: "category", data: dates, gridIndex: 0, boundaryGap: false, splitLine: { show: false },
          axisLabel: { ...axisCommon.axisLabel, formatter: (v) => v.slice(0, 7) } },
        { ...axisCommon, type: "category", data: dates, gridIndex: 1, boundaryGap: false, axisLabel: { show: false }, splitLine: { show: false } },
      ],
      yAxis: [
        { ...axisCommon, type: "value", scale: true, gridIndex: 0, axisLine: { show: false },
          axisLabel: { ...axisCommon.axisLabel, formatter: (v) => fmt.num(v) } },
        { ...axisCommon, type: "value", gridIndex: 1, min: 0, max: 100, interval: 50, axisLine: { show: false },
          name: "RSI", nameLocation: "middle", nameGap: 36, nameTextStyle: { color: t.muted, fontSize: 11 } },
      ],
      series: [
        { name: "S&P 500 close", type: "line", data: d.series.close, showSymbol: false, lineStyle: { width: 2, color: t.s1 },
          itemStyle: { color: t.s1 },
          areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: t.s1 + "33" }, { offset: 1, color: t.s1 + "00" }] } } },
        { name: "50-day SMA", type: "line", data: d.series.sma_fast, showSymbol: false, lineStyle: { width: 1.5, color: t.smaFast }, itemStyle: { color: t.smaFast } },
        { name: "200-day SMA", type: "line", data: d.series.sma_slow, showSymbol: false, lineStyle: { width: 1.5, color: t.smaSlow, type: [6, 4] }, itemStyle: { color: t.smaSlow } },
        { name: "Entry", ...markerCommon(t.entry, 0), data: pts("entry") },
        { name: "Exit", ...markerCommon(t.exit, 180), data: pts("exit") },
        { name: "RSI", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: d.series.rsi, showSymbol: false,
          lineStyle: { width: 1.5, color: t.ink2 }, itemStyle: { color: t.ink2 },
          markLine: { silent: true, symbol: "none", label: { color: t.muted, fontSize: 10, formatter: "{c}" },
            data: [ { yAxis: overbought, lineStyle: { color: t.exit, type: "dashed", width: 1 } },
                    { yAxis: oversold, lineStyle: { color: t.entry, type: "dashed", width: 1 } } ] },
          markArea: { silent: true, data: [
            [{ yAxis: overbought, itemStyle: { color: t.exit, opacity: 0.08 } }, { yAxis: 100 }],
            [{ yAxis: 0, itemStyle: { color: t.entry, opacity: 0.08 } }, { yAxis: oversold }] ] } },
      ],
    };
  }

  function renderKpis(el, d) {
    const b = d.backtest, s = b.strategy, h = b.buy_and_hold;
    el.innerHTML = [
      ["Trades (5y)", b.trades, `Win rate ${fmt.pct(b.win_rate, 0)}`],
      ["Avg trade return", fmt.pct(b.avg_trade_return), b.open_position ? "Position open now" : "Currently flat"],
      ["Max drawdown", fmt.pct(s.max_drawdown), `Buy & hold ${fmt.pct(h.max_drawdown)}`],
      ["Total return", fmt.pct(s.total_return), `Buy & hold ${fmt.pct(h.total_return)} · ${fmt.pct(s.exposure, 0)} time in market`],
    ].map(([k, v, sub]) => `<div class="kpi"><span>${k}</span><b>${v}</b><small>${sub}</small></div>`).join("");
  }

  window.renderSp500 = async function ({ chartEl, kpiEl, noteEl, sources }) {
    let chart;
    try {
      const { data } = await fetchFirst(sources);
      chart = echarts.init(chartEl, null, { renderer: "canvas" });
      const draw = () => chart.setOption(option(data, theme(), chartEl.clientWidth < 640), true);
      draw();
      onRerender(draw);
      new ResizeObserver(() => { chart.resize(); }).observe(chartEl);
      if (kpiEl) renderKpis(kpiEl, data);
      if (noteEl) {
        noteEl.textContent = `${data.meta.strategy.entry_rule} → entry · ${data.meta.strategy.exit_rule} → exit · ` +
          `Data ${fmt.date(data.meta.start)} – ${fmt.date(data.meta.end)} from ${data.meta.source}, refreshed every trading day by GitHub Actions. ` +
          data.meta.disclaimer;
      }
    } catch (err) {
      chartEl.innerHTML = `<p class="chart-note">Chart data could not be loaded (${err.message}).</p>`;
    }
  };
})();
