<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import KeyValue from "$lib/primitives/KeyValue.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import ErrorState from "../primitives/icons/ErrorState.svelte";

    const props = $props<{
        url: string;
        fields: string[];
        title?: string;
        highlight?: string;
        refreshMs?: number;
    }>();

    let data = $state<Record<string, any> | null>(null);
    let error = $state<string | null>(null);
    let loading = $state(true);
    let interval: ReturnType<typeof setInterval> | null = null;
    let authToken = $state<string | null>(null);

    // Subscribe to auth store to get token
    authStore.subscribe((state) => {
        authToken = state.token;
    });

    async function fetchData() {
        if (!props.url) return;

        try {
            const headers: Record<string, string> = {};
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            const res = await fetch(props.url, { headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            data = await res.json();
            error = null;
        } catch (e: any) {
            error = e.message || "Failed to fetch data";
            data = null;
        } finally {
            loading = false;
        }
    }

    function formatFieldName(field: string): string {
        // Convert snake_case or camelCase to Title Case
        return field
            .replace(/_/g, " ")
            .replace(/([A-Z])/g, " $1")
            .trim()
            .split(" ")
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(" ");
    }

    function formatValue(val: any): string {
        if (val === null || val === undefined) return "-";
        if (typeof val === "boolean") return val ? "Yes" : "No";
        if (typeof val === "number") return val.toLocaleString();
        if (Array.isArray(val)) return `[${val.length} items]`;
        if (typeof val === "object") return JSON.stringify(val);
        return String(val);
    }

    onMount(() => {
        fetchData();

        if (props.refreshMs && props.refreshMs > 0) {
            interval = setInterval(fetchData, props.refreshMs);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    });
</script>

<Card fullWidth>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center">
            {#if props.title}
                <h3 class="text-lg font-medium text-[var(--text)]">{props.title}</h3>
            {/if}
            <RefreshButton onRefresh={fetchData} {loading} />
        </div>
    </svelte:fragment>

    {#if loading}
        <div class="state-container">
            <EmptyState />
            
        </div>
    {:else if error}
        <div class="state-container">
            <ErrorState message={error} />
        </div>
    {:else if data}
        <div class="fields-container">
            {#each props.fields as field}
                {@const isHighlight = field === props.highlight}
                <div class:highlight={isHighlight}>
                    <KeyValue
                        label={formatFieldName(field)}
                        value={formatValue(data[field])}
                        class={isHighlight ? "font-semibold" : ""}
                    />
                </div>
            {/each}
        </div>
    {:else}
        <EmptyState />
    {/if}
</Card>

<style>
    .state-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        padding: 2rem 1rem;
    }

    .fields-container {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .highlight {
        background-color: var(--surface-secondary);
        border-radius: 4px;
        padding: 0.25rem 0.5rem;
    }
</style>
