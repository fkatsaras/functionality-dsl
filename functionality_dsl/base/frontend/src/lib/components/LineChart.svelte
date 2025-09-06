<script lang="ts">
  import { onMount } from "svelte";

  const {
    name = "LineChart",
    url,                         // e.g. /api/external/coincapprices/latest
    series = [] as string[],     // e.g. ["bitcoin","ethereum"]
    windowSize = 100,
    refreshMs = 1000,
    height = 220
  } = $props<{
    name?: string;
    url: string;
    series?: string[];
    windowSize?: number;
    refreshMs?: number;
    height?: number;
  }>();

  type Point = { t: number; y: number };
  let points: Record<string, Point[]> = {};
  for (const s of series) points[s] = [];

  let loading = $state<boolean>(false);
  let error   = $state<string | null>(null);

  async function fetchOnce() {
    if (!url) return;
    loading = true;
    error = null;

    try {
      const res = await fetch(import.meta.env.VITE_API_URL + url);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const snapshot = await res.json();   // {key: value, ...}
      const t = Date.now();
      for (const s of series) {
        const v = Number(snapshot?.[s]);
        if (Number.isFinite(v)) {
          points[s] = [...points[s], { t, y: v }].slice(-windowSize);
        }
      }
    } catch (e: any) {
      error = e?.message ?? "Failed to load data.";
    } finally {
      loading = false;
    }
  }

  let timer: any;
  onMount(async () => {
    await fetchOnce();
    timer = setInterval(fetchOnce, refreshMs);
    return () => clearInterval(timer);
  });

  function viewBoxFor(arr: Point[]) {
    if (!arr.length) return "0 0 100 30";
    const ys = arr.map((p) => p.y);
    const min = Math.min(...ys);
    const max = Math.max(...ys);
    const span = Math.max(1e-9, max - min);
    // Normalize to width=100, height=30
    const pts = arr.map((p, i) => {
      const x = (i / Math.max(1, windowSize - 1)) * 100;
      const y = 30 - ((p.y - min) / span) * 28;
      return `${x},${y}`;
    });
    return { pts: pts.join(" "), min, max };
  }
</script>

<div class="w-full flex justify-center">
  <div class="w-4/5 space-y-3">
    <div class="mb-1 flex items-center justify-center gap-3">
      <h2 class="text-base font-approachmono text-text/90 tracking-tight">{name}</h2>
      <button
        class="px-3 py-1 text-xs rounded-lg border thin-border bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition disabled:opacity-60"
        on:click={fetchOnce}
        disabled={loading}
      >
        {loading ? "Loading..." : "Refresh"}
      </button>
      {#if error}<span class="text-xs text-dag-danger">{error}</span>{/if}
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      {#each Object.entries(points) as [name, arr]}
        <div class="rounded-xl2 shadow-card border table-border bg-[color:var(--card)] p-3">
          <div class="text-xs text-text/70 font-approachmono mb-1">{name.toUpperCase()}</div>
          {#if arr.length}
            {#key arr.length}
              {#let computed = viewBoxFor(arr) }
              <div class="flex items-baseline gap-2 mb-1">
                <div class="text-2xl font-approachmono text-text/90">
                  {arr[arr.length - 1].y}
                </div>
                <div class="text-xs text-text/60 font-approachmono">
                  ({computed.min} – {computed.max})
                </div>
              </div>
              <svg viewBox="0 0 100 30" width="100%" height={height} preserveAspectRatio="none">
                <polyline fill="none" stroke="currentColor" stroke-width="0.8" points={computed.pts} />
              </svg>
            {/key}
          {:else}
            <div class="text-sm text-text/60 font-approachmono">No data yet…</div>
          {/if}
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
  .thin-border, .table-border { border-color: var(--edge); }
</style>
