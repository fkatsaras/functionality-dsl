<script lang="ts">
    import { onMount, onDestroy } from "svelte";

    import Card from "$lib/primitives/Card.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import Input from "$lib/primitives/Input.svelte";
    import Button from "$lib/primitives/Button.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";

    import { subscribe, publish } from "$lib/ws";

    const props = $props<{
        name?: string;
        sinkPath?: string | null;
        wsPath?: string | null;
        label?: string;
        placeholder?: string;
        initial?: string;
        submitLabel?: string;
    }>();

    const label = props.label ?? props.name ?? "InputBox";
    const submitText = props.submitLabel ?? "Send";

    // prefer sinkPath over wsPath
    const endpointPath = props.sinkPath || props.wsPath;

    let value = $state(props.initial ?? "");
    let connected = $state(false);
    let error: string | null = $state(null);
    let unsub: (() => void) | null = null;

    function send() {
        if (!connected || !endpointPath) return;

        try {
            publish(endpointPath, value);
            value = "";
        } catch (err) {
            error = "Failed to send message";
            console.error(err);
        }
    }

    onMount(() => {
        if (!endpointPath) {
            error = "No sinkPath or wsPath provided";
            return;
        }

        // Use shared WebSocket connection - subscribe to handle connection state
        unsub = subscribe(endpointPath, (msg) => {
            if (msg?.__meta === "open") {
                connected = true;
                error = null;
            }
            if (msg?.__meta === "close") {
                connected = false;
            }
            // Ignore other messages - Input component only sends, doesn't receive
        });
    });

    onDestroy(() => {
        unsub?.();
        unsub = null;
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
        <div class="flex gap-3 mt-2">
            <Input
                bind:value
                placeholder={props.placeholder ?? ""}
                class="font-approachmono"
                on:keydown={(e: KeyboardEvent) => e.key === "Enter" && send()}
            />

            <Button on:click={send} disabled={!connected}>
                {#if !connected}
                    <Spinner size={16} />
                {:else}
                    {submitText}
                {/if}
            </Button>
        </div>
    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
        "Liberation Mono", "Courier New", monospace;
    }
</style>
