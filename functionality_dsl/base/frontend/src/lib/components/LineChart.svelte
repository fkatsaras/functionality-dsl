<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribe as wsSubscribe } from "../ws";

  const {
    name = "LineChart",
    url,                  // optional HTTP bootstrap (only used if NO wsUrl)
    wsUrl,                // preferred; when present we never poll
    x,                    // e.g. "t"
    y,                    // string | string[]
    xLabel,
    yLabel,
    windowSize: _windowSize = 0, // 0 = keep all
    refreshMs = 0,               // ignored when wsUrl is present
    height = 500,
    // Optional: legend labels & colors (parallel to y order)
    seriesLabels: _seriesLabels = null as null | string[],
    seriesColors: _seriesColors = null as null | string[],
  } = $props<{
    name?: string;
    url?: string;
    wsUrl?: string;
    x: string;
    y: string | string[];
    xLabel?: string;
    yLabel?: string;
    windowSize?: number | null;
    refreshMs?: number;
    height?: number;
    seriesLabels?: string[] | null;
    seriesColors?: string[] | null;
  }>();

  const yKeys: string[] = Array.isArray(y) ? y : [y];
  const windowSize = Number(_windowSize ?? 0);

  // legend labels/colors
  const defaultPalette = ["#3b82f6", "#22c55e", "#f97316", "#e11d48", "#a855f7", "#14b8a6"];
  const seriesLabels = _seriesLabels && _seriesLabels.length === yKeys.length
    ? _seriesLabels
    : yKeys.map(k => k.toUpperCase());
  const seriesColors = _seriesColors && _seriesColors.length === yKeys.length
    ? _seriesColors
    : yKeys.map((_, i) => defaultPalette[i % defaultPalette.length]);

  type Point = { t: number; y: number };
  let series: Record<string, Point[]> = $state({});
  for (const k of yKeys) series[k] = [];

  let error: string | null = null;

  function normT(v: any): number | null {
    if (v == null) return null;
    const n = Number(v);
    if (Number.isFinite(n)) return n;
    const ts = Date.parse(String(v));
    return Number.isNaN(ts) ? null : ts;
  }

  function pushRow(row: any) {
    const t = normT(row?.[x]);
    if (t == null) return;
    for (const key of yKeys) {
      const v = Number(row?.[key]);
      if (Number.isFinite(v)) {
        const next = [...(series[key] || []), { t, y: v }];
        series[key] = windowSize > 0 ? next.slice(-windowSize) : next;
      }
    }
  }

  function pushPayload(payload: any) {
    const rows: any[] = Array.isArray(payload) ? payload : (payload ? [payload] : []);
    for (const r of rows) pushRow(r);
  }

  async function fetchOnce() {
    if (!url) return;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      pushPayload(await res.json());
    } catch (e: any) {
      error = e?.message ?? "Failed to load data.";
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
    // keep a minimum span to avoid divide-by-zero
    return (min === max) ? { min: min - 0.5, max: max + 0.5 } : { min, max };
  }

  function pointsString(arr: Point[], xExt: {min:number;max:number}, yExt: {min:number;max:number}) {
    if (!arr.length) return "";
    const xSpan = Math.max(1e-9, xExt.max - xExt.min);
    const ySpan = Math.max(1e-9, yExt.max - yExt.min);
    return arr.map(p => {
      const px = ((p.t - xExt.min) / xSpan) * 100;       // 0..100
      const py = 30 - ((p.y - yExt.min) / ySpan) * 28;   // 1px top/btm margins
      return `${px},${py}`;
    }).join(" ");
  }

  // ---- lifecycle
  let unsub: null | (() => void) = null;

  onMount(() => {
    if (wsUrl) {
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

  // formatting for legend
  const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 8 });
  const fmt = (n: number) => nf.format(n);
</script>

<div class="w-full flex justify-center">
  <div class="w-4/5 space-y-4">
    <div class="rounded-xl2 shadow-card border table-border bg-[color:var(--card)] p-4">
      <div class="mb-3 text-center">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>
      </div>

      <!-- Legend with latest values -->
      <div class="flex flex-wrap items-center gap-4 mb-2 font-approachmono text-sm">
        {#each yKeys as key, i}
          <div class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 rounded" style="background:{seriesColors[i]}"></span>
            <span class="opacity-80">{seriesLabels[i]}:</span>
            <span class="font-medium">
              {#if (series[key] && series[key].length)}
                {fmt(series[key][series[key].length - 1].y)}
              {:else}
                —
              {/if}
            </span>
          </div>
        {/each}
      </div>

      <!-- Y label + chart -->
      <div class="grid" style="grid-template-columns: auto 1fr; column-gap: 8px;">
        <div class="flex items-center justify-center">
          <div class="text-[11px] text-text/60 font-approachmono"
               style="transform: rotate(-90deg); transform-origin: center;">
            {yLabel || "Value"}
          </div>
        </div>

        <div class="chart-area rounded-lg overflow-hidden">
          {#key allPoints().length}
            {#if allPoints().length}
              {#await Promise.resolve(extentX()) then xExt}
                {#await Promise.resolve(extentY()) then yExt}
                  <svg viewBox="0 0 100 30" width="100%" height="100%" preserveAspectRatio="none">
                    {#each yKeys as key, i}
                      {#if series[key] && series[key].length}
                        <polyline
                          fill="none"
                          stroke={seriesColors[i]}
                          stroke-width="0.8"
                          points={pointsString(series[key], xExt, yExt)}
                        />
                      {/if}
                    {/each}
                  </svg>
                {/await}
              {/await}
            {:else}
              <div class="p-3 text-sm text-text/60 font-approachmono">No data yet...</div>
            {/if}
          {/key}
        </div>
      </div>

      <!-- X label -->
      <div class="mt-3 text-center text-[11px] text-text/60 font-approachmono">
        {xLabel || x}
      </div>

      {#if error}
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
