<script lang="ts">
    import { onMount } from "svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import InfoIcon from "$lib/primitives/icons/InfoIcon.svelte";
    import WarningIcon from "$lib/primitives/icons/WarningIcon.svelte";
    import CriticalIcon from "$lib/primitives/icons/CriticalIcon.svelte";

    const props = $props<{
        name?: string;
        wsUrl: string;
        condition: string;
        message: string;
        severity?: "info" | "warning" | "error";
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

    const shouldShow = $derived(data && !!data[props.condition]);
    const severity = $derived(props.severity || "info");
</script>

{#if shouldShow}
    <div class="alert" class:info={severity === "info"} class:warning={severity === "warning"} class:error={severity === "error"}>
        <div class="alert-icon">
            {#if severity === "info"}
                <InfoIcon />
            {:else if severity === "warning"}
                <WarningIcon />
            {:else if severity === "error"}
                <CriticalIcon />
            {/if}
        </div>
        <div class="alert-message">
            {props.message}
        </div>
        <span class="status-dot" class:connected></span>
    </div>
{/if}

<style>
    .alert {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid;
        font-family: "Approach Mono", monospace;
        margin: 0.5rem 0;
    }

    .alert.info {
        background-color: rgba(59, 130, 246, 0.1);
        border-color: #3b82f6;
        color: #3b82f6;
    }

    .alert.warning {
        background-color: rgba(245, 158, 11, 0.1);
        border-color: #f59e0b;
        color: #f59e0b;
    }

    .alert.error {
        background-color: rgba(239, 68, 68, 0.1);
        border-color: #ef4444;
        color: #ef4444;
    }

    .alert-icon {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .alert-message {
        flex: 1;
        font-size: 0.875rem;
        font-weight: 500;
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
