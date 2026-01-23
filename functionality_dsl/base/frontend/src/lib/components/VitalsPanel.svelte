<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { Heart, Activity, Droplets, Thermometer, Wind, AlertTriangle } from "lucide-svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import Badge from "$lib/primitives/Badge.svelte";

    import { subscribe as wsSubscribe } from "$lib/ws";

    const props = $props<{
        wsUrl: string;
        restUrl?: string;
        title?: string;
    }>();

    // WebSocket data (real-time heart rate)
    interface HeartRateData {
        current_bpm: number;
        timestamp: number;
        status: string;
        needs_attention: boolean;
    }

    // REST data (vitals snapshot)
    interface VitalsData {
        heart_rate?: number;
        blood_pressure_systolic?: number;
        blood_pressure_diastolic?: number;
        temperature_c?: number;
        oxygen_saturation?: number;
        recorded_at?: string;
    }

    let wsData = $state<HeartRateData | null>(null);
    let restData = $state<VitalsData | null>(null);
    let connected = $state(false);
    let error = $state<string | null>(null);
    let unsub: (() => void) | null = null;

    // Heart rate history for mini chart
    let hrHistory = $state<number[]>([]);
    const maxHistory = 30;

    function handleWsMessage(msg: any) {
        if (msg?.__meta === "open") {
            connected = true;
            return;
        }
        if (msg?.__meta === "close") {
            connected = false;
            return;
        }
        connected = true;
        wsData = msg;

        // Add to history
        if (msg?.current_bpm) {
            hrHistory = [...hrHistory.slice(-(maxHistory - 1)), msg.current_bpm];
        }
    }

    async function fetchRestData() {
        if (!props.restUrl) return;
        try {
            const res = await fetch(props.restUrl);
            if (res.ok) {
                restData = await res.json();
            }
        } catch (e) {
            // REST data is optional, don't show error
        }
    }

    onMount(() => {
        if (!props.wsUrl || props.wsUrl === "None") {
            error = "No WebSocket URL provided";
            return;
        }
        unsub = wsSubscribe(props.wsUrl, handleWsMessage);
        fetchRestData();
    });

    onDestroy(() => {
        unsub?.();
    });

    // Computed values
    const bpm = $derived(wsData?.current_bpm ?? restData?.heart_rate ?? 0);
    const status = $derived(wsData?.status ?? "normal");
    const needsAttention = $derived(wsData?.needs_attention ?? false);

    const systolic = $derived(restData?.blood_pressure_systolic ?? 120);
    const diastolic = $derived(restData?.blood_pressure_diastolic ?? 80);
    const temp = $derived(restData?.temperature_c ?? 36.6);
    const o2 = $derived(restData?.oxygen_saturation ?? 98);

    // Status colors
    const statusColor = $derived(
        status === "critical" ? "var(--red-text)" :
        status === "elevated" ? "var(--warning-text)" :
        "var(--green-text)"
    );

    // Generate SVG path for mini heart rate chart
    const chartPath = $derived(() => {
        if (hrHistory.length < 2) return "";
        const minVal = Math.min(...hrHistory) - 5;
        const maxVal = Math.max(...hrHistory) + 5;
        const range = maxVal - minVal || 1;
        const width = 200;
        const height = 40;

        const points = hrHistory.map((v, i) => {
            const x = (i / (maxHistory - 1)) * width;
            const y = height - ((v - minVal) / range) * height;
            return `${x},${y}`;
        });

        return `M ${points.join(" L ")}`;
    });
</script>

