<script lang="ts">
    import { preventDefault } from "svelte/legacy";
    import { onMount, onDestroy } from "svelte";

    import Card from "$lib/primitives/Card.svelte";
    import Input from "$lib/primitives/Input.svelte";
    import Button from "$lib/primitives/Button.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";

    import CheckIcon from "$lib/primitives/icons/CheckIcon.svelte";
    import ErrorIcon from "$lib/primitives/icons/ErrorIcon.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";

    import { subscribe, publish } from "$lib/ws";

    const {
        name = "PublishForm",
        wsPath = null as string | null,
        fields = [] as string[],
        submitLabel = "Send",
        label = "PublishForm"
    } = $props();

    // Build model from fields
    let model: Record<string, any> = {};
    for (const f of fields) model[f] = "";

    // Reactive state
    let connected = $state(false);
    let error = $state<string | null>(null);
    let ok = $state<string | null>(null);
    let busy = $state(false);
    let unsub: (() => void) | null = null;

    function send() {
        if (!connected || !wsPath) {
            error = "Not connected";
            return;
        }

        busy = true;
        error = ok = null;

        try {
            // Parse JSON fields: detect strings that look like JSON and parse them
            const payload = structuredClone(model);
            for (const [key, value] of Object.entries(payload)) {
                if (typeof value === 'string' && value.trim()) {
                    const trimmed = value.trim();
                    // Check if it looks like JSON (starts with [ or {)
                    if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
                        try {
                            payload[key] = JSON.parse(trimmed);
                        } catch (e) {
                            // If parsing fails, keep as string
                        }
                    }
                    // Try to parse as number
                    else if (!isNaN(Number(trimmed)) && trimmed !== '') {
                        payload[key] = Number(trimmed);
                    }
                }
            }

            publish(wsPath, payload);
            ok = "Sent!";
            setTimeout(() => (ok = null), 2500);
        } catch (err: any) {
            error = err?.message ?? "Failed to send";
            console.error(err);
        } finally {
            busy = false;
        }
    }

    onMount(() => {
        if (!wsPath) {
            error = "No wsPath provided";
            return;
        }

        // Subscribe to handle connection state
        unsub = subscribe(wsPath, (msg) => {
            if (msg?.__meta === "open") {
                connected = true;
                error = null;
            }
            if (msg?.__meta === "close") {
                connected = false;
            }
            // Ignore other messages - PublishForm only sends
        });
    });

    onDestroy(() => {
        unsub?.();
        unsub = null;
    });
</script>

<!-- Card wrapper -->
<Card>
    <svelte:fragment slot="header">
        <div class="w-full flex items-center justify-between">
            <span class="font-approachmono text-xl">{label}</span>
            <LiveIndicator {connected} />
        </div>

        {#if ok}
            <CheckIcon class="text-[var(--green-text)]" size={20} />
        {/if}

        {#if error && !ok}
            <ErrorIcon class="text-[var(--edge-light)]" size={20} />
        {/if}
    </svelte:fragment>

    <svelte:fragment slot="children">

        <form class="space-y-4 max-w-[500px]" onsubmit={preventDefault(send)}>

            {#each fields as field}
                <label class="flex flex-col gap-1.5">
                    <span class="text-sm font-mono text-text-muted font-medium tracking-wide">{field}</span>

                    <Input
                        bind:value={model[field]}
                        placeholder={field}
                    />
                </label>
            {/each}

            <div class="pt-2">
                <Button type="submit" disabled={busy || !connected}>
                    {#if busy}
                        <Spinner size={16} />
                    {:else if !connected}
                        <Spinner size={16} />
                    {:else}
                        {submitLabel}
                    {/if}
                </Button>
            </div>

            {#if error}
                <Badge class="text-[var(--edge-light)] mt-2">{error}</Badge>
            {/if}
        </form>

    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
        "Liberation Mono", "Courier New", monospace;
    }
</style>
