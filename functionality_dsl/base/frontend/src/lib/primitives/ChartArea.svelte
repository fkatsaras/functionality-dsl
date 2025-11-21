<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { createEventDispatcher } from "svelte";

    import uPlot from "uplot";
    import "uplot/dist/uPlot.min.css";

    const props = $props<{
        series: Record<string, { t: number; y: number }[]>;
        yKeys: string[];
        labels: string[];
        colors: string[];
        xLabel?: string;
        yLabel?: string;
        xMeta?: { type?: string; format?: string; text?: string } | null;
        yMeta?: { type?: string; format?: string; text?: string } | null;
    }>();

    const dispatch = createEventDispatcher();

    // Determine if X axis should be treated as time
    function isTimeAxis(): boolean {
        if (!props.xMeta) return true; // Default to time for backward compatibility

        const { type, format } = props.xMeta;

        // String types with date/time formats
        if (type === "string" && (format === "date" || format === "datetime" || format === "date_time" || format === "time")) {
            return true;
        }

        // Numeric types with datetime format (Unix timestamps)
        if ((type === "number" || type === "integer") && (format === "datetime" || format === "date_time")) {
            return true;
        }

        // Other numeric types are not time-based
        if (type === "number" || type === "integer") {
            return false;
        }

        return true; // Default to time
    }

    let root: HTMLDivElement;
    let plot: uPlot | null = null;
    let ro: ResizeObserver | null = null;

    function buildOrUpdatePlot() {
        if (!root) return;
        if (!props.yKeys.length) return;

       const xKey = Object.keys(props.series)[0];

        const base = props.series[xKey];
        if (!base || !base.length) return;

        // uPlot expects seconds on time scale
        const xs = base.map((p: { t: number; y: number }) => p.t / 1000);

        const ys = props.yKeys.map((k: string) =>
            props.series[k].map((p: { t: number; y: number }) => p.y)
        );

        const data = [xs, ...ys];

        if (!plot) {
            const opts: uPlot.Options = {
                width: root.clientWidth,
                height: 320,

                legend: {
                    show: false,
                    live: false,
                },
            
                cursor: {
                    show: true,
                    points: { show: true },
                    x: true,
                    y: true,
                    focus: { prox: 32 },
                    bind: { idx: true },
                },
            
                scales: {
                    x: { time: isTimeAxis() },
                    y: { auto: true },
                },
            
                series: [
                    {}, // x series
                    ...props.yKeys.map((_, i) => ({
                        label: props.labels[i],
                        stroke: props.colors[i],
                        scale: "y",
                    }))
                ],

                axes: [
                    {
                        label: props.xLabel,
                        font: "12px \"Approach Mono\"",
                        labelFont: "14px \"Approach Mono\"",
                        stroke: getComputedStyle(root).getPropertyValue('--text').trim(),
                        draw: true,
                    },
                    {
                        label: props.yLabel,
                        font: "12px \"Approach Mono\"",
                        labelFont: "14px \"Approach Mono\"",
                        stroke: getComputedStyle(root).getPropertyValue('--text').trim(),
                        draw: true,
                    }
                ],
                
                hooks: {
                    setLegend: [
                        (u: uPlot) => {
                            const idx = u.cursor.idx;
                        
                            if (idx == null || idx < 0) {
                                dispatch("legend", null);
                                return;
                            }
                        
                            dispatch("legend", {
                                x: u.data[0][idx],
                                values: u.series.slice(1).map((s, i) => ({
                                    label: s.label!,
                                    color: s.stroke as string,
                                    value: u.data[i + 1][idx],
                                }))
                            });
                        }
                    ]
                }
            };


            plot = new uPlot(opts, data, root);

            ro = new ResizeObserver(() => {
                if (!plot) return;
                plot.setSize({ width: root.clientWidth, height: 320 });
            });
            ro.observe(root);
        } else {
            plot.setData(data);
        }
    }

    // Rerun whenever props.series / yKeys / labels / colors change
    $effect(buildOrUpdatePlot);

    onDestroy(() => {
        ro?.disconnect();
        ro = null;
        plot?.destroy();
        plot = null;
    });
</script>

<div
    bind:this={root}
    class="canvas w-full h-[320px] border border-[color:var(--edge-light)] rounded"
/>


<style global>
/* Tick text */
.canvas .u-axis .u-values text {
    fill: var(--text) !important;
}

/* Axis title */
.canvas .u-axis .u-title {
    fill: var(--text) !important;
}

/* Grid lines */
.canvas .u-grid {
    stroke: rgba(255,255,255,0.15) !important;
}

/* Cursor lines */
.canvas .u-cursor-x,
.canvas .u-cursor-y {
    stroke: rgba(255,255,255,0.35) !important;
}
</style>