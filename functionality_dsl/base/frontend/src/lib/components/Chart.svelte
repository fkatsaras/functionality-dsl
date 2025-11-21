<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import Legend from "$lib/primitives/Legend.svelte";
    import ChartArea from "$lib/primitives/ChartArea.svelte";
    import type { LegendEntry } from "$lib/primitives/Legend.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";


    import { detectKeys, pushRow } from "$lib/utils/chartData";

    const props = $props<{
        name?: string;
        url?: string;
        refreshMs?: number;
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

    let loading = $state(false);
    let error = $state<string | null>(null);

    let hoverLegend: { x: number; values: LegendEntry[] } | null = null;

    // ----------------------------------
    // FETCH REST DATA
    // ----------------------------------
    async function fetchOnce() {
        if (!props.url) return;

        loading = true;
        try {
            const res = await fetch(props.url);
            const payload = await res.json();

            if (!Array.isArray(payload) || payload.length === 0) {
                xKey = null;
                yKeys = [];
                series = {};
                loading = false;
                return;
            }

            // detect first row keys
            const init = detectKeys(payload[0]);
            xKey = init.xKey;
            yKeys = init.yKeys;
            series = init.series;

            // Push all rows
            for (const row of payload) {
                series = pushRow(row, xKey, yKeys, series, props.windowSize, props.xMeta);
            }

        } catch (e: any) {
            error = e.message;
        }
        loading = false;
    }

    // initial + interval refresh
    onMount(() => {
        fetchOnce();
        if (props.refreshMs && props.refreshMs > 0) {
            const id = setInterval(fetchOnce, props.refreshMs);
            onDestroy(() => clearInterval(id));
        }
    });

    const defaultPalette = [
        "#3b82f6",
        "#22c55e",
        "#f97316",
        "#e11d48",
        "#a855f7",
        "#14b8a6"
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

    function handleLegend(e: CustomEvent<{ x: number; values: LegendEntry[] } | null>) {
        hoverLegend = e.detail;
    }

    function allPoints() {
        return yKeys.flatMap(k => series[k] || []);
    }
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="w-full flex justify-between items-center">
            <span class="font-approachmono text-xl">
                {props.name ?? "Chart"}
            </span>
            <RefreshButton loading={loading} onRefresh={fetchOnce} />
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
                <EmptyState message="No data loaded." />
            </div>
        {/if}
    </svelte:fragment>
</Card>
