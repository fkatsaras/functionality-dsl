<script lang="ts">
    import { preventDefault } from "svelte/legacy";
    import { authStore } from "$lib/stores/authStore";

    import Card from "$lib/primitives/Card.svelte";
    import Input from "$lib/primitives/Input.svelte";
    import Button from "$lib/primitives/Button.svelte";
    import Badge from "$lib/primitives/Badge.svelte";

    import CheckIcon from "$lib/primitives/icons/CheckIcon.svelte";
    import ErrorIcon from "$lib/primitives/icons/ErrorIcon.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";

    const {
        name = "ActionForm",
        url,
        method = "POST",
        fields = [] as string[],
        pathKey = null,
        submitLabel = "Submit"
    } = $props();

    // Build model
    let model: Record<string, any> = {};
    for (const f of fields) model[f] = "";

    // Reactive state
    let busy = $state(false);
    let error = $state<string | null>(null);
    let ok = $state<string | null>(null);
    let authToken = $state<string | null>(null);

    // Subscribe to auth store to get token
    authStore.subscribe((state) => {
        authToken = state.token;
    });

    function endpoint(): string {
        const base = url.replace(/\/+$/, "");
        let out = base;

        for (const m of base.matchAll(/\{([^{}]+)\}/g)) {
            const key = m[1];
            const val = model[key];
            if (val != null && `${val}`.trim()) {
                out = out.replace(`{${key}}`, encodeURIComponent(val));
            }
        }
        return out;
    }

    async function submit() {
        busy = true;
        error = ok = null;

        try {
            const body = structuredClone(model);
            if (pathKey) delete body[pathKey];

            // Parse JSON fields: detect strings that look like JSON and parse them
            for (const [key, value] of Object.entries(body)) {
                if (typeof value === 'string' && value.trim()) {
                    const trimmed = value.trim();
                    // Check if it looks like JSON (starts with [ or {)
                    if (trimmed.startsWith('[') || trimmed.startsWith('{')) {
                        try {
                            body[key] = JSON.parse(trimmed);
                        } catch (e) {
                            // If parsing fails, keep as string (might be intentional string value)
                        }
                    }
                }
            }

            const finalUrl = endpoint();

            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            const res = await fetch(finalUrl, {
                method,
                headers,
                body:
                    method === "DELETE" || method === "GET"
                        ? undefined
                        : JSON.stringify(body)
            });

            if (!res.ok) {
                const text = await res.text().catch(() => "");
                throw new Error(text || `${res.status} ${res.statusText}`);
            }

            ok = "Done.";
            setTimeout(() => (ok = null), 2500);
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
        <span>{name}</span>

        {#if ok}
            <CheckIcon class="text-[var(--green-text)]" size={20} />
        {/if}

        {#if error}
            <ErrorIcon class="text-[var(--edge-light)]" size={20} />
        {/if}
    </svelte:fragment>

    <svelte:fragment slot="children">

        <form class="space-y-4 max-w-[500px]" onsubmit={preventDefault(submit)}>
        
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
                <Button type="submit" disabled={busy}>
                    {#if busy}
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
