<script lang="ts">
    import { onMount } from "svelte";
    import RefreshButton from "$lib/components/util/RefreshButton.svelte";

    interface ColumnInfo {
        name: string;
        type?: {
            baseType: string;
            format?: string;
            min?: number;
            max?: number;
            exact?: number;
            nullable?: boolean;
        };
    }

    const {
        url = null,
        colNames = [],
        columns = [],
        name = "Table"
    } = $props<{
        url?: string | null;
        colNames?: string[];
        columns?: ColumnInfo[];
        name?: string;
    }>();

    let data = $state<any[]>([]);
    let loading = $state(false);
    let error = $state<string | null>(null);
    let entityKeys = $state<string[]>([]);

    async function load() {
        const finalUrl = url || "";
        if (!finalUrl) {
            error = "No URL provided";
            return;
        }

        loading = true;
        error = null;

        try {
          const response = await fetch(finalUrl);
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
            const keys = Object.keys(json);
            if (keys.length === 1) {
              const first = json[keys[0]];
              if (Array.isArray(first)) {
                data = first;
              } else if (first && typeof first === "object") {
                // Handles { WeatherCompareAPI: { rows: [...] } }
                const innerKeys = Object.keys(first);
                if (innerKeys.length === 1 && Array.isArray(first[innerKeys[0]])) {
                  data = first[innerKeys[0]];
                } else {
                  throw new Error("Expected object with single array field inside entity.");
                }
              } else {
                throw new Error("Expected entity object or array.");
              }
            } else {
              // Multiple keys - find the first array field
              const arrayKey = keys.find(k => Array.isArray(json[k]));
              if (arrayKey) {
                data = json[arrayKey];
                console.log("Found array field in multi-key response:", arrayKey);
              } else {
                throw new Error("Expected single entity key or an object with an array field.");
              }
            }
          }

          // Extract entity keys from the first row for position-based mapping
          if (data.length > 0 && typeof data[0] === "object") {
              entityKeys = Object.keys(data[0]);
              console.log("Entity keys:", entityKeys);
          }
        } catch (err: any) {
            error = err?.message ?? "Failed to load data from source.";
            data = [];
            entityKeys = [];
        } finally {
            loading = false;
        }
    }

    function getValueByPosition(row: any, position: number) {
        if (position < 0 || position >= entityKeys.length) return undefined;
        const key = entityKeys[position];
        return row[key];
    }

    function formatValue(value: any, column: ColumnInfo): string {
        if (value === null || value === undefined) {
            return column.type?.nullable ? "null" : "—";
        }

        const typeInfo = column.type;
        if (!typeInfo) return String(value);

        // Format based on type
        switch (typeInfo.baseType) {
            case "integer":
            case "number":
                if (typeof value === "number") {
                    // Apply decimal precision for numbers
                    if (typeInfo.baseType === "number") {
                        return value.toFixed(2);
                    }
                    return String(value);
                }
                return String(value);

            case "boolean":
                return value ? "✓" : "✗";

            case "string":
                // Format based on string format
                if (typeInfo.format) {
                    switch (typeInfo.format) {
                        case "date":
                            // Parse and format date if it's an ISO string
                            if (typeof value === "string") {
                                try {
                                    const date = new Date(value);
                                    return date.toLocaleDateString();
                                } catch {
                                    return String(value);
                                }
                            }
                            return String(value);

                        case "time":
                            // Format time
                            if (typeof value === "string") {
                                return value; // Already in time format
                            }
                            return String(value);

                        case "email":
                            return String(value);

                        case "uri":
                            // Return as-is for URI (will be handled specially in rendering)
                            return String(value);

                        case "image":
                            // Return as-is for images (will be rendered as <img>)
                            return String(value);

                        default:
                            return String(value);
                    }
                }
                return String(value);

            case "array":
                if (Array.isArray(value)) {
                    return `[${value.length} items]`;
                }
                return String(value);

            case "object":
                if (typeof value === "object") {
                    return "{...}";
                }
                return String(value);

            default:
                return String(value);
        }
    }

    onMount(() => {
        load();
    });
</script>


<div class="w-full flex justify-center items-center">
  <div class="w-4/5">

    <!-- Card -->
    <div class="rounded-2xl shadow-card border table-border bg-[color:var(--card)]">

      <!-- Header -->
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>

        <div class="flex items-center gap-2">
          <RefreshButton onclick={load} {loading} ariaLabel="Refresh table" />
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
              {#each colNames as displayName}
                <th class="text-left font-approachmono font-medium text-text/90 px-3 py-2 border-b thin-border">
                  {displayName}
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
                  {#each colNames as displayName, position}
                    {@const column = columns[position] || { name: displayName, type: { baseType: "string" } }}
                    {@const rawValue = getValueByPosition(row, position)}
                    <td class="px-3 py-2 border-b thin-border text-text/90">
                      {#if column.type?.format === "image" && rawValue}
                        <img src={String(rawValue)} alt={displayName} class="max-w-24 max-h-24 object-contain rounded" />
                      {:else if column.type?.format === "binary" && rawValue}
                        <!-- Base64 encoded image -->
                        <img src={`data:image/png;base64,${String(rawValue)}`} alt={displayName} class="max-w-24 max-h-24 object-contain rounded" />
                      {:else if column.type?.format === "uri" && rawValue && (String(rawValue).endsWith('.jpg') || String(rawValue).endsWith('.jpeg') || String(rawValue).endsWith('.png') || String(rawValue).endsWith('.gif') || String(rawValue).endsWith('.webp'))}
                        <img src={String(rawValue)} alt={displayName} class="max-w-24 max-h-24 object-contain rounded" />
                      {:else}
                        {formatValue(rawValue, column)}
                      {/if}
                    </td>
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