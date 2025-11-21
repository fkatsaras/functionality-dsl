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
    }>();

    // CHART DATA
    let xKey: string | null = $state(null);
    let yKeys: string[] = $state([]);
    let series: Record<string, any[]> = $state({});

    let loading = $state(true);
    let error = $state<string | null>(null);

    let hoverLegend: { x: number; values: LegendEntry[] } | null = null;
    let unsub: null | (() => void) = null;

    // ----------------------------------
    // WS HANDLER
    // ----------------------------------
    function pushPayload(row: any) {
        loading = false;

        if (!row || typeof row !== "object") {
            console.warn('[LiveChart] Invalid row:', row);
            return;
        }

        // detect keys on first packet
        if (!xKey) {
            const init = detectKeys(row);
            xKey = init.xKey;
            yKeys = init.yKeys;
            series = init.series;
            console.log('[LiveChart] Detected keys:', { xKey, yKeys });
            console.log('[LiveChart] xMeta:', props.xMeta);
        }

        // push streaming row
        const before = Object.keys(series).length;
        series = pushRow(row, xKey, yKeys, series, props.windowSize, props.xMeta);
        const after = Object.keys(series).length;

        if (before === 0 && after > 0) {
            console.log('[LiveChart] First data point added:', series);
        }
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
