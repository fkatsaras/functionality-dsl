<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import InfoIcon from "$lib/primitives/icons/InfoIcon.svelte";
    import WarningIcon from "$lib/primitives/icons/WarningIcon.svelte";
    import CriticalIcon from "$lib/primitives/icons/CriticalIcon.svelte";

    const props = $props<{
        name?: string;
        url: string;
        condition: string;
        message: string;
        severity?: "info" | "warning" | "error";
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
        {#if props.refreshMs}
            <RefreshButton onclick={fetchData} />
        {/if}
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
</style>
