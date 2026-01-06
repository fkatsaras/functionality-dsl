<script lang="ts">
    import { onMount } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import BarChart from "$lib/primitives/BarChart.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";

    const props = $props<{
        url: string;
        barFields: Array<{ field: string; label: string; color?: string }>;
        title?: string;
        xLabel?: string;
        yLabel?: string;
        height?: number;
        width?: number;
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

    function transformToBars(): Array<{ label: string; value: number; color?: string }> {
        if (!data) return [];

        return props.barFields.map((bar) => ({
            label: bar.label,
            value: Number(data[bar.field]) || 0,
            color: bar.color,
        }));
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

    const bars = $derived(transformToBars());
</script>

<Card fullWidth>
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
            <p class="text-sm text-[var(--text-muted)]">Loading...</p>
        </div>
    {:else if error}
        <div class="state-container">
            <p class="text-sm text-[var(--red-text)]">Error: {error}</p>
        </div>
    {:else if data && bars.length > 0}
        <BarChart
            bars={bars}
            xLabel={props.xLabel}
            yLabel={props.yLabel}
            height={props.height}
            width={props.width}
        />
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
