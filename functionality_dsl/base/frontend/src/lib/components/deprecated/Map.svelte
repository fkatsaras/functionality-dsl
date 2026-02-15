<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import MapPin from "$lib/primitives/MapPin.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";

    import { subscribe } from "$lib/ws";

    const props = $props<{
        streamPath: string;
        warehouseLat: number;
        warehouseLon: number;
        deliveriesKey?: string;
        driversKey?: string;
        name?: string;
        width?: number;
        height?: number;
    }>();

    const label = props.name || "Map";
    const mapWidth = props.width || 800;
    const mapHeight = props.height || 600;

    // Map bounds (adjust these to match your data's lat/lon range)
    const LAT_MIN = props.warehouseLat - 0.05;
    const LAT_MAX = props.warehouseLat + 0.05;
    const LON_MIN = props.warehouseLon - 0.05;
    const LON_MAX = props.warehouseLon + 0.05;

    let connected = $state(false);
    let error = $state<string | null>(null);
    let data = $state<Record<string, any>>({});

    let unsub: null | (() => void) = null;

    function handleStream(msg: any) {
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

    function latLonToXY(lat: number, lon: number): { x: number; y: number } {
        // Normalize to 0-1 range
        const xNorm = (lon - LON_MIN) / (LON_MAX - LON_MIN);
        const yNorm = 1 - (lat - LAT_MIN) / (LAT_MAX - LAT_MIN); // Invert Y (map coordinates)

        return {
            x: xNorm * mapWidth,
            y: yNorm * mapHeight,
        };
    }

    function getDeliveries(): any[] {
        if (!props.deliveriesKey) return [];
        const deliveries = data[props.deliveriesKey];
        return Array.isArray(deliveries) ? deliveries : [];
    }

    function getDrivers(): any[] {
        if (!props.driversKey) return [];
        const drivers = data[props.driversKey];
        return Array.isArray(drivers) ? drivers : [];
    }

    function getWarehousePos() {
        return latLonToXY(props.warehouseLat, props.warehouseLon);
    }

    function getStatusColor(status: string): string {
        const colors: Record<string, string> = {
            pending: "#eab308",       // yellow
            assigned: "#3b82f6",      // blue
            picked_up: "#a855f7",     // purple
            in_transit: "#6366f1",    // indigo
            delivered: "#4ade80",     // green
            cancelled: "#f87171",     // red
        };
        return colors[status] || "#8b949e";
    }

    onMount(() => {
        if (!props.streamPath) {
            error = "No streamPath provided";
            return;
        }

        unsub = subscribe(props.streamPath, handleStream);

        onDestroy(() => {
            unsub?.();
            unsub = null;
        });
    });
</script>

<Card fullWidth={true}>
    <svelte:fragment slot="header">
        <div class="w-full flex justify-between items-center">
            <span class="font-approachmono text-xl">{label}</span>
            <LiveIndicator connected={connected} />
        </div>

        {#if error}
            <div class="text-xs text-[var(--red-text)] font-approachmono bg-[var(--red-tint)] px-2 py-1 rounded mt-2">
                {error}
            </div>
        {/if}
    </svelte:fragment>

    <svelte:fragment slot="children">
        {#if Object.keys(data).length > 0}
            <div class="map-container" style={`max-width: ${mapWidth}px; width: 100%; height: ${mapHeight}px;`}>
                <!-- Grid background -->
                <svg class="map-grid" width="100%" height="100%" viewBox={`0 0 ${mapWidth} ${mapHeight}`} preserveAspectRatio="xMidYMid meet">
                    <!-- Vertical grid lines -->
                    {#each Array(10) as _, i}
                        <line
                            x1={i * mapWidth / 10}
                            y1={0}
                            x2={i * mapWidth / 10}
                            y2={mapHeight}
                            stroke="var(--edge-soft)"
                            stroke-width="1"
                        />
                    {/each}
                    <!-- Horizontal grid lines -->
                    {#each Array(10) as _, i}
                        <line
                            x1={0}
                            y1={i * mapHeight / 10}
                            x2={mapWidth}
                            y2={i * mapHeight / 10}
                            stroke="var(--edge-soft)"
                            stroke-width="1"
                        />
                    {/each}
                </svg>

                <!-- Warehouse pin (fixed location) -->
                {#if true}
                    {@const warehousePos = getWarehousePos()}
                    <MapPin
                        x={warehousePos.x}
                        y={warehousePos.y}
                        color="#16a34a"
                        size={32}
                        label="Warehouse"
                    />
                {/if}

                <!-- Delivery pins -->
                {#each getDeliveries() as delivery}
                    {@const pickupPos = latLonToXY(delivery.pickupLat, delivery.pickupLat)}
                    {@const deliveryPos = latLonToXY(delivery.deliveryLat, delivery.deliveryLon)}

                    <!-- Pickup location -->
                    <MapPin
                        x={pickupPos.x}
                        y={pickupPos.y}
                        color={getStatusColor(delivery.status)}
                        size={20}
                        label={`${delivery.orderId} (pickup)`}
                    />

                    <!-- Delivery destination -->
                    <MapPin
                        x={deliveryPos.x}
                        y={deliveryPos.y}
                        color={getStatusColor(delivery.status)}
                        size={18}
                        label={`${delivery.orderId} (dest)`}
                    />
                {/each}

                <!-- Driver pins -->
                {#each getDrivers() as driver}
                    {@const driverPos = latLonToXY(driver.lat, driver.lon)}
                    <MapPin
                        x={driverPos.x}
                        y={driverPos.y}
                        color="#7c83ff"
                        size={24}
                        label={driver.driverName}
                    />
                {/each}
            </div>
        {:else if !error}
            <div class="py-8">
                <EmptyState message="Waiting for location data..." />
            </div>
        {/if}
    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }

    .map-container {
        position: relative;
        background: var(--surface);
        border: 2px solid var(--edge);
        border-radius: 8px;
        overflow: hidden;
    }

    .map-grid {
        position: absolute;
        top: 0;
        left: 0;
        pointer-events: none;
    }
</style>
