<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";

    import { spring } from "svelte/motion";

    const props = $props<{
        url: string;
        label?: string;
        field?: string;
        name?: string;
        refreshMs?: number;
    }>();

    let state = $state(false);
    let loading = $state(false);
    let error = $state<string | null>(null);
    let interval: ReturnType<typeof setInterval> | null = null;
    let authToken = $state<string | null>(null);

    authStore.subscribe((authState) => {
        authToken = authState.token;
    });

    // 0 = off, 1 = on
    const position = spring(0, { stiffness: 0.2, damping: 0.4 });

    $effect(() => {
        position.set(state ? 1 : 0);
    });

    async function fetchState() {
        if (!props.url) return;

        try {
            const headers: Record<string, string> = {};
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            const res = await fetch(props.url, { headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            const data = await res.json();
            state = !!data[props.field || "state"];
            error = null;
        } catch (e: any) {
            error = e.message || "Failed to fetch state";
        }
    }

    async function sendToggle(newValue: boolean) {
        loading = true;
        error = null;
        try {
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            const res = await fetch(props.url, {
                method: "PUT",
                headers,
                body: JSON.stringify({ [props.field || "state"]: newValue })
            });
            if (!res.ok) throw new Error(await res.text());

            // Fetch updated state
            await fetchState();
        } catch (err) {
            console.error(err);
            error = "Toggle failed";
            state = !newValue; // Revert on error
        } finally {
            loading = false;
        }
    }

    function flip() {
        const next = !state;
        state = next; // Optimistic update
        sendToggle(next);
    }

    onMount(() => {
        fetchState();

        if (props.refreshMs && props.refreshMs > 0) {
            interval = setInterval(fetchState, props.refreshMs);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    });

    const translateX = $derived(`translateX(${$position * 24}px)`);
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center w-full">
            <span>{props.name || "Toggle"}</span>
            <div class="flex items-center gap-2">
                {#if loading}
                    <Badge class="success">...</Badge>
                {/if}

                {#if error}
                    <div class="badge" style="border-color: #b91c1c; color: #fca5a5;">
                        {error}
                    </div>
                {/if}

                {#if props.refreshMs}
                    <RefreshButton onclick={fetchState} />
                {/if}
            </div>
        </div>
    </svelte:fragment>


    <svelte:fragment slot="children">

        <div class="flex items-center justify-between mt-2 font-approachmono">
            <span class:active-text={state}>{props.label || "Toggle"}</span>

            <button
                type="button"
                role="switch"
                aria-checked={state}
                onclick={flip}
                class="relative w-14 h-8 flex items-center rounded-full border border-[var(--edge-soft)] transition-all"
                class:active={state}
            >
                <span
                    class="inline-block w-6 h-6 bg-white rounded-full shadow-md transition-transform"
                    style="transform: {translateX};"
                />
            </button>
        </div>

    </svelte:fragment>
</Card>

<style>
    button.active {
        background-color: var(--primary);
    }

    .active-text {
        color: var(--primary);
    }
</style>
