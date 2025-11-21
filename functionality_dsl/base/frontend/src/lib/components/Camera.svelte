<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";

    import { subscribe as wsSubscribe } from "$lib/ws";
    import Spinner from "../primitives/icons/Spinner.svelte";

    const props = $props<{
        name?: string;
        wsUrl: string;
        label?: string;
    }>();

    const label = props.label ?? props.name ?? "Camera";

    let connected = $state(false);
    let error: string | null = $state(null);

    // Stores the current image URL (blob URL)
    let frameUrl: string | null = $state(null);

    let unsub: null | (() => void) = null;

    /** Clean existing blob URLs */
    function revokeFrame() {
        if (frameUrl) URL.revokeObjectURL(frameUrl);
        frameUrl = null;
    }

    /** Handle incoming binary frames */
    function handleFrame(data: any) {
        // meta events
        if (data?.__meta === "open") {
            connected = true;
            return;
        }
        if (data?.__meta === "close") {
            connected = false;
            return;
        }

        // Some WS servers wrap binary data ─ detect ArrayBuffer or Blob
        if (data instanceof Blob) {
            revokeFrame();
            frameUrl = URL.createObjectURL(data);
            connected = true;
        } else if (data instanceof ArrayBuffer) {
            revokeFrame();
            frameUrl = URL.createObjectURL(new Blob([data]));
            connected = true;
        } else {
            // ignore unknown packets
        }
    }

    onMount(() => {
        if (!props.wsUrl || props.wsUrl === "None") {
            error = "No WebSocket URL provided";
            return;
        }

        unsub = wsSubscribe(props.wsUrl, handleFrame);

        onDestroy(() => {
            unsub?.();
            revokeFrame();
        });
    });
</script>


<Card>
    <svelte:fragment slot="header">
        <div class="w-full flex items-center justify-between">
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
        <div class="w-full flex justify-center items-center bg-[color:var(--surface)] p-4 rounded-xl min-h-[400px]">
            {#if frameUrl}
                <img
                    src={frameUrl}
                    alt="Camera Feed"
                    class="rounded-xl max-h-[600px] object-contain shadow-lg"
                />
            {:else}
                <div class="text-text-muted font-approachmono py-20 opacity-60">
                    <Spinner size={20} />
                </div>
            {/if}
        </div>
    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco,
            Consolas, "Liberation Mono", "Courier New", monospace;
    }
</style>
