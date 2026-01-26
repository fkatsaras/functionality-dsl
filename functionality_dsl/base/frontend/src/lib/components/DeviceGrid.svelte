<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { Lightbulb, Power, Sun, Moon, Zap, AlertCircle } from "lucide-svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import Badge from "$lib/primitives/Badge.svelte";

    import { subscribe as wsSubscribe } from "$lib/ws";

    const props = $props<{
        wsUrl: string;
        commandWsUrl?: string;
        title?: string;
        deviceType?: "streetlight" | "bulb" | "switch";
    }>();

    interface DeviceStatus {
        streetId?: string;
        device_id?: string;
        id?: string;
        brightness: number;
        isOn: boolean;
        timestamp: number;
    }

    interface AlertData {
        level: string;
        message: string;
        timestamp: number;
    }

    let devices = $state<Map<string, DeviceStatus>>(new Map());
    let alerts = $state<AlertData[]>([]);
    let connected = $state(false);
    let error = $state<string | null>(null);
    let unsub: (() => void) | null = null;
    let commandWs: WebSocket | null = null;

    function getDeviceId(msg: any): string {
        return msg.streetId || msg.device_id || msg.id || `device-${devices.size}`;
    }

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

        // Handle alert messages
        if (msg.level && msg.message) {
            alerts = [msg, ...alerts.slice(0, 4)];
            return;
        }

        // Handle device status
        const id = getDeviceId(msg);
        const newDevices = new Map(devices);
        newDevices.set(id, {
            streetId: id,
            brightness: msg.brightness ?? 0,
            isOn: msg.isOn ?? (msg.brightness > 0),
            timestamp: msg.timestamp ?? Date.now(),
        });
        devices = newDevices;
    }

    function sendCommand(deviceId: string, action: string, brightness?: number) {
        if (!props.commandWsUrl) return;

        // Create or reuse WebSocket for commands
        if (!commandWs || commandWs.readyState !== WebSocket.OPEN) {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsHost = window.location.host;
            commandWs = new WebSocket(`${wsProtocol}//${wsHost}${props.commandWsUrl}`);
        }

        const command = {
            action,
            brightness: brightness ?? (action === "on" ? 100 : 0),
            duration: 0,
        };

        if (commandWs.readyState === WebSocket.OPEN) {
            commandWs.send(JSON.stringify(command));
        } else {
            commandWs.onopen = () => {
                commandWs?.send(JSON.stringify(command));
            };
        }
    }

    onMount(() => {
        if (!props.wsUrl || props.wsUrl === "None") {
            error = "No WebSocket URL provided";
            return;
        }
        unsub = wsSubscribe(props.wsUrl, handleMessage);
    });

    onDestroy(() => {
        unsub?.();
        commandWs?.close();
    });

    // Computed
    const deviceList = $derived(Array.from(devices.values()));
    const onlineCount = $derived(deviceList.filter(d => d.isOn).length);
    const totalCount = $derived(deviceList.length);
    const avgBrightness = $derived(
        totalCount > 0
            ? Math.round(deviceList.reduce((sum, d) => sum + d.brightness, 0) / totalCount)
            : 0
    );

    function getBrightnessColor(brightness: number): string {
        if (brightness === 0) return "var(--text-muted)";
        if (brightness < 30) return "var(--yellow-text)";
        if (brightness < 70) return "var(--warning-text)";
        return "var(--green-text)";
    }

    function getAlertColor(level: string): string {
        switch (level?.toLowerCase()) {
            case "critical":
            case "error":
                return "var(--red-text)";
            case "warning":
                return "var(--warning-text)";
            default:
                return "var(--blue-text)";
        }
    }
</script>

