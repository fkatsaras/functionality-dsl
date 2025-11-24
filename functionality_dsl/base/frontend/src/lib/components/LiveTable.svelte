<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import EmptyState from "../primitives/icons/EmptyState.svelte";
    import { subscribe } from "$lib/ws";

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

    const props = $props<{
        streamPath: string;
        keyField: string;
        colNames: string[];
        columns?: ColumnInfo[];
        label?: string;
        maxRows?: number;
        name?: string;
    }>();

    // defaults
    const label = props.label ?? "Live Table";
    const maxRows = props.maxRows ?? 100;
    const columns = props.columns ?? props.colNames.map(name => ({
        name,
        type: { baseType: "string" }
    }));

    // reactive state
    let connected = $state(false);
    let error = $state<string | null>(null);
    let rowsMap = $state<Map<any, any>>(new Map()); // key -> row data
    let orderedKeys = $state<any[]>([]); // maintain insertion order

    let unsub: null | (() => void) = null;

    function handleStream(msg: any) {
        // meta events
        if (msg?.__meta === "open") {
            connected = true;
            return;
        }
        if (msg?.__meta === "close") {
            connected = false;
            return;
        }
    
        connected = true;
    
        // Extract array of messages (or single message)
        const messages = props.arrayField
            ? (msg?.[props.arrayField] ?? [])
            : [msg];
    
        for (const item of messages) {
            const key = item?.[props.keyField];
        
            if (key === undefined || key === null) {
                console.warn(
                    `Received item without keyField '${props.keyField}':`,
                    item
                );
                continue;
            }
        
            // Update existing row
            if (rowsMap.has(key)) {
                rowsMap.set(key, item);
            } else {
                // Insert new row
                rowsMap.set(key, item);
                orderedKeys = [...orderedKeys, key];
            
                // Enforce maxRows (FIFO)
                if (orderedKeys.length > maxRows) {
                    const removedKey = orderedKeys.shift();
                    if (removedKey !== undefined) {
                        rowsMap.delete(removedKey);
                    }
                }
            }
        }
    
        // Trigger Svelte reactivity
        rowsMap = rowsMap;
        orderedKeys = orderedKeys;
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

        // Format based on type (same as Table component)
        switch (typeInfo.baseType) {
            case "integer":
            case "number":
                if (typeof value === "number") {
                    if (typeInfo.baseType === "number") {
                        return value.toFixed(2);
                    }
                    return String(value);
                }
                return String(value);

            case "boolean":
                return value ? "✓" : "✗";

            case "string":
                if (typeInfo.format) {
                    switch (typeInfo.format) {
                        case "date":
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
                            return String(value);

                        case "email":
                        case "uri":
                        case "image":
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
        if (!props.streamPath) {
            error = "No streamPath provided";
            return;
        }

        unsub = subscribe(props.streamPath, handleStream);

        onDestroy(() => {
            unsub?.();
            unsub = null;
        });
    });
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="w-full flex justify-between items-center">
            <span class="font-approachmono text-xl">{label}</span>
            <div class="flex items-center gap-2">
                {#if orderedKeys.length > 0}
                    <span class="text-xs text-text-muted font-approachmono">
                        {orderedKeys.length} row{orderedKeys.length !== 1 ? 's' : ''}
                    </span>
                {/if}
                <LiveIndicator connected={connected} />
            </div>
        </div>

        {#if error}
            <div class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded mt-2">
                {error}
            </div>
        {/if}
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="overflow-x-auto w-full">
            <table class="min-w-full border-collapse text-sm font-mono">
                <thead class="bg-[color:var(--surface)] sticky top-0 z-10">
                    <tr>
                        {#each props.colNames as displayName}
                            <th class="text-left px-3 py-2 border-b border-[color:var(--edge)] font-mono text-text/90 tracking-wide">
                                {displayName}
                            </th>
                        {/each}
                    </tr>
                </thead>

                <tbody>
                    {#if orderedKeys.length === 0}
                        <tr>
                            <td colspan={props.colNames.length} class="text-center py-20">
                                {#if !error}
                                    <EmptyState message="Waiting for data..." />
                                {/if}
                            </td>
                        </tr>
                    {:else}
                        {#each orderedKeys as key (key)}
                            {@const row = rowsMap.get(key)}
                            <tr class="odd:bg-transparent even:bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition-colors">
                                {#each props.colNames as displayName, position}
                                    {@const column = columns[position] || { name: displayName, type: { baseType: "string" } }}
                                    {@const rawValue = getValueByName(row, column.name)}

                                    <td class="px-3 py-2 border-b border-[color:var(--edge)] text-text/90 font-mono">
                                        {#if column.type?.format === "image" && rawValue}
                                            <img src={String(rawValue)} class="max-w-24 max-h-24 object-contain rounded" alt={column.name} />
                                        {:else if column.type?.format === "binary" && rawValue}
                                            <img src={`data:image/png;base64,${String(rawValue)}`} class="max-w-24 max-h-24 object-contain rounded" alt={column.name} />
                                        {:else if column.type?.format === "uri" && rawValue && (String(rawValue).match(/\.(jpg|jpeg|png|gif|webp)$/i))}
                                            <img src={String(rawValue)} class="max-w-24 max-h-24 object-contain rounded" alt={column.name} />
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
        background: #0f141c;
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

    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
