<script lang="ts">
    export type LegendEntry = {
        label: string;
        color: string;
        value: number;
    };

    const props = $props<{
        values: LegendEntry[] | null;
        fallbackSeries: Record<string, { t: number; y: number }[]>;
        labels: string[];
        colors: string[];
        yKeys: string[];
    }>();
</script>

<div class="flex flex-wrap items-center gap-4 mb-4 font-approachmono text-sm">
    {#each props.yKeys as key, i}
        <div class="flex items-center gap-2">
            <span class="inline-block w-3 h-3 rounded" style="background:{props.colors[i]}"></span>

            <span class="opacity-80">{props.labels[i]}:</span>

            <span class="font-medium">
                {#if props.values}
                    {props.values[i].value.toFixed(1)}
                {:else if props.fallbackSeries[key]?.length}
                    {props.fallbackSeries[key][props.fallbackSeries[key].length - 1].y.toFixed(1)}
                {:else}
                    —
                {/if}
            </span>
        </div>
    {/each}
</div>
