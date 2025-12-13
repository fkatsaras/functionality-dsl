<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import Metric from "$lib/primitives/Metric.svelte";
    import MetricGrid from "$lib/primitives/MetricGrid.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";

    import { subscribe } from "$lib/ws";

    interface MetricConfig {
        key: string;
        label: string;
        trend?: "up" | "down" | null;
    }

    const props = $props<{
        streamPath: string;
        metrics: string[] | MetricConfig[];
        name?: string;
    }>();

    const label = props.name || "Live Metrics";

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

    function normalizeMetrics(): MetricConfig[] {
        return props.metrics.map((m) => {
            if (typeof m === "string") {
                return { key: m, label: m };
            }
            return m;
        });
    }

    function getNestedValue(obj: any, path: string) {
        return path.split(".").reduce((acc, key) => acc?.[key], obj);
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

<Card>
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
            <MetricGrid>
                {#each normalizeMetrics() as metric}
                    {@const value = getNestedValue(data, metric.key)}
                    <Metric
                        value={value ?? "—"}
                        label={metric.label}
                        trend={metric.trend}
                    />
                {/each}
            </MetricGrid>
        {:else if !error}
            <div class="py-8">
                <EmptyState message="Waiting for metrics..." />
            </div>
        {/if}
    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
