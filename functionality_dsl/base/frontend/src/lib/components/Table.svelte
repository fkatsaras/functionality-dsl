<script lang="ts">
        import { onMount } from "svelte";
        import { authStore } from "$lib/stores/authStore";
        import RefreshButton from "$lib/primitives/RefreshButton.svelte";
        import Badge from "$lib/primitives/Badge.svelte";
        import Card from "$lib/primitives/Card.svelte";


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

        // Get initial auth state synchronously
        const initialAuth = authStore.getState();
        let authToken = $state<string | null>(initialAuth.token);
        let authType = $state<string>(initialAuth.authType);

        // Subscribe to auth store for updates
        authStore.subscribe((state) => {
                authToken = state.token;
                authType = state.authType;
        });

        async function load() {
                const finalUrl = url || "";
                if (!finalUrl) {
                        error = "No URL provided";
                        return;
                }

                loading = true;
                error = null;

                try {
                    const headers: Record<string, string> = {};
                    const fetchOptions: RequestInit = { headers };

                    // For JWT auth, use Authorization header
                    // For session auth, include credentials (cookies)
                    if (authType === 'jwt' && authToken) {
                        headers['Authorization'] = `Bearer ${authToken}`;
                    } else if (authType === 'session') {
                        fetchOptions.credentials = 'include';
                    }

                    const response = await fetch(finalUrl, fetchOptions);
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

        function getValueByName(row: any, fieldName: string) {
                return row[fieldName];
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


<Card class="table-card">
    <svelte:fragment slot="header">
        <div class="flex items-center justify-between w-full">
            <span>{name}</span>

            <div class="flex items-center gap-2">
                {#if error}
                    <Badge class="text-[var(--edge-light)] mt-2">{error}</Badge>
                {/if}
                <RefreshButton onRefresh={load} loading={loading} />
            </div>
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="overflow-x-auto w-full">
            <table class="min-w-full border-collapse text-sm font-mono">
                <thead class="bg-[color:var(--surface)] sticky top-0 z-10">
                    <tr>
                        {#each colNames as displayName}
                            <th class="text-left px-3 py-2 border-b border-[color:var(--edge)] font-mono text-text/90 tracking-wide">
                                {displayName}
                            </th>
                        {/each}
                    </tr>
                </thead>
            
                <tbody>
                    {#if data.length === 0}
                        <!-- Show nothing while loading and avoid shrinking -->
                        <tr>
                            <td colspan={colNames.length} class="h-10"></td>
                        </tr>
                    {:else}
                        {#each data as row, i (`row-${i}`)}
                            <tr class="odd:bg-transparent even:bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition-colors">
                                {#each colNames as displayName, position}
                                    {@const column = columns[position] || { name: displayName, type: { baseType: "string" } }}
                                    {@const rawValue = getValueByName(row, column.name)}
                            
                                    <td class="px-3 py-2 border-b border-[color:var(--edge)] text-text/90 font-mono">
                                        {#if column.type?.format === "image" && rawValue}
                                            <img src={String(rawValue)} class="max-w-24 max-h-24 object-contain rounded" />
                                        {:else if column.type?.format === "binary" && rawValue}
                                            <img src={`data:image/png;base64,${String(rawValue)}`} class="max-w-24 max-h-24 object-contain rounded" />
                                        {:else if column.type?.format === "uri" && rawValue && (String(rawValue).match(/\.(jpg|jpeg|png|gif|webp)$/i))}
                                            <img src={String(rawValue)} class="max-w-24 max-h-24 object-contain rounded" />
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
    </svelte:fragment>

</Card>

<style>

    table {
        width: 100%;
        border-spacing: 0;
    }

    thead th {
        background: #0f141c; /* darker than surface */
        border-bottom: 2px solid var(--edge-light);
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.03em;
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
    }

    th {
        background: var(--surface);
        font-size: 0.8rem;
        font-weight: 600;
        user-select: none;
    }

    td {
        font-size: 0.8rem;
    }

</style>