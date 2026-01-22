<script lang="ts">
    import { onMount } from "svelte";
    import { Thermometer, Droplets, Power } from "lucide-svelte";
    import Card from "$lib/primitives/Card.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import Dial from "$lib/primitives/Dial.svelte";

    const props = $props<{
        url: string;
        title?: string;
        minTemp?: number;
        maxTemp?: number;
    }>();

    const MIN_TEMP = props.minTemp ?? 50;
    const MAX_TEMP = props.maxTemp ?? 90;

    let data = $state<{
        current_temp_f: number;
        target_temp_f: number;
        mode: string;
        humidity_percent: number;
    } | null>(null);
    let error = $state<string | null>(null);
    let loading = $state(true);
    let updating = $state(false);

    // Local target for dial interaction (preview before commit)
    let localTarget = $state(70);

    // Sync local target when data loads
    $effect(() => {
        if (data && !updating) {
            localTarget = data.target_temp_f;
        }
    });

    async function fetchData() {
        try {
            const res = await fetch(props.url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            data = await res.json();
            error = null;
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    async function updateTarget(newTarget: number) {
        if (!data || updating) return;

        const clampedTarget = Math.round(Math.min(MAX_TEMP, Math.max(MIN_TEMP, newTarget)));
        if (clampedTarget === data.target_temp_f) return;

        updating = true;
        try {
            const res = await fetch(props.url, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    target_temp_f: clampedTarget,
                    mode: data.mode
                })
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            data = await res.json();
        } catch (e: any) {
            error = e.message;
        } finally {
            updating = false;
        }
    }

    function handleDialChange(value: number) {
        localTarget = value;
    }

    function handleDialCommit(value: number) {
        updateTarget(value);
    }

    onMount(() => {
        fetchData();
    });

    // Computed values
    const isHeating = $derived(data ? data.current_temp_f < localTarget : false);
    const isCooling = $derived(data ? data.current_temp_f > localTarget : false);
    const dialMode = $derived<"heating" | "cooling" | "off">(
        isHeating ? "heating" : isCooling ? "cooling" : "off"
    );
</script>

<Card fullWidth>
    <svelte:fragment slot="header">
        <div class="header">
            <div class="header-left">
                <Thermometer size={18} />
                <span>{props.title || "Thermostat"}</span>
            </div>
            <RefreshButton onRefresh={fetchData} {loading} />
        </div>
    </svelte:fragment>

    {#if loading}
        <div class="loading-state">
            <div class="loader"></div>
        </div>
    {:else if error}
        <div class="error-state">
            <span class="error-text">{error}</span>
        </div>
    {:else if data}
        <div class="thermostat-body">
            <!-- Digital Display - Current Temperature -->
            <div class="digital-display">
                <div class="current-temp">
                    <span class="temp-value">{data.current_temp_f}</span>
                    <span class="temp-unit">°F</span>
                </div>
                <div class="temp-label">Current</div>
            </div>

            <!-- Dial with value display below -->
            <div class="dial-section">
                <Dial
                    value={localTarget}
                    min={MIN_TEMP}
                    max={MAX_TEMP}
                    size={180}
                    mode={dialMode}
                    onChange={handleDialChange}
                    onCommit={handleDialCommit}
                    disabled={updating}
                >
                    <div slot="value" class="dial-value-display">
                        <span class="target-value">{localTarget}<span class="target-unit">°F</span></span>
                        <span class="target-label">Target</span>
                    </div>
                </Dial>
            </div>

            <!-- Status row -->
            <div class="status-row">
                <div class="status-item">
                    <Droplets size={16} class="status-icon" />
                    <span class="status-value">{data.humidity_percent}%</span>
                    <span class="status-label">Humidity</span>
                </div>
                <div class="status-item">
                    <Power size={16} class="status-icon" />
                    <Badge class={data.mode === "off" ? "mode-off" : "mode-on"}>
                        {data.mode.toUpperCase()}
                    </Badge>
                </div>
            </div>
        </div>
    {/if}

    <svelte:fragment slot="footer">
        {#if data}
            <div class="footer-content">
                {#if isHeating}
                    <span class="heating-indicator">Heating to {localTarget}°F</span>
                {:else if isCooling}
                    <span class="cooling-indicator">Cooling to {localTarget}°F</span>
                {:else}
                    <span class="stable-indicator">Temperature stable</span>
                {/if}
            </div>
        {/if}
    </svelte:fragment>
</Card>

<style>
    .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--text);
        font-weight: 500;
    }

    .loading-state, .error-state {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 3rem;
    }

    .loader {
        width: 32px;
        height: 32px;
        border: 3px solid var(--edge-soft);
        border-top-color: var(--accent);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .error-text {
        color: var(--red-text);
        font-size: 0.875rem;
    }

    .thermostat-body {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1.5rem 1rem;
        gap: 1.5rem;
    }

    /* Digital Display */
    .digital-display {
        display: flex;
        flex-direction: column;
        align-items: center;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
    }

    .current-temp {
        display: flex;
        align-items: flex-start;
        font-family: "Approach Mono", monospace;
    }

    .temp-value {
        font-size: 2.5rem;
        font-weight: 500;
        color: var(--text);
        line-height: 1;
        letter-spacing: -0.02em;
    }

    .temp-unit {
        font-size: 1rem;
        color: var(--text-muted);
        margin-top: 0.25rem;
    }

    .temp-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Dial Section */
    .dial-section {
        display: flex;
        justify-content: center;
    }

    .dial-value-display {
        display: flex;
        flex-direction: column;
        align-items: center;
        font-family: "Approach Mono", monospace;
    }

    .target-value {
        font-size: 1.75rem;
        font-weight: 500;
        color: var(--text);
        line-height: 1;
    }

    .target-unit {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-left: 0.125rem;
    }

    .target-label {
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.25rem;
    }

    /* Status Row */
    .status-row {
        display: flex;
        gap: 2rem;
        padding-top: 0.5rem;
        border-top: 1px solid var(--edge-soft);
        width: 100%;
        justify-content: center;
    }

    .status-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
    }

    .status-item :global(.status-icon) {
        color: var(--text-muted);
    }

    .status-value {
        font-size: 1rem;
        font-weight: 500;
        color: var(--text);
        font-family: "Approach Mono", monospace;
    }

    .status-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    :global(.mode-off) {
        background: var(--surface) !important;
        color: var(--text-muted) !important;
        border: 1px solid var(--edge) !important;
    }

    :global(.mode-on) {
        background: var(--green-tint) !important;
        color: var(--green-text) !important;
        border: 1px solid var(--green-text) !important;
    }

    /* Footer */
    .footer-content {
        width: 100%;
        text-align: center;
        font-size: 0.875rem;
        font-family: "Approach Mono", monospace;
    }

    .heating-indicator {
        color: var(--warning-text);
    }

    .cooling-indicator {
        color: var(--accent);
    }

    .stable-indicator {
        color: var(--green-text);
    }
</style>
