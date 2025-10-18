<script lang="ts">
  import { onMount } from "svelte";
  import { RefreshButton } from "$lib/components/util/RefreshButton.svelte";

  export let name: string;
  export let url: string;
  export let fields: string[] = [];
  export let label: string = "";
  export let pathKey: string | null = null;
  export let value: string | number | null = null;

  let data: Record<string, any> | null = $state(null);
  let loading = $state(false);
  let error: string | null = $state(null);

  async function fetchData() {
    if (!url) return;
    let finalUrl = url;

    // Replace {pathKey} placeholder dynamically
    if (pathKey && value != null) {
      finalUrl = url.replace(`{${pathKey}}`, String(value));
    }

    console.log(`[ObjectView] Fetching ${finalUrl}`);

    loading = true;
    error = null;
    data = null;

    try {
      const res = await fetch(finalUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      data = await res.json();
    } catch (err) {
      error = String(err);
    } finally {
      loading = false;
    }
  }

  // Run on mount
  onMount(fetchData);

  //  React to value changes dynamically (runes style)
  $effect(() => {
    if (value != null) {
      fetchData();
    }
  });
</script>

<div
  class="rounded-2xl border bg-[color:var(--card)] p-6 w-full transition-colors"
  class:border-dag-success={loading}
  class:border-dag-danger={!loading}
>
  <div class="flex items-center justify-between mb-3">
    <h2 class="text-lg font-bold font-approachmono text-text/90">{label || name}</h2>
    <RefreshButton onclick={fetchData} />
  </div>

  {#if loading}
    <p class="text-sm opacity-60">Loading...</p>
  {:else if error}
    <p class="text-red-600 text-sm">Error: {error}</p>
  {:else if data}
    <div class="space-y-2">
      {#each fields as f}
        <div class="flex justify-between border-b border-border/30 pb-1">
          <span class="font-semibold text-text/80">{f}</span>
          <span class="text-text/70">{data[f]}</span>
        </div>
      {/each}
    </div>
  {:else}
    <p class="opacity-50 text-sm">No data loaded.</p>
  {/if}
</div>
