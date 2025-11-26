<script lang="ts">
    import Card from "$lib/primitives/Card.svelte";
    import Input from "$lib/primitives/Input.svelte";
    import Button from "$lib/primitives/Button.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";
    import JSONResult from "$lib/primitives/JSONResult.svelte";

    const {
        name = "QueryForm",
        url,
        fields = [] as string[],
        submitLabel = "Submit"
    } = $props();

    // Build model for query parameters
    let model: Record<string, any> = {};
    for (const f of fields) model[f] = "";

    // Reactive state
    let busy = $state(false);
    let error = $state<string | null>(null);
    let result = $state<any | null>(null);

    async function submit() {
        busy = true;
        error = null;
        result = null;

        try {
            // Build URL with query parameters
            const params = new URLSearchParams();
            for (const [key, value] of Object.entries(model)) {
                if (value != null && `${value}`.trim()) {
                    params.append(key, `${value}`);
                }
            }

            const queryString = params.toString();
            const finalUrl = queryString ? `${url}?${queryString}` : url;

            const res = await fetch(finalUrl, {
                method: "GET",
                headers: { "Accept": "application/json" }
            });

            if (!res.ok) {
                const text = await res.text().catch(() => "");
                throw new Error(text || `${res.status} ${res.statusText}`);
            }

            result = await res.json();
        } catch (e: any) {
            error = e?.message ?? "Request failed.";
        } finally {
            busy = false;
        }
    }
</script>

<!-- Card wrapper -->
<Card>
    <svelte:fragment slot="header">
        <span class="font-approachmono">{name}</span>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="flex flex-col gap-3">
            {#each fields as field}
                <div class="flex flex-col gap-1">
                    <label class="text-sm text-text/70 font-approachmono">{field}</label>
                    <Input
                        bind:value={model[field]}
                        placeholder={field}
                        class="font-approachmono"
                        on:keydown={(e) => e.key === "Enter" && submit()}
                    />
                </div>
            {/each}

            <Button
                on:click={submit}
                disabled={busy}
                class="mt-2"
            >
                {#if busy}
                    <Spinner size={16} />
                {:else}
                    {submitLabel}
                {/if}
            </Button>

            {#if error}
                <Badge class="text-[var(--red-text)] mt-2">{error}</Badge>
            {/if}

            {#if result}
                <JSONResult data={result} class="mt-4" />
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
