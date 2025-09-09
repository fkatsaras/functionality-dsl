<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribe } from "$lib/ws";

  const {
    wsPath = null,
    valueKey = "value",
    min = 0,              // may be string at runtime → coerce below
    max = 100,            // may be string at runtime → coerce below
    label = "",
    unit = "",
    name = "Gauge",
    initial = null,
  } = $props<{
    wsPath?: string | null;
    valueKey?: string;
    min?: number | string;
    max?: number | string;
    label?: string;
    unit?: string;
    name?: string;
    initial?: number | string | null;
  }>();

  // ---- numeric coercions (handle SSR + string props) ----
  const minN = $derived(Number(min) || 0);
  const maxN = $derived(Number(max) || 100);

  let value = $state<number>(Number(initial ?? minN));
  let connected = $state(false);
  let error = $state<string | null>(null);

  function getByPath(obj: any, path: string) {
    try { return path.split(".").reduce((acc: any, k: string) => (acc == null ? undefined : acc[k]), obj); }
    catch { return undefined; }
  }

  let unsubscribe: (() => void) | null = null;

  onMount(() => {
    if (!wsPath) { error = "No wsPath provided"; return; }
    unsubscribe = subscribe(wsPath, (msg: any) => {
      if (msg && msg.__meta === "open")  { connected = true;  return; }
      if (msg && msg.__meta === "close") { connected = false; return; }
        
      connected = true; // any data implies live
        
      try {
        const raw = getByPath(msg, valueKey);
        const minLocal = Number(min) || 0;
        const maxLocal = Number(max) || 100;
        const num = Number(raw);
        if (Number.isFinite(num)) {
          value = Math.min(maxLocal, Math.max(minLocal, num));
        }
      } catch (e: any) {
        error = e?.message ?? "Parse error";
      }
    });
  });

  onDestroy(() => { try { unsubscribe?.(); } catch {} unsubscribe = null; connected = false; });

  // runes reactivity
  const R = 60;
  const CIRC = 2 * Math.PI * R;
  const span = $derived((maxN - minN) || 1);
  const pct  = $derived(Math.max(0, Math.min(1, (value - minN) / span)));
  const dash = $derived(`${CIRC * pct} ${CIRC}`);

  function fmt(v: any) {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(2) : String(v ?? "");
  }
</script>
<div class="gauge-wrap">
  <div class="header">
    <h2 class="title">{name}</h2>
    <span class="badge" data-ok={connected}>{connected ? "LIVE" : "OFF"}</span>
    {#if error}<span class="err">{error}</span>{/if}
  </div>

  <div class="gauge-card">
    <svg width="180" height="120" viewBox="0 0 200 120" aria-label="gauge">
      <path d="M20,110 A90,90 0 0,1 180,110" fill="none" stroke="#eee" stroke-width="16" />
      <path
        d="M20,110 A90,90 0 0,1 180,110"
        fill="none"
        stroke-width="16"
        stroke-linecap="round"
        stroke="currentColor"
        style="stroke-dasharray: {dash};"
      />
      <g transform="translate(100,110)">
        <line x1="0" y1="0" x2="0" y2="-70" stroke="currentColor" stroke-width="3" transform="rotate({180 * pct})" />
        <circle cx="0" cy="0" r="4" fill="currentColor" />
      </g>
    </svg>

    <div class="value">{fmt(value)}{unit ? ` ${unit}` : ''}</div>
    {#if label}<div class="label">{label}</div>{/if}
    <div class="range">min {min} · max {max}</div>
  </div>
</div>

<style>
  .gauge-wrap { width: 100%; display: flex; justify-content: center; }
  .header { width: 80%; display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .title { font-size: 0.95rem; font-weight: 600; color: var(--text, #222); margin: 0; }
  .badge { font-size: 0.7rem; padding: 2px 6px; border-radius: 8px; background: #eee; color: #333; }
  .badge[data-ok="true"] { background: #d1fae5; color: #065f46; }
  .err { font-size: 0.75rem; color: var(--danger, #c00); margin-left: 8px; }
  .gauge-card { width: 80%; display:flex; flex-direction:column; align-items:center; gap:8px;
                padding:16px; border:1px solid var(--edge, #eee); border-radius:16px;
                background: var(--card, #fff); box-shadow: 0 1px 8px rgba(0,0,0,0.04); }
  .value { font-size: 1.75rem; font-weight: 700; color: var(--text, #222); }
  .label { color:#666; font-size: 0.9rem; }
  .range { color:#888; font-size: 0.75rem; }
</style>