<Card fullWidth>
    <svelte:fragment slot="header">
        <div class="header">
            <div class="header-left">
                <Activity size={20} />
                <span class="title">{props.title || "Vitals Monitor"}</span>
            </div>
            <div class="header-right">
                {#if needsAttention}
                    <Badge class="alert-badge">
                        <AlertTriangle size={12} />
                        ATTENTION
                    </Badge>
                {/if}
                <LiveIndicator {connected} />
            </div>
        </div>
    </svelte:fragment>

    <div class="vitals-body">
        {#if error}
            <div class="error-state">
                <span class="error-text">{error}</span>
            </div>
        {:else}
            <!-- Main Heart Rate Display -->
            <div class="heart-rate-section">
                <div class="hr-display">
                    <div class="hr-icon" class:critical={status === "critical"} class:elevated={status === "elevated"}>
                        <Heart size={32} fill={statusColor} color={statusColor} class="heart-icon" />
                    </div>
                    <div class="hr-value-container">
                        <span class="hr-value" style="color: {statusColor}">{bpm}</span>
                        <span class="hr-unit">BPM</span>
                    </div>
                    <Badge class="status-badge status-{status}">
                        {status.toUpperCase()}
                    </Badge>
                </div>

                <!-- Mini Heart Rate Chart -->
                <div class="hr-chart">
                    <svg viewBox="0 0 200 40" preserveAspectRatio="none">
                        <path
                            d={chartPath()}
                            fill="none"
                            stroke={statusColor}
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        />
                    </svg>
                    <div class="chart-label">Real-time heart rate</div>
                </div>
            </div>

            <!-- Secondary Vitals Grid -->
            <div class="vitals-grid">
                <!-- Blood Pressure -->
                <div class="vital-card">
                    <div class="vital-icon bp">
                        <Activity size={18} />
                    </div>
                    <div class="vital-info">
                        <span class="vital-value">{systolic}/{diastolic}</span>
                        <span class="vital-label">Blood Pressure</span>
                        <span class="vital-unit">mmHg</span>
                    </div>
                </div>

                <!-- Oxygen Saturation -->
                <div class="vital-card">
                    <div class="vital-icon o2" class:low={o2 < 95} class:critical={o2 < 90}>
                        <Wind size={18} />
                    </div>
                    <div class="vital-info">
                        <span class="vital-value" class:warning={o2 < 95} class:critical={o2 < 90}>{o2}%</span>
                        <span class="vital-label">O₂ Saturation</span>
                        <span class="vital-unit">SpO₂</span>
                    </div>
                </div>

                <!-- Temperature -->
                <div class="vital-card">
                    <div class="vital-icon temp" class:elevated={temp > 37.5}>
                        <Thermometer size={18} />
                    </div>
                    <div class="vital-info">
                        <span class="vital-value" class:warning={temp > 37.5}>{temp.toFixed(1)}°C</span>
                        <span class="vital-label">Temperature</span>
                        <span class="vital-unit">Body</span>
                    </div>
                </div>
            </div>
        {/if}
    </div>

    <svelte:fragment slot="footer">
        <div class="footer-content">
            <div class="footer-left">
                {#if restData?.recorded_at}
                    <span class="last-reading">Last snapshot: {new Date(restData.recorded_at).toLocaleTimeString()}</span>
                {/if}
            </div>
            <div class="footer-right">
                {#if needsAttention}
                    <span class="attention-text">Vitals require attention</span>
                {:else}
                    <span class="normal-text">All vitals normal</span>
                {/if}
            </div>
        </div>
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
    }

    .header-right {
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .title {
        font-size: 1.125rem;
        font-weight: 500;
        font-family: "Approach Mono", monospace;
    }

    :global(.alert-badge) {
        background: var(--red-tint) !important;
        color: var(--red-text) !important;
        border: 1px solid var(--red-text) !important;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    .vitals-body {
        padding: 1.5rem;
        min-height: 300px;
    }

    .error-state {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 200px;
    }

    .error-text {
        color: var(--red-text);
        font-size: 0.875rem;
    }

    /* Heart Rate Section */
    .heart-rate-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--edge-soft);
        margin-bottom: 1.5rem;
    }

    .hr-display {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .hr-icon {
        padding: 0.75rem;
        background: var(--green-tint);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
    }

    .hr-icon.elevated {
        background: var(--yellow-tint);
    }

    .hr-icon.critical {
        background: var(--red-tint);
        animation: pulse 1s infinite;
    }

    :global(.heart-icon) {
        animation: heartbeat 1s ease-in-out infinite;
    }

    @keyframes heartbeat {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
    }

    .hr-value-container {
        display: flex;
        align-items: baseline;
        gap: 0.25rem;
    }

    .hr-value {
        font-size: 3rem;
        font-weight: 500;
        font-family: "Approach Mono", monospace;
        line-height: 1;
    }

    .hr-unit {
        font-size: 1rem;
        color: var(--text-muted);
        font-family: "Approach Mono", monospace;
    }

    :global(.status-badge) {
        font-size: 0.65rem !important;
        padding: 0.25rem 0.5rem !important;
    }

    :global(.status-normal) {
        background: var(--green-tint) !important;
        color: var(--green-text) !important;
        border: 1px solid var(--green-text) !important;
    }

    :global(.status-elevated) {
        background: var(--yellow-tint) !important;
        color: var(--yellow-text) !important;
        border: 1px solid var(--yellow-text) !important;
    }

    :global(.status-critical) {
        background: var(--red-tint) !important;
        color: var(--red-text) !important;
        border: 1px solid var(--red-text) !important;
    }

    /* Mini Chart */
    .hr-chart {
        width: 100%;
        max-width: 300px;
        height: 50px;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        border-radius: 8px;
        padding: 0.5rem;
        position: relative;
    }

    .hr-chart svg {
        width: 100%;
        height: 100%;
    }

    .chart-label {
        position: absolute;
        bottom: 2px;
        right: 8px;
        font-size: 0.6rem;
        color: var(--text-muted);
        font-family: "Approach Mono", monospace;
    }

    /* Vitals Grid */
    .vitals-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
    }

    .vital-card {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        border-radius: 8px;
        transition: all 0.2s ease;
    }

    .vital-card:hover {
        border-color: var(--edge);
    }

    .vital-icon {
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }

    .vital-icon.bp {
        background: var(--purple-tint);
        color: var(--purple-text);
    }

    .vital-icon.o2 {
        background: var(--cyan-tint);
        color: var(--cyan-text);
    }

    .vital-icon.o2.low {
        background: var(--yellow-tint);
        color: var(--yellow-text);
    }

    .vital-icon.o2.critical {
        background: var(--red-tint);
        color: var(--red-text);
    }

    .vital-icon.temp {
        background: var(--blue-tint);
        color: var(--blue-text);
    }

    .vital-icon.temp.elevated {
        background: var(--warning-text);
        color: white;
    }

    .vital-info {
        display: flex;
        flex-direction: column;
    }

    .vital-value {
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--text);
        font-family: "Approach Mono", monospace;
        line-height: 1.2;
    }

    .vital-value.warning {
        color: var(--warning-text);
    }

    .vital-value.critical {
        color: var(--red-text);
    }

    .vital-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        font-family: "Approach Mono", monospace;
    }

    .vital-unit {
        font-size: 0.6rem;
        color: var(--text-muted);
        opacity: 0.7;
    }

    /* Footer */
    .footer-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
        font-size: 0.75rem;
        font-family: "Approach Mono", monospace;
    }

    .last-reading {
        color: var(--text-muted);
    }

    .attention-text {
        color: var(--red-text);
    }

    .normal-text {
        color: var(--green-text);
    }

    /* Responsive */
    @media (max-width: 600px) {
        .vitals-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
