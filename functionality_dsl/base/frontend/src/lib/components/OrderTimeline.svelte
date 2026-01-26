<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { Package, Truck, CheckCircle, Clock, MapPin } from "lucide-svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import Badge from "$lib/primitives/Badge.svelte";

    import { subscribe as wsSubscribe } from "$lib/ws";

    const props = $props<{
        wsUrl: string;
        wsParams?: string[];  // Parameter names required for WebSocket connection
        title?: string;
    }>();

    interface OrderData {
        order_id: string;
        status: string;
        tracking?: string | null;
        is_shipped?: boolean;
        is_delivered?: boolean;
        timestamp?: number;
    }

    let data = $state<OrderData | null>(null);
    let connected = $state(false);
    let error = $state<string | null>(null);
    let unsub: (() => void) | null = null;

    // WebSocket params state
    let wsParamValues = $state<Record<string, string>>({});
    let wsParamsProvided = $state(false);

    // Check if we need params before connecting
    const needsWsParams = $derived(
        props.wsParams && props.wsParams.length > 0 && !wsParamsProvided
    );

    // Status progression stages
    const stages = [
        { key: "pending", label: "Order Placed", icon: Clock },
        { key: "processing", label: "Processing", icon: Package },
        { key: "shipped", label: "Shipped", icon: Truck },
        { key: "delivered", label: "Delivered", icon: CheckCircle },
    ];

    function getStageIndex(status: string): number {
        const normalized = status?.toLowerCase().replace(/[_\s-]/g, "") || "pending";
        if (normalized.includes("deliver")) return 3;
        if (normalized.includes("ship") || normalized.includes("transit")) return 2;
        if (normalized.includes("process") || normalized.includes("confirm")) return 1;
        return 0;
    }

    const currentStageIndex = $derived(data ? getStageIndex(data.status) : 0);

    function handleMessage(msg: any) {
        if (msg?.__meta === "open") {
            connected = true;
            return;
        }
        if (msg?.__meta === "close") {
            connected = false;
            return;
        }
        connected = true;
        data = msg;
    }

    function buildWsUrl(): string {
        let url = props.wsUrl;
        if (props.wsParams && props.wsParams.length > 0) {
            const params = new URLSearchParams();
            for (const param of props.wsParams) {
                if (wsParamValues[param]) {
                    params.append(param, wsParamValues[param]);
                }
            }
            const queryString = params.toString();
            if (queryString) {
                url = url.includes('?') ? `${url}&${queryString}` : `${url}?${queryString}`;
            }
        }
        return url;
    }

    function connectWebSocket() {
        if (!props.wsUrl || props.wsUrl === "None") {
            error = "No WebSocket URL provided";
            return;
        }
        const url = buildWsUrl();
        unsub = wsSubscribe(url, handleMessage);
    }

    function submitWsParams() {
        // Validate all params are provided
        if (props.wsParams) {
            for (const param of props.wsParams) {
                if (!wsParamValues[param] || wsParamValues[param].trim() === "") {
                    error = `Parameter "${param}" is required`;
                    return;
                }
            }
        }
        wsParamsProvided = true;
        error = null;
        connectWebSocket();
    }

    function formatFieldName(field: string): string {
        return field
            .replace(/_/g, " ")
            .replace(/([A-Z])/g, " $1")
            .trim()
            .split(" ")
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(" ");
    }

    onMount(() => {
        // Only auto-connect if no params are needed
        if (!props.wsParams || props.wsParams.length === 0) {
            connectWebSocket();
        }
    });

    onDestroy(() => {
        unsub?.();
    });

    function formatTimestamp(ts?: number): string {
        if (!ts) return "";
        const date = new Date(ts);
        return date.toLocaleString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }
</script>

