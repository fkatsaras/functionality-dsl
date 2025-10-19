<script lang="ts">
  import { onMount } from "svelte";
  import RefreshButton from "$lib/components/util/RefreshButton.svelte";

  // Props (from backend-generated component)
  const {
    name = "ObjectView",
    endpoint = "",
    fields = [],
    label = "",
  } = $props<{
    name?: string;
    endpoint?: string;
    fields?: string[];
    label?: string;
  }>();

  // State
  let id = $state("");
  let data: Record<string, any> | null = $state(null);
  let loading = $state(false);
  let error: string | null = $state(null);

  function buildUrl() {
    if (!endpoint || !id.trim()) return "";
    return `${endpoint}/${encodeURIComponent(id.trim())}`;
  }

  async function fetchData() {
    const finalUrl = buildUrl();
    if (!finalUrl) {
      error = "Please enter an ID.";
      return;
    }

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

  onMount(() => {
    if (id) fetchData();
  });
</script>

<div class="w-full flex justify-center items-center">
  <div class="w-4/5">
    <!-- Card -->
    <div class="rounded-2xl shadow-card border table-border bg-[color:var(--card)] transition-shadow hover:shadow-md">
      <!-- Header -->
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{label || name}</h2>

        <div class="flex items-center gap-2">
          <RefreshButton on:click={fetchData} {loading} ariaLabel="Refresh object" />
          {#if error}
            <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">{error}</span>
          {/if}
        </div>
      </div>

      <!-- Input Row -->
      <div class="flex gap-2 px-4 pb-3">
        <input
          type="text"
          bind:value={id}
          placeholder="Enter ID..."
          class="border thin-border rounded px-3 py-2 flex-1 font-approachmono bg-[color:var(--surface)] text-text focus:outline-none focus:ring-2 focus:ring-blue-400"
          on:keydown={(e) => e.key === 'Enter' && fetchData()}
        />
        <button
          class="px-4 py-2 rounded bg-dag-success text-white font-approachmono transition-colors hover:bg-green-600 disabled:opacity-50"
          on:click={fetchData}
          disabled={loading || !id.trim()}
        >
          View
        </button>
      </div>

      <!-- Content -->
      <div class="px-4 pb-4">
        {#if loading}
          <p class="font-approachmono text-sm opacity-60">Loading…</p>
        {:else if error && !data}
          <p class="font-approachmono text-sm text-dag-danger">{error}</p>
        {:else if data}
          <div class="border-t thin-border divide-y divide-[color:var(--edge)]">
            {#each fields as f}
              <div class="flex justify-between py-2 px-1 even:bg-[color:var(--surface)] font-approachmono text-text/90">
                <span class="font-medium text-text/80">{f}</span>
                <span class="text-text/70">{data[f]}</span>
              </div>
            {/each}
          </div>
        {:else}
          <p class="font-approachmono text-sm opacity-60">No data loaded.</p>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
  .thin-border, .table-border {
    border-color: var(--edge);
  }
</style>
