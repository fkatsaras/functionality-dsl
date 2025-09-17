<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribe as wsSubscribe } from "../ws";
  import RefreshButton from "./util/RefreshButton.svelte";

  const {
    name = "LineChart",
    url,
    wsUrl,
    xSpec,
    ySpec,
    xLabel,
    yLabel,
    windowSize: _windowSize = 0,
    refreshMs = 0,
    height = 1000,
    seriesLabels: _seriesLabels = null as null | string[],
    seriesColors: _seriesColors = null as null | string[],
  } = $props<{
    name?: string;
    url?: string;
    wsUrl?: string;
    xSpec: string | number[];                 // <- if array: MUST be number[]
    ySpec: string | number[] | number[][];    // <- arrays MUST be number[]
    xLabel?: string;
    yLabel?: string;
    windowSize?: number | null;
    refreshMs?: number;
    height?: number;
    seriesLabels?: string[] | null;
    seriesColors?: string[] | null;
  }>();

  // type guards
  const isNumberArray = (a: unknown): a is number[] =>
    Array.isArray(a) && a.every(v => typeof v === "number" && Number.isFinite(v));
  
  const isNumberArrayArray = (a: unknown): a is number[][] =>
    Array.isArray(a) && a.length > 0 && a.every(isNumberArray);

  const isStringArray = (a: unknown): a is string[] =>
    Array.isArray(a) && a.every(v => typeof v === "string");

  let loading: boolean = $state(Boolean(url));
  let error: string | null = null;
  const windowSize = Number(_windowSize ?? 0);

  // --- normalize ySpec into either: list of keys (string[]) OR list of numeric arrays (number[][])
  function normalizeYSpec(spec: any): string[] | number[][] {
    if (Array.isArray(spec)) {
      if (spec.length > 0 && Array.isArray(spec[0])) return spec as number[][];
      return spec as any[]; // either number[] OR string[]
    }
    return [spec]; // single key or single numeric array
  }
  const ySpecNorm = normalizeYSpec(ySpec);

  // --- series container
  type Point = { t: number; y: number };
  let series: Record<string, Point[]> = $state({});

  // --- decide legend keys + boot empty series
  let yKeysForLegend: string[] = [];
  const isDirectSingleNumeric = isNumberArray(ySpecNorm);
  const isDirectMultiNumeric  = isNumberArrayArray(ySpecNorm);
  if (isDirectSingleNumeric) {
    yKeysForLegend = ["series1"];
  } else if (isDirectMultiNumeric) {
    yKeysForLegend = (ySpecNorm as number[][]).map((_, i) => `series${i+1}`);
  } else {
    yKeysForLegend = (ySpecNorm as string[]); // keys
  }
  for (const k of yKeysForLegend) series[k] = [];

  // --- legend labels/colors
  const defaultPalette = ["#3b82f6", "#22c55e", "#f97316", "#e11d48", "#a855f7", "#14b8a6"];
  const seriesLabels = _seriesLabels && _seriesLabels.length === yKeysForLegend.length
    ? _seriesLabels
    : yKeysForLegend.map(k => String(k).toUpperCase());
  const seriesColors = _seriesColors && _seriesColors.length === yKeysForLegend.length
    ? _seriesColors
    : yKeysForLegend.map((_, i) => defaultPalette[i % defaultPalette.length]);

  // --- helpers: NO normalization — enforce numbers
  const isNum = (v: any) => Number.isFinite(v);
  function assertNumArray(arr: any, where: string): asserts arr is number[] {
    if (!Array.isArray(arr) || !arr.every(isNum)) {
      throw new Error(`${where} must be an array of numbers`);
    }
  }

  function resetSeries() {
    for (const k of yKeysForLegend) series[k] = [];
  }

  // --- core pairing by INDEX (no guessing)
  function ingestArrays(xArr: number[], yArrs: number[][], labelKeys: string[]) {
    assertNumArray(xArr, "xSpec");
    for (let i = 0; i < yArrs.length; i++) assertNumArray(yArrs[i], `ySpec[${i}]`);

    const n = Math.min(xArr.length, ...yArrs.map(a => a.length));
    for (let i = 0; i < n; i++) {
      const t = xArr[i];
      for (let s = 0; s < yArrs.length; s++) {
        const v = yArrs[s][i];
        const key = labelKeys[s];
        const next = [...(series[key] || []), { t, y: v }];
        series[key] = windowSize > 0 ? next.slice(-windowSize) : next;
      }
    }
  }

  // --- push data either from payload keys, or directly from provided arrays
  function pushPayload(payload: any, { replace = false } = {}) {
    if (replace) resetSeries();

    // Resolve x
    let xArr: number[] = [];
    if (Array.isArray(xSpec)) {
      xArr = xSpec as number[];
    } else if (typeof xSpec === "string" && payload && Array.isArray(payload[xSpec])) {
      xArr = payload[xSpec] as number[];
    }

    // Resolve y (arrays + labels)
    let yArrs: number[][] = [];
    let labels: string[] = [];

    if (isDirectSingleNumeric) {
      yArrs = [ySpecNorm as number[]];
      labels = ["series1"];
    } else if (isDirectMultiNumeric) {
      yArrs = ySpecNorm as number[][];
      labels = yArrs.map((_, i) => `series${i+1}`);
    } else {
      const keys = ySpecNorm as string[];
      for (const k of keys) {
        const arr = payload && Array.isArray(payload[k]) ? payload[k] : [];
        yArrs.push(arr as number[]);
      }
      labels = keys;
    }

    if (xArr.length && yArrs.length) {
      ingestArrays(xArr, yArrs, labels);
    }
  }

  // --- fetch / ws
  async function fetchOnce({ replace = false } = {}) {
    if (!url) return;
    loading = true;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const payload = await res.json();
      // For this generic component we expect an OBJECT like { xKey: number[], yKey1: number[], ... }
      const obj = Array.isArray(payload) ? payload[0] : payload;
      pushPayload(obj, { replace });
    } catch (e: any) {
      error = e?.message ?? "Failed to load data.";
    } finally {
      loading = false;
    }
  }

  // ---- geometry helpers
  function allPoints(): Point[] {
    return yKeysForLegend.flatMap(k => series[k] || []);
  }

  function extentX(): { min: number; max: number } {
    const pts = allPoints();
    if (!pts.length) return { min: 0, max: 0 };
    const xs = pts.map(p => p.t);
    return { min: Math.min(...xs), max: Math.max(...xs) };
  }

  function extentY(): { min: number; max: number } {
    const pts = allPoints();
    if (!pts.length) return { min: 0, max: 0 };
    const ys = pts.map(p => p.y);
    const min = Math.min(...ys);
    const max = Math.max(...ys);
    return (min === max) ? { min: min - 0.5, max: max + 0.5 } : { min, max };
  }

  // --- "nice" ticks
  function niceStep(span: number, target: number) {
    if (span <= 0 || !Number.isFinite(span)) return 1;
    const raw = span / Math.max(1, target);
    const pow10 = Math.pow(10, Math.floor(Math.log10(raw)));
    const cand = [1, 2, 5, 10].map(m => m * pow10);
    let best = cand[0], bestDiff = Infinity;
    for (const s of cand) {
      const diff = Math.abs(span / s - target);
      if (diff < bestDiff) { bestDiff = diff; best = s; }
    }
    return best;
  }
  function makeTicks(min: number, max: number, count = 4): number[] {
    if (min === max) return [min];
    const span = max - min;
    const step = niceStep(span, count);
    const start = Math.ceil(min / step) * step;
    const ticks: number[] = [];
    for (let v = start; v <= max + 1e-9; v += step) ticks.push(Number(v.toFixed(12)));
    return ticks;
  }

  // --- formatters
  const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 8 });
  const fmt = (n: number) => nf.format(n);
  function fmtTimeTick(v: number, span: number): string {
    const isTime = v > 1e9 || span > 1e6;
    if (!isTime) return fmt(v);
    const d = new Date(v);
    if (span >= 24 * 3600 * 1000) {
      return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(d);
    } else if (span >= 60 * 60 * 1000) {
      return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(d);
    } else {
      return new Intl.DateTimeFormat(undefined, { minute: "2-digit", second: "2-digit" }).format(d);
    }
  }

  // --- plot geometry helpers
  const VB_W = 100, VB_H = 30;
  const PLOT_PAD = { left: 1, right: 1, top: 2, bottom: 2 };
  const GUTTER_Y_WIDTH = 42;
  const GUTTER_X_HEIGHT = 22;
  const TICK_MARK_W = 8;
  const TICK_MARK_H = 8;

  function sxPlot(v: number, xExt: {min:number;max:number}) {
    const span = Math.max(1e-9, xExt.max - xExt.min);
    return PLOT_PAD.left + ((v - xExt.min) / span) * (VB_W - PLOT_PAD.left - PLOT_PAD.right);
  }
  function syPlot(v: number, yExt: {min:number;max:number}) {
    const span = Math.max(1e-9, yExt.max - yExt.min);
    return PLOT_PAD.top + (VB_H - PLOT_PAD.top - PLOT_PAD.bottom)
      - ((v - yExt.min) / span) * (VB_H - PLOT_PAD.top - PLOT_PAD.bottom);
  }
  function pointsString(arr: Point[], xExt: {min:number;max:number}, yExt: {min:number;max:number}) {
    if (!arr.length) return "";
    return arr.map(p => `${sxPlot(p.t, xExt)},${syPlot(p.y, yExt)}`).join(" ");
  }
  const xPct = (v: number, xExt: {min:number;max:number}) => (sxPlot(v, xExt) / VB_W) * 100;
  const yPct = (v: number, yExt: {min:number;max:number}) => (syPlot(v, yExt) / VB_H) * 100;

  // ---- lifecycle
  let unsub: null | (() => void) = null;
  onMount(() => {
    // Direct arrays -> ingest immediately
    if (Array.isArray(xSpec) || isDirectSingleNumeric || isDirectMultiNumeric) {
      try {
        const xArr = Array.isArray(xSpec) ? (xSpec as number[]) : [];
        let yArrs: number[][] = [];
        let labels: string[] = [];
        if (isDirectSingleNumeric) {
          yArrs = [ySpecNorm as number[]];
          labels = ["series1"];
        } else if (isDirectMultiNumeric) {
          yArrs = ySpecNorm as number[][];
          labels = yArrs.map((_, i) => `series${i+1}`);
        }
        if (xArr.length && yArrs.length) ingestArrays(xArr, yArrs, labels);
      } catch (e: any) {
        error = e?.message ?? "Invalid array data.";
      }
    } else if (wsUrl) {
      unsub = wsSubscribe(wsUrl, (payload) => {
        const obj = Array.isArray(payload) ? payload[0] : payload;
        pushPayload(obj);
      });
    } else if (url) {
      fetchOnce();
      if (refreshMs > 0) {
        const id = setInterval(() => fetchOnce(), refreshMs);
        onDestroy(() => clearInterval(id));
      }
    }
  });
  onDestroy(() => { if (unsub) unsub(); });
