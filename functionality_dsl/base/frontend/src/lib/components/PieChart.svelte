<script lang="ts">
    import { onMount } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import PieChart from "$lib/primitives/PieChart.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import ErrorState from "../primitives/icons/ErrorState.svelte";

    const props = $props<{
        url: string;
        sliceFields: Array<{ field: string; label: string; color: string }>;
        title?: string;
        size?: number;
        refreshMs?: number;
    }>();

    let data = $state<Record<string, any> | null>(null);
    let error = $state<string | null>(null);
    let loading = $state(true);
    let interval: ReturnType<typeof setInterval> | null = null;

    async function fetchData() {
        if (!props.url) return;

        try {
            const res = await fetch(props.url);
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

    function transformToSlices(): Array<{ label: string; value: number; color: string }> {
        if (!data) return [];

        return props.sliceFields
            .map((slice) => ({
                label: slice.label,
                value: Number(data[slice.field]) || 0,
                color: slice.color,
            }))
            .filter((slice) => slice.value > 0); // Filter out zero values
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

    const slices = $derived(transformToSlices());
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center">
            {#if props.title}
                <h3 class="text-sm font-medium text-[var(--text)]">{props.title}</h3>
            {/if}
            {#if props.refreshMs}
                <RefreshButton onclick={fetchData} />
            {/if}
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
    {:else if data && slices.length > 0}
        <PieChart slices={slices} size={props.size} />
    {:else}
        <div class="state-container">
            <EmptyState />
            <p class="text-sm text-[var(--text-muted)]">No data available</p>
        </div>
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
</style>
