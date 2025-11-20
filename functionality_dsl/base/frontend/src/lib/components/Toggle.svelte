<script lang="ts">
    import Card from "$lib/primitives/Card.svelte";
    import Badge from "$lib/primitives/Badge.svelte";

    import { spring } from "svelte/motion";
    import { writable, derived } from "svelte/store";

    const {
        endpointPath,
        label = "Toggle",
        field = "state",
        name = "ToggleSwitch"
    } = $props<{
        endpointPath: string;
        label?: string;
        field?: string;
        name?: string;
    }>();

    const state = writable(false);
    let loading = false;
    let error: string | null = null;

    // 0 = off, 1 = on
    const position = spring(0, { stiffness: 0.2, damping: 0.4 });
    const translateX = derived(position, ($p) => `translateX(${$p * 24}px)`);

    $effect(() => {
        position.set($state ? 1 : 0);
    });

    async function sendToggle(newValue: boolean) {
        loading = true;
        error = null;
        try {
            const res = await fetch(endpointPath, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ [field]: newValue })
            });
            if (!res.ok) throw new Error(await res.text());
        } catch (err) {
            console.error(err);
            error = "Toggle failed";
        } finally {
            loading = false;
        }
    }

    function flip() {
        state.update((prev) => {
            const next = !prev;
            sendToggle(next);
            return next;
        });
    }
</script>

<Card>
    <svelte:fragment slot="header">
        {name}

        {#if loading}
            <Badge class="success">...</Badge>
        {/if}

        {#if error}
            <div class="badge" style="border-color: #b91c1c; color: #fca5a5;">
                {error}
            </div>
        {/if}
    </svelte:fragment>

    
    <svelte:fragment slot="children">

        <div class="flex items-center justify-between mt-2 font-approachmono">
            <span>{label}</span>

            <button
                type="button"
                role="switch"
                aria-checked={$state}
                onclick={flip}
                class="relative w-14 h-8 flex items-center rounded-full border border-[var(--edge-soft)] transition-all"
            >
                <span
                    class="inline-block w-6 h-6 bg-white rounded-full shadow-md transition-transform"
                    style="transform: {$translateX};"
                />
            </button>
        </div>

    </svelte:fragment>
</Card>
