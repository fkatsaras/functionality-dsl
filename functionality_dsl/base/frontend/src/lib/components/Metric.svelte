<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import Metric from "$lib/primitives/Metric.svelte";
    import Card from "$lib/primitives/Card.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import UnauthorizedState from "../primitives/icons/UnauthorizedState.svelte";
    import ErrorState from "../primitives/icons/ErrorState.svelte";

    const props = $props<{
        url: string;
        field: string;
        label?: string;
        format?: "number" | "currency" | "percent" | string;
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

    function formatValue(val: any): string {
        if (val === null || val === undefined) return "-";

        if (props.format === "currency") {
            return `$${Number(val).toFixed(2)}`;
        }
        if (props.format === "percent") {
            return `${Number(val).toFixed(1)}%`;
        }
        if (props.format === "number" || typeof val === "number") {
            return Number(val).toLocaleString();
        }

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

    const value = $derived(data ? data[props.field] : null);
    const displayValue = $derived(formatValue(value));
    const displayLabel = $derived(props.label || props.field);
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center">
            <h3 class="text-sm font-medium text-[var(--text-muted)]">{displayLabel}</h3>
            {#if props.refreshMs}
                <RefreshButton onclick={fetchData} />
            {/if}
        </div>
    </svelte:fragment>

    {#if loading}
        <div class="loading-state">
            <EmptyState />
            
        </div>
    {:else if error === "401"}
        <UnauthorizedState />
    {:else if error}
        <ErrorState message={error} />
    {:else if data}
        <Metric value={displayValue} label={displayLabel} />
    {:else}
        <EmptyState />
    {/if}
</Card>

<style>
    .loading-state,
    .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        padding: 1rem;
    }
</style>
