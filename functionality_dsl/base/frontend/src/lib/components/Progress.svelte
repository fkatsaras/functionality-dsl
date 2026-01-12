<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import ErrorState from "../primitives/icons/ErrorState.svelte";

    const props = $props<{
        name?: string;
        url: string;
        field: string;
        min?: number;
        max?: number;
        threshold?: number;
        label?: string;
        refreshMs?: number;
    }>();

    let data = $state<Record<string, any> | null>(null);
    let error = $state<string | null>(null);
    let loading = $state(true);
    let interval: ReturnType<typeof setInterval> | null = null;
    let authToken = $state<string | null>(null);

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

    onMount(() => {
        fetchData();

        if (props.refreshMs && props.refreshMs > 0) {
            interval = setInterval(fetchData, props.refreshMs);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    });

    const value = $derived(data ? Number(data[props.field]) || 0 : 0);
    const min = $derived(props.min ?? 0);
    const max = $derived(props.max ?? 100);
    const percentage = $derived(((value - min) / (max - min)) * 100);
    const isOverThreshold = $derived(
        props.threshold !== undefined && value > props.threshold
    );
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center w-full">
            <h3 class="text-sm font-medium" class:accent-text={!isOverThreshold} class:warning-text-header={isOverThreshold}>
                {props.label || props.field}
            </h3>
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
    {:else if data}
        <div class="progress-container">
            <div class="progress-value" class:warning={isOverThreshold}>
                {value.toFixed(1)} / {max}
            </div>
            <div class="progress-bar-bg">
                <div
                    class="progress-bar-fill"
                    class:warning={isOverThreshold}
                    style="width: {Math.min(100, Math.max(0, percentage))}%"
                ></div>
            </div>
            {#if isOverThreshold}
                <div class="warning-text">
                    ⚠️ Threshold exceeded ({props.threshold})
                </div>
            {/if}
        </div>
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
        padding: 1rem;
    }

    .progress-container {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: 0.5rem 0;
    }

    .progress-value {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--text);
        font-family: "Approach Mono", monospace;
    }

    .progress-value.warning {
        color: #f59e0b;
    }

    .progress-bar-bg {
        width: 100%;
        height: 1.5rem;
        background-color: var(--bg-subtle);
        border-radius: 0.5rem;
        overflow: hidden;
        border: 1px solid var(--edge);
    }

    .progress-bar-fill {
        height: 100%;
        background-color: var(--accent);
        transition: width 0.3s ease;
    }

    .progress-bar-fill.warning {
        background-color: #f59e0b;
    }

    .warning-text {
        font-size: 0.875rem;
        color: #f59e0b;
        font-family: "Approach Mono", monospace;
    }

    .accent-text {
        color: var(--accent);
    }

    .warning-text-header {
        color: #f59e0b;
    }
</style>