</script>


<div class="w-full flex justify-center">
  <div class="w-4/5 space-y-4">

    <!-- 1) CARD: column flexbox : set height from the prop -->
    <div class="rounded-xl2 shadow-card border table-border bg-[color:var(--card)] p-4 flex flex-col">
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>
        {#if url}
          <RefreshButton on:click={() => fetchOnce({ replace: true })} {loading} ariaLabel="Refresh chart" />
        {/if}

      </div>

      <!-- Legend -->
      <div class="flex flex-wrap items-center gap-4 mb-2 font-approachmono text-sm">
        {#each yKeysForLegend as key, i}
          <div class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 rounded" style="background:{seriesColors[i]}"></span>
            <span class="opacity-80">{seriesLabels[i]}:</span>
            <span class="font-medium">
              {#if (series[key] && series[key].length)} {fmt(series[key][series[key].length - 1].y)} {:else} — {/if}
            </span>
          </div>
        {/each}
      </div>

      <!-- 2) GRID -->
      <div class="flex-1">
        <div
          class="grid h-[inherit]"
          style={`height:${height}px; grid-template-columns: auto ${GUTTER_Y_WIDTH}px 1fr; grid-template-rows: 1fr ${GUTTER_X_HEIGHT}px; column-gap: 8px; row-gap: 4px;`}
        > 
          <!-- Y axis label -->
          <div class="flex items-center justify-center">
            <div class="text-[11px] text-text/60 font-approachmono"
                 style="transform: rotate(-90deg); transform-origin: center;">
              {yLabel || "Value"}
            </div>
          </div>

          <!-- Y ticks + labels  -->
          <div class="relative h-full min-h-0">
            {#if allPoints().length}
              {#await Promise.resolve(extentY()) then yExt}
                {#each makeTicks(yExt.min, yExt.max, 4) as ty}
                  <div
                    class="absolute right-0 flex items-center gap-1 pr-1 select-none"
                    style={`top:${yPct(ty, yExt)}%; transform:translateY(-50%);`}
                  >
                    <div class="text-[11px] font-approachmono text-white/85 leading-none">{fmt(ty)}</div>
                    <div class="h-px bg-white/85" style={`width:${TICK_MARK_W}px`}></div>
                  </div>
                {/each}
              {/await}
            {/if}
          </div>

          <!-- Plot (dotted background) -->
          <div class="chart-area rounded-lg overflow-hidden relative" style="height: 100%;">
            {#key allPoints().length}
              {#if allPoints().length}
                {#await Promise.resolve(extentX()) then xExt}
                  {#await Promise.resolve(extentY()) then yExt}
                    <svg 
                      viewBox="0 0 {VB_W} {VB_H}" 
                      class="absolute inset-0 w-full h-full"
                      preserveAspectRatio="none"
                    >
                      {#each yKeysForLegend as key, i}
                        {#if series[key] && series[key].length}
                          <polyline
                            fill="none"
                            stroke={seriesColors[i]}
                            stroke-width="0.2"
                            points={pointsString(series[key], xExt, yExt)}
                          />
                        {/if}
                      {/each}
                    </svg>
                  {/await}
                {/await}
              {:else}
                <div class="absolute inset-0 flex items-center justify-center">
                  <div class="text-sm text-text/60 font-approachmono">No data yet...</div>
                </div>
              {/if}
            {/key}
          </div>

          <!-- spacer under Y label -->
          <div></div>

          <!-- X gutter (under the plot) -->
          <div></div>
          <div class="relative">
            {#if allPoints().length}
              {#await Promise.resolve(extentX()) then xExt}
                {#each makeTicks(xExt.min, xExt.max, 5) as tx}
                  <div
                    class="absolute top-0 flex flex-col items-center select-none"
                    style={`left:${xPct(tx, xExt)}%; transform:translateX(-50%);`}
                  >
                    <div class="w-px bg-white/85" style={`height:${TICK_MARK_H}px`}></div>
                    <div class="text-[11px] font-approachmono text-white/85 leading-none mt-1">
                      {fmtTimeTick(tx, Math.max(1e-9, xExt.max - xExt.min))}
                    </div>
                  </div>
                {/each}
              {/await}
            {/if}
          </div>
        </div>
      </div>

      <!-- X axis label -->
      <div class="mt-2 text-center text-[11px] text-text/60 font-approachmono">
        {xLabel || x}
      </div>

      {#if $error}
        <div class="mt-2 text-xs text-red-500 font-approachmono">{error}</div>
      {/if}
    </div>
  </div>
</div>


<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
  .thin-border, .table-border { border-color: var(--edge); }

  .chart-area {
    background-color: var(--card);
    background-image:
      radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 0);
    background-size: 20px 20px;
  }
</style>
