<script lang="ts">
    import { onMount } from "svelte";
    import RefreshButton from "$lib/components/util/RefreshButton.svelte";

    const {
        url = null,
        colNames = [],
        name = "Table"
    } = $props<{
        url?: string | null;
        colNames?: string[];
        name?: string;
    }>();

    let data = $state<any[]>([]);
    let loading = $state(!!url);
    let error = $state<string | null>(null);

    async function load() {
        if (!url) return;
        loading = true;
        error = null;

        try {
          const response = await fetch(url);
          if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);

          const json = await response.json();

          if (Array.isArray(json)) {
              if (
                  json.length === 1 &&
                  typeof json[0] === "object" &&
                  Object.keys(json[0]).length === 1
              ) {
                  // Case: [{"lol": [...]}] → unwrap to [...]
                  const firstKey = Object.keys(json[0])[0];
                  data = json[0][firstKey];
                  console.log("Unwrapped single-field object:", firstKey, data);
              } else {
                  // Already a plain array of rows
                  data = json;
              }
          } else if (json && typeof json === "object") {
              // Case: { "lol": [...] }
              const keys = Object.keys(json);
              if (keys.length === 1 && Array.isArray(json[keys[0]])) {
                  data = json[keys[0]];
                  console.log("Unwrapped object:", keys[0], data);
              } else {
                  throw new Error("Response JSON is not a list or single-field object containing a list.");
              }
          } else {
              throw new Error("Unexpected response format.");
          }      
        } catch (err: any) {
            error = err?.message ?? "Failed to load data from source.";
            data = [];
        } finally {
            loading = false;
        }
    }

    function colValue(row: any, key: string) {
        return key.split('.').reduce((acc: any, k: string) => (acc ? acc[k] : undefined), row);
    }

    onMount(load);
</script>


<div class="w-full flex justify-center items-center">
  <div class="w-4/5">

    <!-- Card -->
    <div class="rounded-2xl shadow-card border table-border bg-[color:var(--card)]">

      <!-- Header -->
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>

        <div class="flex items-center gap-2">
          <RefreshButton on:click={load} {loading} ariaLabel="Refresh table" />
          {#if error}
            <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">
              {error}
            </span>
          {/if}
        </div>
      </div>

      <!-- Scroll area only for the table -->
      <div class="overflow-auto">
        <table class="min-w-full border-collapse text-sm">
          <thead class="bg-[color:var(--surface)] sticky top-0 z-10">
            <tr>
              {#each colNames as key}
                <th class="text-left font-approachmono font-medium text-text/90 px-3 py-2 border-b thin-border">
                  {key.replace('_',' ').replace('-',' ')}
                </th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#if loading}
              <tr><td class="font-approachmono px-3 py-4 text-text-muted" colspan={colNames.length}>Loading…</td></tr>
            {:else if error}
              <tr><td class="font-approachmono px-3 py-4 text-dag-danger" colspan={colNames.length}>{error}</td></tr>
            {:else if data.length === 0}
              <tr><td class="font-approachmono px-3 py-4 text-text-muted" colspan={colNames.length}>No data</td></tr>
            {:else}
              {#each data as row, i (`row-${i}`)}
                <tr class="font-approachmono odd:bg-transparent even:bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition-colors">
                  {#each colNames as key}
                    <td class="px-3 py-2 border-b thin-border text-text/90">{colValue(row, key)}</td>
                  {/each}
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }
    .thin-border, .table-border { border-color: var(--edge); }
</style>
