<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import Legend from "$lib/primitives/Legend.svelte";
    import ChartArea from "$lib/primitives/ChartArea.svelte";
    import type { LegendEntry } from "$lib/primitives/Legend.svelte";
    import EmptyState from "../primitives/icons/EmptyState.svelte";


    import { subscribe as wsSubscribe } from "$lib/ws";
    import { detectKeys, pushRow } from "$lib/utils/chartData";

    const props = $props<{
        name?: string;
        wsUrl: string;
        windowSize?: number;
        xLabel?: string;
        yLabel?: string;
        xMeta?: { type?: string; format?: string; text?: string } | null;
        yMeta?: { type?: string; format?: string; text?: string } | null;
        seriesLabels?: string[] | null;
        seriesColors?: string[] | null;
        // Bind to attribute name (like Chart component's 'values: data')
        values?: string;  // Attribute name containing the value to plot
    }>();

    // CHART DATA
    let xKey: string | null = $state(null);
    let yKeys: string[] = $state([]);
    let series: Record<string, any[]> = $state({});

    let loading = $state(true);
    let error = $state<string | null>(null);
    let connected = $state(false);

    let hoverLegend: { x: number; values: LegendEntry[] } | null = null;
    let unsub: null | (() => void) = null;

    // ----------------------------------
    // WS HANDLER
    // ----------------------------------
    function pushPayload(row: any) {
        // Handle meta events
        if (row?.__meta === "open") {
            connected = true;
            loading = false;
            return;
        }
        if (row?.__meta === "close") {
            connected = false;
            return;
        }

        loading = false;
        connected = true;

        if (!row || typeof row !== "object") return;

        // Initialize on first data packet
        if (!xKey) {
            if (props.values) {
                // Use explicit field name - create single series from that field
                xKey = "__timestamp";  // Auto-generate timestamps for X-axis
                yKeys = [props.values];
                series = { [props.values]: [] };
            } else {
                // Auto-detect all numeric fields
                const init = detectKeys(row);
                xKey = init.xKey;
                yKeys = init.yKeys;
                series = init.series;
            }
        }

        // Add timestamp and push the row
        const timestamp = Date.now();
        const enrichedRow = { ...row, __timestamp: timestamp };
        series = pushRow(enrichedRow, xKey, yKeys, series, props.windowSize, props.xMeta);
    }

    onMount(() => {
        if (!props.wsUrl || props.wsUrl === "None") {
            error = "No WS URL provided";
            loading = false;
            return;
        }

        unsub = wsSubscribe(props.wsUrl, pushPayload);

        onDestroy(() => {
            unsub?.();
        });
    });

    // ----------------------------------
    // Legend / Labels / Colors
    // ----------------------------------
    const defaultPalette = [
        "#3b82f6", "#22c55e", "#f97316",
        "#e11d48", "#a855f7", "#14b8a6"
    ];

    const labels = $derived(
        props.seriesLabels?.length === yKeys.length
            ? props.seriesLabels
            : yKeys.map(k => k.toUpperCase())
    );

    const colors = $derived(
        props.seriesColors?.length === yKeys.length
            ? props.seriesColors
            : yKeys.map((_, i) => defaultPalette[i % defaultPalette.length])
    );

    const allPoints = () => yKeys.flatMap(k => series[k] || []);

    const handleLegend = (e: CustomEvent<{ x: number; values: LegendEntry[] } | null>) =>
        hoverLegend = e.detail;
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="w-full flex justify-between items-center">
            <span class="font-approachmono text-xl">
                {props.name ?? "Live Chart"}
            </span>
            <LiveIndicator connected={!loading} />
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <Legend
            values={hoverLegend?.values ?? null}
            fallbackSeries={series}
            labels={labels}
            colors={colors}
            yKeys={yKeys}
        />

        {#if allPoints().length} 
            <ChartArea
                {series}
                {yKeys}
                {labels}
                {colors}
                xLabel={props.xLabel}
                yLabel={props.yLabel}
                xMeta={props.xMeta}
                yMeta={props.yMeta}
                on:legend={handleLegend}
            />
        {:else}
            <div class="text-center py-20 text-text-muted font-approachmono">
                <EmptyState message="No telemetry data yet..." />
            </div>
        {/if}
    </svelte:fragment>
</Card>
