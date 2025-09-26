<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribe } from "$lib/ws";

  const {
    wsPath = null,
    valueKey = "value",
    min = 0,              // may be string at runtime
    max = 100,
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
      console.log("Gauge message:", msg); 
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

<div class="w-full flex justify-center p-4">
  <div class="w-full max-w-sm">

    <!-- Card-->
    <div
      class="rounded-2xl shadow-lg border bg-[color:var(--card)] p-6 flex flex-col items-center gap-4 transition-shadow duration-200 hover:shadow-xl"
      class:border-dag-success={connected}
      class:border-dag-danger={!connected}
    >
      <!-- Header -->
      <div class="mb-6 w-full flex items-center justify-between">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>
      
        <!-- NEW: actionform-style live indicator -->
        <div
          class="flex items-center gap-2 px-2 py-1 rounded-md border"
          class:border-dag-success={connected}
          class:border-dag-danger={!connected}
        >
          <!-- outlined circle like ActionForm tick color -->
          <svg
            class="w-4 h-4"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            aria-hidden="true"
            class:text-dag-success={connected}
            class:text-dag-danger={!connected}
          >
            <circle cx="10" cy="10" r="8.5" />
          </svg>
        
          <!-- LIVE/OFF label in Approach Mono, green/red letters only -->
          <span
            class="text-xs font-approachmono"
            class:text-dag-success={connected}
            class:text-dag-danger={!connected}
          >
            {connected ? "LIVE" : "OFF"}
          </span>
        </div>
      
        {#if error}
          <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">{error}</span>
        {/if}
      </div>
      
      <!-- gauge -->
      <div class="relative flex items-end gap-4">
        <!-- Min indicator -->
        <div class="flex flex-col items-end gap-1">
          <div class="w-2 h-2 rounded-full bg-text/30"></div>
          <div class="text-xs font-approachmono text-text/50">{min}</div>
        </div>
        
        <svg width="200" height="130" viewBox="0 0 220 130" aria-label="gauge" class="drop-shadow-sm">
          <!-- Background arc -->
          <path 
            d="M30,120 A90,90 0 0,1 190,120" 
            fill="none" 
            stroke="var(--edge)" 
            stroke-width="12" 
            opacity="0.3"
          />
          <!-- Progress arc -->
          <path
            d="M30,120 A90,90 0 0,1 190,120"
            fill="none"
            stroke-width="12"
            stroke-linecap="round"
            stroke="currentColor"
            style="stroke-dasharray: {dash}; transition: stroke-dasharray 0.3s ease-out;"
            class="text-text"
          />
          <!-- Needle -->
          <g transform="translate(110,120)">
            <line 
              x1="0" y1="0" x2="0" y2="-75" 
              stroke="currentColor" 
              stroke-width="3" 
              stroke-linecap="round"
              transform="rotate({180 * pct})" 
              class="transition-transform duration-300 ease-out text-text"
            />
            <circle cx="0" cy="0" r="5" fill="currentColor" class="text-text" />
            <circle cx="0" cy="0" r="2" fill="var(--card)" />
          </g>
        </svg>
        
        <!-- Max indicator -->
        <div class="flex flex-col items-end gap-1">
          <div class="w-2 h-2 rounded-full bg-text/30"></div>
          <div class="text-xs font-approachmono text-text/50">{max}</div>
        </div>
      </div>

      <!-- value display  -->
      <div class="text-center space-y-2">
        <div class="text-3xl font-bold font-approachmono text-text tracking-tight">
          {fmt(value)}{unit ? ` ${unit}` : ''}
        </div>
        {#if label}
          <div class="text-sm text-text/70 font-approachmono">{label}</div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
  .thin-border { 
    border-color: var(--edge); 
    border-width: 1px;
  }
</style>