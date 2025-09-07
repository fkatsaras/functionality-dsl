<script lang="ts">
  import { onMount, onDestroy } from "svelte";

  const {
    name = "LineChart",
    url,                  // optional: one-shot REST (and/or bootstrap for WS)
    wsUrl,                // optional: if present -> open WebSocket and STOP polling
    x,                    // REQUIRED: field name for x (e.g. "t")
    y,                    // REQUIRED: string | string[] for y fields (e.g. "c" or ["c","v"])
    xLabel,
    yLabel,
    windowSize: _windowSize = 0, // 0 = keep all history
    refreshMs = 0,               // default to no polling for REST unless explicitly set
    height = 320
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
  }>();

  const windowSize = Number(_windowSize ?? 0);
  const yKeys: string[] = Array.isArray(y) ? y : [y];

  type Point = { t: number; y: number };
  let points = $state<Record<string, Point[]>>({});
  for (const k of yKeys) points[k] = [];

  let loading = $state<boolean>(false);
  let error   = $state<string | null>(null);

  // formatting helpers
  const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 8 });
  const nfTerse = new Intl.NumberFormat(undefined, { maximumFractionDigits: 4 });
  const fmtNum = (n: number) => nf.format(n);
  const fmtRange = (min: number, max: number) => `${nfTerse.format(min)} - ${nfTerse.format(max)}`;

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
        const next = [...(points[key] || []), { t, y: v }];
        points[key] = windowSize > 0 ? next.slice(-windowSize) : next;
      }
    }
  }

  function pushPayload(payload: any) {
    const rows: any[] = Array.isArray(payload) ? payload : (payload ? [payload] : []);
    for (const r of rows) pushRow(r);
  }

  async function fetchOnce() {
    if (!url) return;
    loading = true;
    error = null;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const payload = await res.json();
      // REST: consume ALL rows on first fetch (static); not just the last element
      pushPayload(payload);
    } catch (e: any) {
      error = e?.message ?? "Failed to load data.";
    } finally {
      loading = false;
    }
  }

  function toWsUrl(u: string): string {
    if (!u) return "";
    if (u.startsWith("ws://") || u.startsWith("wss://")) return u;
    const base = (import.meta as any).env?.VITE_API_URL || window.location.origin;
    const full = new URL(u, base);
    full.protocol = full.protocol === "https:" ? "wss:" : "ws:";
    return full.toString();
  }

  let timer: any;
  let sock: WebSocket | null = null;

  function resolveWs(u: string): string {
    if (!u) return "";
    // absolute WS already
    if (u.startsWith("ws://") || u.startsWith("wss://")) return u;
    // path-only => let the browser use current origin (localhost:5173) and Vite will proxy+upgrade
    if (u.startsWith("/")) return u;
    // support devs who accidentally pass http(s)
    if (u.startsWith("http://"))  return "ws://"  + u.slice(7);
    if (u.startsWith("https://")) return "wss://" + u.slice(8);
    // otherwise leave as-is
    return u;
  }
  
  function openSocket() {
    if (!wsUrl) return;
    const full = resolveWs(wsUrl);
    try {
      sock = new WebSocket(full);
      sock.onmessage = (ev) => {
        try { pushPayload(typeof ev.data === "string" ? JSON.parse(ev.data) : ev.data); } catch {}
      };
      sock.onerror = () => { error = "WebSocket error"; };
    } catch (e: any) {
      error = e?.message ?? "WebSocket failed to open.";
    }
  }

  onMount(() => {
    // Bootstrap via REST only if there's no wsUrl
    if (!wsUrl && url) fetchOnce();

    if (wsUrl) {
      openSocket();
    } else if (url && refreshMs > 0) {
      timer = setInterval(fetchOnce, refreshMs);
    }

    return () => { if (timer) clearInterval(timer); if (sock) try { sock.close(); } catch {} };
  });

  function viewBoxFor(arr: Point[]) {
    if (!arr.length) return { pts: "", min: 0, max: 0 };
    const ys = arr.map((p) => p.y);
    const min = Math.min(...ys);
    const max = Math.max(...ys);
    const span = Math.max(1e-9, max - min);
    const pts = arr.map((p, i) => {
      const x = (i / Math.max(1, arr.length - 1)) * 100;
      const y = 30 - ((p.y - min) / span) * 28;
      return `${x},${y}`;
    });
    return { pts: pts.join(" "), min, max };
  }

  function extentX(arr: Point[]) {
    if (!arr.length) return { min: 0, max: 0 };
    const xs = arr.map((p) => p.t);
    return { min: Math.min(...xs), max: Math.max(...xs) };
  }
</script>

<div class="w-full flex justify-center">
  <div class="w-4/5 space-y-6">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      {#each Object.entries(points) as [key, arr]}
        <div class="rounded-xl2 shadow-card border table-border bg-[color:var(--card)] p-4">
          <!-- Header inside card, centered -->
          <div class="mb-4 text-center">
            <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>
          </div>

          {#if arr.length}
            {#key arr.length}
              <div class="flex items-baseline gap-2 mb-3">
                <div class="text-2xl font-approachmono text-text/90">
                  {fmtNum(arr[arr.length - 1].y)}
                </div>
                {#if windowSize !== 0}
                  <div class="text-xs text-text/60 font-approachmono">
                    ({fmtRange(viewBoxFor(arr).min, viewBoxFor(arr).max)})
                  </div>
                {/if}
              </div>

              <!-- Plot row: Y label + CHART AREA WITH DOTS ONLY -->
              <div class="grid" style="grid-template-columns: auto 1fr; column-gap: 8px;">
                <div class="flex items-center justify-center">
                  <div
                    class="text-[11px] text-text/60 font-approachmono"
                    style="transform: rotate(-90deg); transform-origin: center;"
                  >
                    {yLabel || key.toUpperCase()}
                  </div>
                </div>
                <div class="chart-area rounded-lg overflow-hidden">
                  <svg viewBox="0 0 100 30" width="100%" height={height} preserveAspectRatio="none">
                    <polyline fill="none" stroke="currentColor" stroke-width="0.8" points={viewBoxFor(arr).pts} />
                  </svg>
                </div>
              </div>

              <div class="mt-3 relative text-[11px] text-text/60 font-approachmono">
                <div class="text-center">{xLabel || x}</div>
                <div class="absolute right-0 top-0">
                  {fmtNum(arr[arr.length - 1].t)}
                  {#if windowSize !== 0}
                    <span class="opacity-70">({fmtRange(extentX(arr).min, extentX(arr).max)})</span>
                  {/if}
                </div>
              </div>
            {/key}
          {:else}
            <div class="text-sm text-text/60 font-approachmono">No data yet...</div>
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

  /* dotted grid ONLY in plot area */
  .chart-area {
    background-color: var(--card);
    background-image:
      radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 0);
    background-size: 20px 20px;
  }
</style>
