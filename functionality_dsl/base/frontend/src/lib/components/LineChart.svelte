<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribe as wsSubscribe } from "../ws";
  import RefreshButton from "./util/RefreshButton.svelte";

  const {
    name = "LineChart",
    url,
    wsUrl,
    refreshMs = 0,
    windowSize: _windowSize = 0,
    height = 240,
    xLabel,
    yLabel,
    seriesLabels: _seriesLabels = null as null | string[],
    seriesColors: _seriesColors = null as null | string[],
  } = $props<{
    name?: string;
    url?: string;
    wsUrl?: string;
    refreshMs?: number;
    windowSize?: number;
    height?: number;
    xLabel?: string;
    yLabel?: string;
    seriesLabels?: string[] | null;
    seriesColors?: string[] | null;
  }>();

  let loading: boolean = $state(Boolean(url));
  let xKey: string | null = $state(null);
  let yKeys: string[] = $state([]);

  type Point = { t: number; y: number };
  let series: Record<string, Point[]> = $state({});

  let error: string | null = $state(null);
  const windowSize = $derived(Number(_windowSize ?? 0));
  
  // legend labels/colors
  const defaultPalette = ["#3b82f6", "#22c55e", "#f97316", "#e11d48", "#a855f7", "#14b8a6"];
  const seriesLabels = $derived(
    _seriesLabels && _seriesLabels.length === yKeys.length
      ? _seriesLabels
      : yKeys.map(k => k.toUpperCase())
  );

  const seriesColors = $derived(
    _seriesColors && _seriesColors.length === yKeys.length
      ? _seriesColors
      : yKeys.map((_, i) => defaultPalette[i % defaultPalette.length])
);


  function resetSeries() {
    series = Object.fromEntries(yKeys.map(k => [k, []]));
  }

  function normT(v: any): number | null {
    if (v == null) return null;
    const n = Number(v);
    if (Number.isFinite(n)) return n;
    const ts = Date.parse(String(v));
    return Number.isNaN(ts) ? null : ts;
  }

  function pushRow(row: any) {
    if (!xKey) return;
    const t = normT(row?.[xKey]);
    if (t == null) return;
    for (const key of yKeys) {
      const v = Number(row?.[key]);
      if (Number.isFinite(v)) {
        const next = [...(series[key] || []), { t, y: v }];
        series = { ...series, [key]: windowSize > 0 ? next.slice(-windowSize) : next };
      }
    }
  }

  function pushPayload(payload: any) {
    // 0) Envelope normalize to an array of entity dicts
    const entities: any[] =
      Array.isArray(payload) ? payload :
      (payload && typeof payload === "object" ? [payload] : []);
    if (!entities.length) return;

    // 1) CASE A: list-of-dicts (REST-style) nested under the first attr
    let rows: any[] = [];
    outer: for (const ent of entities) {
      if (ent && typeof ent === "object") {
        for (const v of Object.values(ent)) {
          if (Array.isArray(v) && v.length && typeof v[0] === "object") {
            rows = v;
            break outer;
          }
        }
      }
    }
    if (rows.length) {
      if (!xKey || !yKeys.length) {
        const first = rows[0];
        if (first && typeof first === "object") {
          const keys = Object.keys(first);
          xKey = keys[0] ?? null;
          yKeys = keys.slice(1);
          series = Object.fromEntries(yKeys.map(k => [k, []]));
        }
      }
      for (const r of rows) pushRow(r);
      return;
    }

    // 2) CASE B: single-row dict (WS tick) like {tick:{t:..., btc:...}} or {t:..., btc:...}
    let single: any = null;

    // 2a) payload itself is the row
    if (!Array.isArray(payload) && payload && typeof payload === "object") {
      const vals = Object.values(payload);
      // if it looks like { tick: {...} }, take that inner dict
      if (vals.length === 1 && vals[0] && typeof vals[0] === "object" && !Array.isArray(vals[0])) {
        single = vals[0];
      } else {
        // or just use payload if it smells like a row already
        single = payload;
      }
    }

    if (single && typeof single === "object" && !Array.isArray(single)) {
      if (!xKey || !yKeys.length) {
        const keys = Object.keys(single);
        xKey = keys[0] ?? xKey;
        yKeys = keys.slice(1);
        series = Object.fromEntries(yKeys.map(k => [k, []]));
      }
      pushRow(single);
    }
  }


  async function fetchOnce({ replace = false } = {}) {
    if (!url) return;
    loading = true;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const payload = await res.json();
      console.log("raw payload from", url, payload);

      if (replace) resetSeries();
      pushPayload(payload);
    } catch (e: any) {
      error = e?.message ?? "Failed to load data.";
    } finally {
      loading = false;
    }
  }


  // ---- geometry helpers (shared x/y scales across all series)
  function allPoints(): Point[] {
    return yKeys.flatMap(k => series[k] || []);
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

  // --- "nice" ticks for linear scales
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

  // --- plot + gutters
  const VB_W = 100, VB_H = 30;     // viewBox for the plot SVG
  const PLOT_PAD = { left: 1, right: 1, top: 2, bottom: 2 }; // tiny breathing room inside dotted bg

  // Gutters (HTML) — OUTSIDE the dotted area
  const GUTTER_Y_WIDTH = 42;  // px space for Y tick labels + marks
  const GUTTER_X_HEIGHT = 22; // px space for X tick labels + marks

  // Ticks = SAME size as axis labels (use Tailwind text-[11px]); marks sized to match
  const TICK_MARK_W = 8;  // px (Y marks, horizontal)
  const TICK_MARK_H = 8;  // px (X marks, vertical)

  // Scale helpers for plot SVG (data -> viewBox units)
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

  // Fractions for HTML positioning (0..1 within the plot’s SVG viewBox)
  const xPct = (v: number, xExt: {min:number;max:number}) => (sxPlot(v, xExt) / VB_W) * 100;
  const yPct = (v: number, yExt: {min:number;max:number}) => (syPlot(v, yExt) / VB_H) * 100;

  // ---- lifecycle
  let unsub: null | (() => void) = null;
  onMount(() => {
    if (wsUrl && wsUrl !== "None") {
      unsub = wsSubscribe(wsUrl, pushPayload);
    } else if (url) {
      fetchOnce();
      if (refreshMs > 0) {
        const id = setInterval(fetchOnce, refreshMs);
        onDestroy(() => clearInterval(id));
      }
    }
  });
  onDestroy(() => { if (unsub) unsub(); });
</script>


<div class="flex justify-center items-center w-full">
  <div
    class="rounded-2xl border bg-[color:var(--card)] p-6 flex flex-col transition-colors"
    style="width: 1600px; height: 500px;"
    class:border-dag-success={loading}
    class:border-dag-danger={!loading}
  >
    <!-- Header -->
    <div class="pb-3 w-full flex items-center justify-between gap-3">
      <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>

      <!-- LIVE indicator (same style as InputBox) -->
      <div
        class="flex items-center gap-2 px-2 py-1 rounded-md border"
        class:border-dag-success={loading}
        class:border-dag-danger={!loading}
      >
        <svg
          class="w-4 h-4"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          aria-hidden="true"
          class:text-dag-success={loading}
          class:text-dag-danger={!loading}
        >
          <circle cx="10" cy="10" r="8.5" />
        </svg>
        <span
          class="text-xs font-approachmono"
          class:text-dag-success={loading}
          class:text-dag-danger={!loading}
        >
          {loading ? "LIVE" : "OFF"}
        </span>
      </div>
    </div>

    <!-- Legend -->
    <div class="flex flex-wrap items-center gap-4 mb-4 font-approachmono text-sm">
      {#each yKeys as key, i}
        <div class="flex items-center gap-2">
          <span class="inline-block w-3 h-3 rounded" style="background:{seriesColors[i]}"></span>
          <span class="opacity-80">{seriesLabels[i]}:</span>
          <span class="font-medium">
            {#if (series[key] && series[key].length)} {fmt(series[key][series[key].length - 1].y)} {:else} — {/if}
          </span>
        </div>
      {/each}
    </div>

    <!-- Chart area -->
    <div
      class="relative"
      style="flex:1; height:380px; display:grid;
             grid-template-columns: 80px 1fr;   /* wider left gutter for Y labels */
             grid-template-rows: 1fr 60px;      /* taller bottom gutter for X labels */
             column-gap: 16px; row-gap: 12px;"
    >
      <!-- Y axis + ticks -->
      <div class="relative">
        <div class="absolute left-0 top-1/2 -translate-y-1/2 rotate-[-90deg] text-[13px] text-text/70 font-approachmono font-bold">
          {yLabel || "Value"}
        </div>

        {#if allPoints().length}
          {#await Promise.resolve(extentY()) then yExt}
            {#each makeTicks(yExt.min, yExt.max, 5) as ty}
              <div
                class="absolute right-0 pr-2 flex items-center gap-2 select-none"
                style={`top:${yPct(ty, yExt)}%; transform:translateY(-50%);`}
              >
                <div class="text-[13px] font-approachmono font-bold text-white leading-none">{fmt(ty)}</div>
                <div class="h-px bg-white/85" style="width:10px;"></div>
              </div>
            {/each}
          {/await}
        {/if}
      </div>

      <!-- Plot -->
      <div class="chart-area rounded-lg overflow-hidden relative border-4 border-white" style="height:100%;">
        {#if allPoints().length}
          {#await Promise.resolve(extentX()) then xExt}
            {#await Promise.resolve(extentY()) then yExt}
              <svg viewBox="0 0 {VB_W} {VB_H}" class="absolute inset-0 w-full h-full" preserveAspectRatio="none">
                {#each yKeys as key, i}
                  {#if series[key] && series[key].length}
                    <polyline
                      fill="none"
                      stroke={seriesColors[i]}
                      stroke-width="0.35"
                      points={pointsString(series[key], xExt, yExt)}
                    />
                  {/if}
                {/each}
              </svg>
            {/await}
          {/await}
        {:else}
          <div class="absolute inset-0 flex items-center justify-center text-text/60 font-approachmono text-sm">
            No data yet...
          </div>
        {/if}
      </div>

      <!-- Spacer -->
      <div></div>

      <!-- X ticks + label -->
      <div class="relative">
        {#if allPoints().length}
          {#await Promise.resolve(extentX()) then xExt}
            {#each makeTicks(xExt.min, xExt.max, 7) as tx}
              <div
                class="absolute top-0 flex flex-col items-center select-none"
                style={`left:${xPct(tx, xExt)}%; transform:translateX(-50%);`}
              >
                <div class="w-px bg-white/85" style="height:10px;"></div>
                <div class="text-[13px] font-approachmono font-bold text-white leading-none mt-2">
                  {fmtTimeTick(tx, Math.max(1e-9, xExt.max - xExt.min))}
                </div>
              </div>
            {/each}
          {/await}
        {/if}

        <div class="absolute bottom-0 left-1/2 -translate-x-1/2 mt-6 text-[13px] text-text/70 font-approachmono font-bold">{xLabel}</div>
      </div>
    </div>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
  .chart-area {
    background-color: var(--card);
    background-image:
      radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 0);
    background-size: 20px 20px;
  }
</style>

