<script lang="ts">
  import { onMount } from "svelte";
  import RefreshButton from "$lib/components/util/RefreshButton.svelte";
  import { buildUrlWithParams, buildQueryString } from "$lib/utils/paramBuilder";

  // Props
  const {
    name = "PageView",
    endpoint = "",
    pathParams = [],
    queryParams = [],
    fields = [],
    label = "",
  } = $props<{
    name?: string;
    endpoint?: string;
    pathParams?: string[];
    queryParams?: string[];
    fields?: string[];
    label?: string;
  }>();

  // State
  let pathValues = $state<Record<string, string>>({});
  let queryValues = $state<Record<string, string>>({});
  let data: Record<string, any> | null = $state(null);
  let loading = $state(false);
  let error: string | null = $state(null);

  // Initialize path param values
  $effect(() => {
    const initial: Record<string, string> = {};
    for (const param of pathParams) {
      initial[param] = "";
    }
    if (Object.keys(pathValues).length !== pathParams.length) {
      pathValues = initial;
    }
  });

  // Initialize query param values
  $effect(() => {
    const initial: Record<string, string> = {};
    for (const param of queryParams) {
      initial[param] = "";
    }
    if (Object.keys(queryValues).length !== queryParams.length) {
      queryValues = initial;
    }
  });

  function buildUrl() {
    if (!endpoint) return "";

    // Build URL with path params
    let url = buildUrlWithParams(endpoint, pathValues);
    if (!url && pathParams.length > 0) return "";

    // Add query params using reusable utility
    const queryString = buildQueryString(queryValues);
    if (queryString) {
      url += `?${queryString}`;
    }

    return url;
  }

  async function fetchData() {
    const finalUrl = buildUrl();
    if (!finalUrl) {
      error = "Please fill in required path parameters.";
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

  // Helper function to access nested fields
  function getNestedValue(obj: any, path: string): any {
    const keys = path.split('.');
    let current = obj;
    for (const key of keys) {
      if (current === null || current === undefined) return undefined;
      current = current[key];
    }
    return current;
  }

  onMount(() => {
    // Don't auto-load - user must click Get button
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
          <RefreshButton on:click={fetchData} {loading} ariaLabel="Refresh data" />
          {#if error}
            <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">{error}</span>
          {/if}
        </div>
      </div>

      <!-- Input Row -->
      <div class="flex flex-col gap-3 px-4 pb-3">
        <!-- Path Parameters -->
        {#if pathParams.length > 0}
          <div class="flex gap-2 flex-wrap">
            <span class="text-xs font-approachmono text-text/50 self-center">Path:</span>
            {#each pathParams as param}
              <input
                id="path-{param}"
                type="text"
                bind:value={pathValues[param]}
                class="px-3 py-2 text-sm border thin-border rounded font-approachmono bg-[color:var(--surface)] text-text focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder={param}
                onkeydown={(e) => e.key === 'Enter' && fetchData()}
              />
            {/each}
          </div>
        {/if}

        <!-- Query Parameters -->
        {#if queryParams.length > 0}
          <div class="flex gap-2 flex-wrap">
            <span class="text-xs font-approachmono text-text/50 self-center">Query:</span>
            {#each queryParams as param}
              <input
                id="query-{param}"
                type="text"
                bind:value={queryValues[param]}
                class="px-3 py-2 text-sm border thin-border rounded font-approachmono bg-[color:var(--surface)] text-text focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder={param}
                onkeydown={(e) => e.key === 'Enter' && fetchData()}
              />
            {/each}
          </div>
        {/if}

        <!-- Get Button -->
        <div class="flex gap-2">
          <button
            class="px-4 py-2 rounded bg-dag-success text-white font-approachmono transition-colors hover:bg-green-600 disabled:opacity-50"
            onclick={fetchData}
            disabled={loading || pathParams.some(p => !pathValues[p])}
          >
            Get
          </button>
        </div>
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
                <span class="text-text/70">{getNestedValue(data, f)}</span>
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
