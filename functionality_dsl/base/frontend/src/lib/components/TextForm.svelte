<script lang="ts">
    import Card from "$lib/primitives/Card.svelte";
    import Textarea from "$lib/primitives/Textarea.svelte";
    import Button from "$lib/primitives/Button.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";
    import JSONResult from "$lib/primitives/JSONResult.svelte";

    const {
        name = "TextForm",
        url,
        label = "Text Input",
        placeholder = "Enter text here...",
        submitLabel = "Submit"
    } = $props();

    // State
    let text = $state("");
    let busy = $state(false);
    let error = $state<string | null>(null);
    let result = $state<any | null>(null);

    async function submit() {
        busy = true;
        error = null;
        result = null;

        try {
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "text/plain",
                    "Accept": "application/json"
                },
                body: text
            });

            if (!res.ok) {
                const errorText = await res.text().catch(() => "");
                throw new Error(errorText || `${res.status} ${res.statusText}`);
            }

            // Try to parse as JSON
            const contentType = res.headers.get("content-type") || "";
            if (contentType.includes("application/json")) {
                result = await res.json();
            } else {
                // Plain text response
                const textResponse = await res.text();
                result = { response: textResponse };
            }
        } catch (e: any) {
            error = e?.message ?? "Request failed.";
        } finally {
            busy = false;
        }
    }
</script>

<Card>
    <svelte:fragment slot="header">
        <span class="font-approachmono">{name}</span>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="flex flex-col gap-3">
            <label class="text-sm text-text/70 font-approachmono">{label}</label>

            <Textarea
                bind:value={text}
                {placeholder}
                rows={8}
                class="font-approachmono"
            />

            <Button
                on:click={submit}
                disabled={busy || !text.trim()}
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
