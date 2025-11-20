<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import EmptyState from "../primitives/icons/EmptyState.svelte";

    import { subscribe } from "$lib/ws";

    const props = $props<{
        streamPath: string;
        fields: string[];
        label?: string;
        maxMessages?: number;
        name?: string;
    }>();

    // defaults
    const label = props.label ?? "Live";
    const maxMessages = props.maxMessages ?? 50;

    // reactive state
    let connected = $state(false);
    let error = $state<string | null>(null);
    let messages = $state<any[]>([]);

    let unsub: null | (() => void) = null;

    function pick(msg: any) {
        const obj: Record<string, any> = {};
        for (const f of props.fields) obj[f] = msg?.[f];
        return obj;
    }

    function handleStream(msg: any) {
        if (msg?.__meta === "open") { connected = true; return; }
        if (msg?.__meta === "close") { connected = false; return; }

        connected = true;
        messages = [...messages, pick(msg)].slice(-maxMessages);
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
            <div class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded mt-2">
                {error}
            </div>
        {/if}
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="flex-1 flex flex-col gap-2 overflow-y-auto rounded-md p-3 bg-dag-surface h-[500px]">
            {#each messages as msg}
                <div class="px-3 py-2 font-approachmono text-sm text-text border-b border-white/10">
                    {#each props.fields as f}
                        {msg[f]}{#if f !== props.fields[props.fields.length - 1]} · {/if}
                    {/each}
                </div>
            {/each}

            {#if !messages.length && !error}
                <div class="text-center text-text-muted font-approachmono py-20">
                    <EmptyState message="No telemetry data yet..." />
                </div>
            {/if}
        </div>
    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
