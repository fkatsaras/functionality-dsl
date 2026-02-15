<script lang="ts">
    import { onMount } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import PieChart from "$lib/primitives/PieChart.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import ErrorState from "../primitives/icons/ErrorState.svelte";

    const props = $props<{
        name?: string;
        wsUrl: string;
        sliceFields: Array<{ field: string; label: string; color: string }>;
        title?: string;
        size?: number;
    }>();

    let data = $state<Record<string, any> | null>(null);
    let error = $state<string | null>(null);
    let connected = $state(false);
    let ws: WebSocket | null = null;

    onMount(() => {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsPath = props.wsUrl.startsWith("/") ? props.wsUrl : `/${props.wsUrl}`;
        const fullWsUrl = `${protocol}//${window.location.host}${wsPath}`;

        ws = new WebSocket(fullWsUrl);

        ws.onopen = () => {
            connected = true;
            error = null;
        };

        ws.onmessage = (event) => {
            try {
                data = JSON.parse(event.data);
                error = null;
            } catch (e) {
                error = "Failed to parse message";
            }
        };

        ws.onerror = () => {
            error = "WebSocket error";
            connected = false;
        };

        ws.onclose = () => {
            connected = false;
        };

        return () => {
            if (ws) ws.close();
        };
    });

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

    const slices = $derived(transformToSlices());
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center w-full">
            {#if props.title}
                <h3 class="text-sm font-medium text-[var(--text)]">{props.title}</h3>
            {/if}
            <span class="status-dot" class:connected></span>
        </div>
    </svelte:fragment>

    {#if error}
        <div class="state-container">
            <ErrorState message={error} />
        </div>
    {:else if !connected}
        <div class="state-container">
            <EmptyState />
            <p class="text-sm text-[var(--text-muted)]">Connecting...</p>
        </div>
    {:else if data && slices.length > 0}
        <PieChart slices={slices} size={props.size} />
    {:else}
        <div class="state-container">
            <EmptyState />
            <p class="text-sm text-[var(--text-muted)]">Waiting for data...</p>
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

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #ef4444;
    }

    .status-dot.connected {
        background-color: #22c55e;
    }
</style>
