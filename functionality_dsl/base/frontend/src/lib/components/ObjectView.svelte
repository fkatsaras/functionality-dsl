<script lang="ts">
    import { onMount } from "svelte";
    import Card from "$lib/primitives/Card.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import Badge from "$lib/primitives/Badge.svelte";

    import Input from "$lib/primitives/Input.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";
    import Button from "$lib/primitives/Button.svelte";

    import { buildUrlWithParams, buildQueryString } from "$lib/utils/paramBuilder";

    const props = $props<{
        name?: string;
        endpoint?: string;
        pathParams?: string[];
        queryParams?: string[];
        fields?: string[];
        label?: string;
    }>();

    const label = props.label || props.name || "ObjectView";

    let id = $state("");
    let paramValues = $state<Record<string, string>>({});
    let data: Record<string, any> | null = $state(null);
    let loading = $state(false);
    let error: string | null = $state(null);

    // initialize path and query params when they change
    $effect(() => {
        const init: Record<string, string> = {};
        if (props.pathParams?.length) {
            for (const p of props.pathParams) {
                init[p] = "";
            }
        }
        if (props.queryParams?.length) {
            for (const p of props.queryParams) {
                init[p] = "";
            }
        }
        if (Object.keys(init).length > 0) {
            paramValues = init;
        }
    });

    function buildUrl() {
        if (!props.endpoint) return "";

        let baseUrl = props.endpoint;

        // Handle path parameters
        if (props.pathParams?.length) {
            baseUrl = buildUrlWithParams(props.endpoint, paramValues);
            if (!baseUrl) return ""; // Missing required path params
        }

        // Handle query parameters
        if (props.queryParams?.length) {
            const queryString = buildQueryString(paramValues);
            return queryString ? `${baseUrl}?${queryString}` : "";
        }

        // Fallback to ID-based behavior (legacy)
        if (!id.trim()) return "";
        return `${props.endpoint}/${encodeURIComponent(id.trim())}`;
    }

    async function fetchData() {
        const url = buildUrl();
        if (!url) {
            error = props.pathParams?.length || props.queryParams?.length
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
            </div>
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">

        {#if props.pathParams?.length || props.queryParams?.length}
            <div class="flex gap-2 mb-4">
                {#if props.pathParams?.length}
                    {#each props.pathParams as param}
                        <Input
                            bind:value={paramValues[param]}
                            placeholder={param}
                            class="font-approachmono"
                            on:keydown={(e: KeyboardEvent) => e.key === "Enter" && fetchData()}
                        />
                    {/each}
                {/if}

                {#if props.queryParams?.length}
                    {#each props.queryParams as param}
                        <Input
                            bind:value={paramValues[param]}
                            placeholder={param}
                            class="font-approachmono"
                            on:keydown={(e: KeyboardEvent) => e.key === "Enter" && fetchData()}
                        />
                    {/each}
                {/if}

                <Button
                    on:click={fetchData}
                    disabled={loading || [...(props.pathParams || []), ...(props.queryParams || [])].some((p: string) => !paramValues[p])}
                >
                    {#if loading}
                        <Spinner size={16} />
                    {:else}
                        View
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

        {#if error}
            <Badge class="text-[var(--edge-light)] mt-2">{error}</Badge>
        {/if}

        {#if loading}
            <Spinner size={20} />

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
