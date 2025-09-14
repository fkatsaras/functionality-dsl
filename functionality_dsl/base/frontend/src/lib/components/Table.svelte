<script lang="ts">
    import { onMount } from "svelte";
    import RefreshButton from "$lib/components/util/RefreshButton.svelte";

    const {
        rows = null,
        url = null,
        columns = [],
        primaryKey = "id",
        name = "Table"
    } = $props<{
        rows?: any[] | null;
        url?: string | null;
        columns?: Array<{ key: string; label: string }>;
        primaryKey?: string;
        name?: string;
    }>();

    let data = $state<any[]>(rows ?? []);
    let loading = $state(!rows && !!url);
    let error = $state<string | null>(null);

    async function load() {
        if (!url) return;
        loading = true;
        error = null;

        try {
            const response = await fetch(url);

            if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
            data = await response.json();
        } catch (err: any) {
            error = err?.message ?? 'Failed to load data from source.'; 
        } finally {
            loading = false;
        }
    }

    function colValue(row: any, key: string){
        return key.split('.').reduce((acc: any, k: string) => (acc ? acc[k] : undefined), row);
    }

    onMount(async () => {
        if (rows) return;
        await load();
    });
</script>

<div class="w-full flex justify-center items-center">
  <div class="w-4/5">

    <!-- Card -->
    <div class="rounded-2xl shadow-card border table-border bg-[color:var(--card)]">

      <!-- Header -->
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <h2 class="text-base font-approachmono text-text/90 tracking-tight font-medium">{name}</h2>

        <!-- Right controls grouped (prevents weird spacing when error appears) -->
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
              {#each columns as c}
                <th class="text-left font-approachmono font-medium text-text/90 px-3 py-2 border-b thin-border">
                  {c.label}
                </th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#if loading}
              <tr><td class="font-approachmono px-3 py-4 text-text-muted" colspan={columns.length}>Loading…</td></tr>
            {:else if error}
              <tr><td class="font-approachmono px-3 py-4 text-dag-danger" colspan={columns.length}>{error}</td></tr>
            {:else if data.length === 0}
              <tr><td class="font-approachmono px-3 py-4 text-text-muted" colspan={columns.length}>No data</td></tr>
            {:else}
              {#each data as row, i (`${row?.id ?? row?.[primaryKey] ?? JSON.stringify(row)}-${i}`)}
                <tr class="font-approachmono odd:bg-transparent even:bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition-colors">
                  {#each columns as c}
                    <td class="px-3 py-2 border-b thin-border text-text/90">{colValue(row, c.key)}</td>
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