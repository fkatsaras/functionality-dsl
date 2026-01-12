<script lang="ts">
    import { onMount } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import ErrorState from "../primitives/icons/ErrorState.svelte";

    const props = $props<{
        name?: string;
        wsUrl: string;
        field: string;
        min?: number;
        max?: number;
        threshold?: number;
        label?: string;
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
        padding: 1rem;
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