<Card fullWidth>
    <svelte:fragment slot="header">
        <div class="header">
            <div class="header-left">
                <Package size={20} />
                <span class="title">{props.title || "Order Timeline"}</span>
            </div>
            <LiveIndicator {connected} />
        </div>
    </svelte:fragment>

    <div class="timeline-body">
        {#if needsWsParams}
            <!-- WebSocket params form -->
            <div class="params-form">
                <p class="params-hint">Enter parameters to track order:</p>
                {#if error}
                    <div class="error-text">{error}</div>
                {/if}
                {#each props.wsParams || [] as param}
                    <div class="param-row">
                        <label class="param-label" for={param}>{formatFieldName(param)}</label>
                        <input
                            type="text"
                            id={param}
                            class="param-input"
                            placeholder={param}
                            bind:value={wsParamValues[param]}
                            onkeydown={(e) => e.key === 'Enter' && submitWsParams()}
                        />
                    </div>
                {/each}
                <button class="connect-btn" onclick={submitWsParams}>
                    Track Order
                </button>
            </div>
        {:else if error}
            <div class="error-state">
                <span class="error-text">{error}</span>
            </div>
        {:else if !data}
            <div class="loading-state">
                <div class="loader"></div>
                <span class="loading-text">Waiting for order updates...</span>
            </div>
        {:else}
            <!-- Order ID Header -->
            <div class="order-header">
                <div class="order-id-section">
                    <span class="order-label">Order ID</span>
                    <span class="order-id">{data.order_id}</span>
                </div>
                {#if data.tracking}
                    <div class="tracking-section">
                        <MapPin size={14} />
                        <span class="tracking-number">{data.tracking}</span>
                    </div>
                {/if}
            </div>

            <!-- Timeline -->
            <div class="timeline">
                {#each stages as stage, i}
                    {@const isCompleted = i <= currentStageIndex}
                    {@const isCurrent = i === currentStageIndex}
                    {@const Icon = stage.icon}
                    <div class="timeline-stage" class:completed={isCompleted} class:current={isCurrent}>
                        <div class="stage-icon" class:completed={isCompleted} class:current={isCurrent}>
                            <Icon size={20} />
                        </div>
                        <div class="stage-content">
                            <span class="stage-label" class:completed={isCompleted}>{stage.label}</span>
                            {#if isCurrent && data.timestamp}
                                <span class="stage-time">{formatTimestamp(data.timestamp)}</span>
                            {/if}
                        </div>
                        {#if i < stages.length - 1}
                            <div class="connector" class:completed={i < currentStageIndex}></div>
                        {/if}
                    </div>
                {/each}
            </div>

            <!-- Status Badge -->
            <div class="status-section">
                <Badge class={currentStageIndex === 3 ? "status-delivered" : currentStageIndex >= 2 ? "status-shipped" : "status-processing"}>
                    {data.status.toUpperCase()}
                </Badge>
            </div>
        {/if}
    </div>

    <svelte:fragment slot="footer">
        {#if data}
            <div class="footer-content">
                {#if currentStageIndex === 3}
                    <span class="status-complete">Order delivered successfully</span>
                {:else if currentStageIndex === 2}
                    <span class="status-shipping">Package is on its way</span>
                {:else}
                    <span class="status-pending">Order is being prepared</span>
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
    }

    .title {
        font-size: 1.125rem;
        font-weight: 500;
        font-family: "Approach Mono", monospace;
    }

    .timeline-body {
        padding: 1.5rem;
        min-height: 280px;
    }

    .loading-state, .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        gap: 1rem;
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

    .loading-text {
        color: var(--text-muted);
        font-size: 0.875rem;
        font-family: "Approach Mono", monospace;
    }

    .error-text {
        color: var(--red-text);
        font-size: 0.875rem;
    }

    /* Order Header */
    .order-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--edge-soft);
    }

    .order-id-section {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .order-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .order-id {
        font-size: 1.25rem;
        font-weight: 500;
        color: var(--text);
        font-family: "Approach Mono", monospace;
    }

    .tracking-section {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.75rem;
        background: var(--blue-tint);
        border: 1px solid var(--blue-text);
        border-radius: 6px;
        color: var(--blue-text);
        font-size: 0.75rem;
        font-family: "Approach Mono", monospace;
    }

    .tracking-number {
        letter-spacing: 0.02em;
    }

    /* Timeline */
    .timeline {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        position: relative;
        padding: 0 0.5rem;
        margin-bottom: 2rem;
    }

    .timeline-stage {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        flex: 1;
        z-index: 1;
    }

    .stage-icon {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--surface);
        border: 2px solid var(--edge);
        color: var(--text-muted);
        transition: all 0.3s ease;
    }

    .stage-icon.completed {
        background: var(--green-tint);
        border-color: var(--green-text);
        color: var(--green-text);
    }

    .stage-icon.current {
        background: var(--accent);
        border-color: var(--accent);
        color: white;
        box-shadow: 0 0 0 4px rgba(124, 131, 255, 0.2);
    }

    .stage-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-top: 0.75rem;
        text-align: center;
    }

    .stage-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-family: "Approach Mono", monospace;
        transition: color 0.3s ease;
    }

    .stage-label.completed {
        color: var(--text);
        font-weight: 500;
    }

    .stage-time {
        font-size: 0.65rem;
        color: var(--accent);
        margin-top: 0.25rem;
        font-family: "Approach Mono", monospace;
    }

    /* Connector line between stages */
    .connector {
        position: absolute;
        top: 24px;
        left: calc(50% + 28px);
        width: calc(100% - 56px);
        height: 2px;
        background: var(--edge);
        z-index: 0;
    }

    .connector.completed {
        background: var(--green-text);
    }

    /* Status Section */
    .status-section {
        display: flex;
        justify-content: center;
        padding-top: 1rem;
        border-top: 1px solid var(--edge-soft);
    }

    :global(.status-delivered) {
        background: var(--green-tint) !important;
        color: var(--green-text) !important;
        border: 1px solid var(--green-text) !important;
    }

    :global(.status-shipped) {
        background: var(--blue-tint) !important;
        color: var(--blue-text) !important;
        border: 1px solid var(--blue-text) !important;
    }

    :global(.status-processing) {
        background: var(--yellow-tint) !important;
        color: var(--yellow-text) !important;
        border: 1px solid var(--yellow-text) !important;
    }

    /* Footer */
    .footer-content {
        width: 100%;
        text-align: center;
        font-size: 0.875rem;
        font-family: "Approach Mono", monospace;
    }

    .status-complete {
        color: var(--green-text);
    }

    .status-shipping {
        color: var(--blue-text);
    }

    .status-pending {
        color: var(--yellow-text);
    }

    /* WebSocket params form styles */
    .params-form {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: 1rem;
    }

    .params-hint {
        font-size: 0.875rem;
        color: var(--text-muted);
        margin: 0;
        font-family: "Approach Mono", monospace;
    }

    .param-row {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .param-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .param-input {
        padding: 0.5rem;
        border: 1px solid var(--edge);
        border-radius: 4px;
        background: var(--surface);
        color: var(--text);
        font-size: 0.875rem;
        font-family: "Approach Mono", monospace;
    }

    .param-input:focus {
        outline: none;
        border-color: var(--accent);
    }

    .connect-btn {
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
        background: var(--accent);
        color: white;
        font-size: 0.875rem;
        font-weight: 500;
        font-family: "Approach Mono", monospace;
        cursor: pointer;
        transition: opacity 0.15s;
        margin-top: 0.5rem;
    }

    .connect-btn:hover {
        opacity: 0.9;
    }
</style>
