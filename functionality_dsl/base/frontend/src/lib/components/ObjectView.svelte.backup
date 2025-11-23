<script lang="ts">
    import { onMount } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";

    import Input from "$lib/primitives/Input.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";
    import Button from "$lib/primitives/Button.svelte";

    import { buildUrlWithParams } from "$lib/utils/paramBuilder";

    const props = $props<{
        name?: string;
        endpoint?: string;
        pathParams?: string[];
        fields?: string[];
        label?: string;
    }>();

    const label = props.label || props.name || "ObjectView";

    let id = $state("");
    let paramValues = $state<Record<string, string>>({});
    let data: Record<string, any> | null = $state(null);
    let loading = $state(false);
    let error: string | null = $state(null);

    // initialize path params
    $effect(() => {
        const init: Record<string, string> = {};
        for (const p of props.pathParams ?? []) init[p] = "";
        if (Object.keys(paramValues).length !== (props.pathParams?.length ?? 0)) {
            paramValues = init;
        }
    });

    function buildUrl() {
        if (!props.endpoint) return "";

        if (props.pathParams?.length) {
            return buildUrlWithParams(props.endpoint, paramValues);
        }

        if (!id.trim()) return "";
        return `${props.endpoint}/${encodeURIComponent(id.trim())}`;
    }

    async function fetchData() {
        const url = buildUrl();
        if (!url) {
            error = props.pathParams?.length
                ? "Please fill in all parameters."
                : "Please enter an ID.";
            data = null;
            return;
        }

        loading = true;
        error = null;
        data = null;

        try {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            data = await res.json();
        } catch (e) {
            error = String(e);
        } finally {
            loading = false;
        }
    }

    function getNestedValue(obj: any, path: string) {
        return path.split(".").reduce((acc, key) => acc?.[key], obj);
    }
</script>


<Card>
    <svelte:fragment slot="header">
        <div class="w-full flex justify-between items-center">
            <span class="font-approachmono text-xl">{label}</span>

            <div class="flex items-center gap-2">
                <RefreshButton on:click={fetchData} {loading} ariaLabel="Refresh object" />

                {#if error}
                    <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">
                        {error}
                    </span>
                {/if}
            </div>
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">

        {#if props.pathParams?.length}
            <div class="flex gap-2 mb-4">
                {#each props.pathParams as param}
                    <Input
                        bind:value={paramValues[param]}
                        placeholder={param}
                        class="font-approachmono"
                        on:keydown={(e: KeyboardEvent) => e.key === "Enter" && fetchData()}
                    />
                {/each}

                <Button
                    on:click={fetchData}
                    disabled={loading || props.pathParams.some((p: string) => !paramValues[p])}
                >
                    {#if loading}
                        <Spinner size={16} />
                    {:else}
                        Get
                    {/if}
                </Button>
            </div>

        {:else}

            <div class="flex gap-2 mb-4">
                <Input
                    bind:value={id}
                    placeholder="Enter ID…"
                    class="font-approachmono flex-1"
                    on:keydown={(e: KeyboardEvent) => e.key === "Enter" && fetchData()}
                />

                <Button
                    on:click={fetchData}
                    disabled={loading || !id.trim()}
                >
                    {#if loading}
                        <Spinner size={16} />
                    {:else}
                        View
                    {/if}
                </Button>
            </div>
        {/if}

        {#if loading}
            <Spinner size={20} />

        {:else if error && !data}
            <p class="font-approachmono text-sm text-dag-danger">{error}</p>

        {:else if data}
            <div class="border-t thin-border divide-y divide-[color:var(--edge)]">
                {#each props.fields as f}
                    <div class="flex justify-between py-2 px-1 even:bg-[color:var(--surface)] font-approachmono text-text/90">
                        <span class="font-medium text-text/80">{f}</span>
                        <span class="text-text/70">{getNestedValue(data, f)}</span>
                    </div>
                {/each}
            </div>

        {:else}
            <EmptyState message="No data loaded." />
        {/if}

    </svelte:fragment>
</Card>


<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
    .thin-border {
        border-color: var(--edge);
    }
</style>
