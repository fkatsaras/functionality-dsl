<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { subscribe } from "$lib/ws";

  const {
    streamPath,
    fields = [],
    label = "Live",
    maxMessages = 50,
    name = "LiveView",
  } = $props<{
    streamPath: string;
    fields: string[];
    label?: string;
    maxMessages?: number;
    name?: string;
  }>();

  let connected = $state(false);
  let error = $state<string | null>(null);
  let messages = $state<any[]>([]);

  let unsubscribe: (() => void) | null = null;

  function pickFields(msg: any) {
    const obj: Record<string, any> = {};
    for (const f of fields) obj[f] = msg?.[f];
    return obj;
  }

  onMount(() => {
    if (!streamPath) { error = "No streamPath"; return; }

    unsubscribe = subscribe(streamPath, (msg: any) => {
      if (msg?.__meta === "open") { connected = true; return; }
      if (msg?.__meta === "close") { connected = false; return; }

      connected = true;
      messages = [...messages, pickFields(msg)].slice(-maxMessages);
    });
  });

  onDestroy(() => { unsubscribe?.(); unsubscribe = null; });
</script>

<div class="w-full flex justify-center p-6">
  <!-- make container wider -->
  <div class="w-full max-w-3xl">
    <div
      class="rounded-2xl shadow-lg border bg-[color:var(--card)] p-6 flex flex-col gap-4 transition-shadow duration-200 hover:shadow-xl h-[600px]"
      class:border-dag-success={connected}
      class:border-dag-danger={!connected}
    >
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{label}</h2>
        <div
          class="flex items-center gap-2 px-2 py-1 rounded-md border"
          class:border-dag-success={connected}
          class:border-dag-danger={!connected}
        >
          <svg class="w-4 h-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"
            class:text-dag-success={connected}
            class:text-dag-danger={!connected}>
            <circle cx="10" cy="10" r="8.5" />
          </svg>
          <span class="text-xs font-approachmono"
            class:text-dag-success={connected}
            class:text-dag-danger={!connected}>
            {connected ? "LIVE" : "OFF"}
          </span>
        </div>
      </div>

      {#if error}
        <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">{error}</span>
      {/if}

      <!-- Messages -->
      <div class="flex-1 flex flex-col gap-2 overflow-y-auto rounded-md p-3 bg-dag-surface">
        {#each messages as msg}
          <div class="px-3 py-2 font-approachmono text-sm text-text border-b border-white/10">
            {#each fields as f}
              {msg[f]}{#if f !== fields[fields.length - 1]} · {/if}
            {/each}
          </div>
        {/each}
      </div>
    </div>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
</style>
