<!-- src/lib/components/Plot.svelte -->
<script lang="ts">
  // Props: arrays of integers (numbers), zipped pairwise → (x[i], y[i])
  const {
    name = "Plot",
    x = [] as number[],
    y = [] as number[],
    xLabel = "X",
    yLabel = "Y",
    height = 500,
    pointRadius = 1.0,
  } = $props<{
    name?: string;
    x: number[];
    y: number[];
    xLabel?: string;
    yLabel?: string;
    height?: number;
    pointRadius?: number;
  }>();

  // zip to points
  type Pt = { x: number; y: number };
  const n = Math.min(x.length, y.length);
  const points: Pt[] = Array.from({ length: n }, (_, i) => ({ x: Number(x[i]), y: Number(y[i]) }))
    .filter(p => Number.isFinite(p.x) && Number.isFinite(p.y));

  // extents
  function extentX() {
    if (!points.length) return { min: 0, max: 1 };
    const xs = points.map(p => p.x);
    const min = Math.min(...xs), max = Math.max(...xs);
    return (min === max) ? { min: min - 0.5, max: max + 0.5 } : { min, max };
  }
  function extentY() {
    if (!points.length) return { min: 0, max: 1 };
    const ys = points.map(p => p.y);
    const min = Math.min(...ys), max = Math.max(...ys);
    return (min === max) ? { min: min - 0.5, max: max + 0.5 } : { min, max };
  }

  // axes + ticks (minimal)
  function niceStep(span: number, target = 4) {
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
  function makeTicks(min: number, max: number, count = 4) {
    if (min === max) return [min];
    const span = max - min;
    const step = niceStep(span, count);
    const start = Math.ceil(min / step) * step;
    const out: number[] = [];
    for (let v = start; v <= max + 1e-9; v += step) out.push(Number(v.toFixed(12)));
    return out;
  }
  const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 8 });
  const fmt = (n: number) => nf.format(n);

  // plot geometry (same spirit as LineChart)
  const VB_W = 100, VB_H = 30;
  const PLOT_PAD = { left: 1, right: 1, top: 2, bottom: 2 };
  const GUTTER_Y_WIDTH = 42;  // px
  const GUTTER_X_HEIGHT = 22; // px
  const TICK_MARK_W = 8;      // px (Y)
  const TICK_MARK_H = 8;      // px (X)

  function sxPlot(v: number, xExt: {min:number;max:number}) {
    const span = Math.max(1e-9, xExt.max - xExt.min);
    return PLOT_PAD.left + ((v - xExt.min) / span) * (VB_W - PLOT_PAD.left - PLOT_PAD.right);
  }
  function syPlot(v: number, yExt: {min:number;max:number}) {
    const span = Math.max(1e-9, yExt.max - yExt.min);
    return PLOT_PAD.top + (VB_H - PLOT_PAD.top - PLOT_PAD.bottom)
      - ((v - yExt.min) / span) * (VB_H - PLOT_PAD.top - PLOT_PAD.bottom);
  }
  const xPct = (v: number, xExt: {min:number;max:number}) => (sxPlot(v, xExt) / VB_W) * 100;
  const yPct = (v: number, yExt: {min:number;max:number}) => (syPlot(v, yExt) / VB_H) * 100;
</script>

<div class="w-full flex justify-center">
  <div class="w-4/5 space-y-4">
    <div class="rounded-xl2 shadow-card border table-border bg-[color:var(--card)] p-4 flex flex-col">
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>
      </div>

      <!-- grid with gutters like LineChart -->
      <div class="flex-1">
        <div
          class="grid h-[inherit]"
          style={`height:${height}px; grid-template-columns: auto ${GUTTER_Y_WIDTH}px 1fr; grid-template-rows: 1fr ${GUTTER_X_HEIGHT}px; column-gap: 8px; row-gap: 4px;`}
        >
          <!-- Y axis label -->
          <div class="flex items-center justify-center">
            <div class="text-[11px] text-text/60 font-approachmono"
                 style="transform: rotate(-90deg); transform-origin: center;">
              {yLabel}
            </div>
          </div>

          <!-- Y ticks -->
          <div class="relative h-full min-h-0">
            {#if points.length}
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

          <!-- Plot area -->
          <div class="chart-area rounded-lg overflow-hidden relative" style="height:100%;">
            {#if points.length}
              {#await Promise.resolve(extentX()) then xExt}
                {#await Promise.resolve(extentY()) then yExt}
                  <svg
                    viewBox="0 0 {VB_W} {VB_H}"
                    class="absolute inset-0 w-full h-full"
                    preserveAspectRatio="none"
                  >
                    {#each points as p}
                      <circle
                        cx={sxPlot(p.x, xExt)}
                        cy={syPlot(p.y, yExt)}
                        r={pointRadius}
                        fill="#3b82f6"
                      />
                    {/each}
                  </svg>
                {/await}
              {/await}
            {:else}
              <div class="absolute inset-0 flex items-center justify-center">
                <div class="text-sm text-text/60 font-approachmono">No data yet...</div>
              </div>
            {/if}
          </div>

          <!-- spacer under Y label -->
          <div></div>

          <!-- X gutter -->
          <div></div>
          <div class="relative">
            {#if points.length}
              {#await Promise.resolve(extentX()) then xExt}
                {#each makeTicks(xExt.min, xExt.max, 5) as tx}
                  <div
                    class="absolute top-0 flex flex-col items-center select-none"
                    style={`left:${xPct(tx, xExt)}%; transform:translateX(-50%);`}
                  >
                    <div class="w-px bg-white/85" style={`height:${TICK_MARK_H}px`}></div>
                    <div class="text-[11px] font-approachmono text-white/85 leading-none mt-1">{fmt(tx)}</div>
                  </div>
                {/each}
              {/await}
            {/if}
          </div>
        </div>
      </div>

      <!-- X axis label -->
      <div class="mt-2 text-center text-[11px] text-text/60 font-approachmono">
        {xLabel}
      </div>
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