<Card fullWidth>
    <svelte:fragment slot="header">
        <div class="header">
            <div class="header-left">
                <Lightbulb size={20} />
                <span class="title">{props.title || "Device Grid"}</span>
            </div>
            <div class="header-right">
                <div class="summary-stats">
                    <span class="stat">
                        <Power size={14} />
                        {onlineCount}/{totalCount}
                    </span>
                    <span class="stat">
                        <Sun size={14} />
                        {avgBrightness}%
                    </span>
                </div>
                <LiveIndicator {connected} />
            </div>
        </div>
    </svelte:fragment>

    <div class="device-body">
        {#if error}
            <div class="error-state">
                <span class="error-text">{error}</span>
            </div>
        {:else if deviceList.length === 0}
            <div class="empty-state">
                <Lightbulb size={48} class="empty-icon" />
                <span class="empty-text">Waiting for device status...</span>
                <span class="empty-subtext">Devices will appear when they report their status</span>
            </div>
        {:else}
            <!-- Alerts Section -->
            {#if alerts.length > 0}
                <div class="alerts-section">
                    {#each alerts.slice(0, 3) as alert}
                        <div class="alert-item" style="border-left-color: {getAlertColor(alert.level)}">
                            <AlertCircle size={14} style="color: {getAlertColor(alert.level)}" />
                            <span class="alert-message">{alert.message}</span>
                            <Badge class="alert-level" style="color: {getAlertColor(alert.level)}">
                                {alert.level}
                            </Badge>
                        </div>
                    {/each}
                </div>
            {/if}

            <!-- Device Grid -->
            <div class="devices-grid">
                {#each deviceList as device}
                    {@const brightnessColor = getBrightnessColor(device.brightness)}
                    <div class="device-card" class:off={!device.isOn}>
                        <!-- Device Visual -->
                        <div class="device-visual">
                            <div class="bulb-container" class:on={device.isOn}>
                                <Lightbulb
                                    size={32}
                                    fill={device.isOn ? brightnessColor : "none"}
                                    color={device.isOn ? brightnessColor : "var(--text-muted)"}
                                />
                                {#if device.isOn}
                                    <div class="glow" style="background: {brightnessColor}"></div>
                                {/if}
                            </div>
                        </div>

                        <!-- Device Info -->
                        <div class="device-info">
                            <span class="device-id">{device.streetId}</span>
                            <div class="device-status">
                                <Badge class={device.isOn ? "status-on" : "status-off"}>
                                    {device.isOn ? "ON" : "OFF"}
                                </Badge>
                            </div>
                        </div>

                        <!-- Brightness Bar -->
                        <div class="brightness-section">
                            <div class="brightness-bar">
                                <div
                                    class="brightness-fill"
                                    style="width: {device.brightness}%; background: {brightnessColor}"
                                ></div>
                            </div>
                            <span class="brightness-value">{device.brightness}%</span>
                        </div>

                        <!-- Control Buttons -->
                        {#if props.commandWsUrl}
                            <div class="device-controls">
                                <button
                                    class="control-btn on"
                                    onclick={() => sendCommand(device.streetId || '', 'on', 100)}
                                    disabled={device.isOn && device.brightness === 100}
                                >
                                    <Sun size={14} />
                                </button>
                                <button
                                    class="control-btn dim"
                                    onclick={() => sendCommand(device.streetId || '', 'dim', 50)}
                                >
                                    <Moon size={14} />
                                </button>
                                <button
                                    class="control-btn off"
                                    onclick={() => sendCommand(device.streetId || '', 'off', 0)}
                                    disabled={!device.isOn}
                                >
                                    <Power size={14} />
                                </button>
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}
    </div>

    <svelte:fragment slot="footer">
        <div class="footer-content">
            <div class="footer-left">
                <Zap size={14} />
                <span>{totalCount} devices connected</span>
            </div>
            <div class="footer-right">
                {#if onlineCount === totalCount && totalCount > 0}
                    <span class="all-on">All devices online</span>
                {:else if onlineCount === 0 && totalCount > 0}
                    <span class="all-off">All devices offline</span>
                {:else}
                    <span class="mixed">{onlineCount} active, {totalCount - onlineCount} standby</span>
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
        gap: 1rem;
    }

    .title {
        font-size: 1.125rem;
        font-weight: 500;
        font-family: "Approach Mono", monospace;
    }

    .summary-stats {
        display: flex;
        gap: 0.75rem;
    }

    .stat {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.75rem;
        color: var(--text-muted);
        font-family: "Approach Mono", monospace;
    }

    .device-body {
        padding: 1.5rem;
        min-height: 280px;
    }

    .error-state, .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 200px;
        gap: 0.75rem;
    }

    .error-text {
        color: var(--red-text);
        font-size: 0.875rem;
    }

    :global(.empty-icon) {
        color: var(--text-muted);
        opacity: 0.5;
    }

    .empty-text {
        color: var(--text-muted);
        font-size: 0.875rem;
        font-family: "Approach Mono", monospace;
    }

    .empty-subtext {
        color: var(--text-muted);
        font-size: 0.75rem;
        opacity: 0.7;
    }

    /* Alerts */
    .alerts-section {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--edge-soft);
    }

    .alert-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        border-left: 3px solid;
        border-radius: 4px;
        font-size: 0.75rem;
    }

    .alert-message {
        flex: 1;
        color: var(--text);
        font-family: "Approach Mono", monospace;
    }

    :global(.alert-level) {
        font-size: 0.6rem !important;
        padding: 0.125rem 0.375rem !important;
    }

    /* Device Grid */
    .devices-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 1rem;
    }

    .device-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1rem;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        border-radius: 10px;
        transition: all 0.2s ease;
    }

    .device-card:hover {
        border-color: var(--edge);
        transform: translateY(-2px);
    }

    .device-card.off {
        opacity: 0.7;
    }

    /* Device Visual */
    .device-visual {
        margin-bottom: 0.75rem;
    }

    .bulb-container {
        position: relative;
        padding: 0.75rem;
        border-radius: 50%;
        background: var(--card);
        border: 2px solid var(--edge-soft);
        transition: all 0.3s ease;
    }

    .bulb-container.on {
        border-color: var(--yellow-text);
    }

    .glow {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 60px;
        height: 60px;
        border-radius: 50%;
        opacity: 0.2;
        filter: blur(10px);
        pointer-events: none;
    }

    /* Device Info */
    .device-info {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.375rem;
        margin-bottom: 0.75rem;
    }

    .device-id {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text);
        font-family: "Approach Mono", monospace;
    }

    :global(.status-on) {
        background: var(--green-tint) !important;
        color: var(--green-text) !important;
        border: 1px solid var(--green-text) !important;
        font-size: 0.6rem !important;
    }

    :global(.status-off) {
        background: var(--surface) !important;
        color: var(--text-muted) !important;
        border: 1px solid var(--edge) !important;
        font-size: 0.6rem !important;
    }

    /* Brightness Bar */
    .brightness-section {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }

    .brightness-bar {
        flex: 1;
        height: 6px;
        background: var(--edge-soft);
        border-radius: 3px;
        overflow: hidden;
    }

    .brightness-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }

    .brightness-value {
        font-size: 0.65rem;
        color: var(--text-muted);
        font-family: "Approach Mono", monospace;
        min-width: 28px;
        text-align: right;
    }

    /* Controls */
    .device-controls {
        display: flex;
        gap: 0.375rem;
    }

    .control-btn {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        border: 1px solid var(--edge);
        background: var(--card);
        color: var(--text-muted);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
    }

    .control-btn:hover:not(:disabled) {
        border-color: var(--edge-light);
    }

    .control-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    .control-btn.on:hover:not(:disabled) {
        background: var(--yellow-tint);
        border-color: var(--yellow-text);
        color: var(--yellow-text);
    }

    .control-btn.dim:hover:not(:disabled) {
        background: var(--blue-tint);
        border-color: var(--blue-text);
        color: var(--blue-text);
    }

    .control-btn.off:hover:not(:disabled) {
        background: var(--red-tint);
        border-color: var(--red-text);
        color: var(--red-text);
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

    .footer-left {
        display: flex;
        align-items: center;
        gap: 0.375rem;
        color: var(--text-muted);
    }

    .all-on {
        color: var(--green-text);
    }

    .all-off {
        color: var(--text-muted);
    }

    .mixed {
        color: var(--yellow-text);
    }
</style>
