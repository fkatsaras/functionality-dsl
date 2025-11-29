<script lang="ts">
    import Card from "$lib/primitives/Card.svelte";
    import Button from "$lib/primitives/Button.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import Input from "$lib/primitives/Input.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";

    const props = $props<{
        label?: string;
        endpoint: string;
        filename?: string;
        buttonText?: string;
        params?: Record<string, string>;
        autoDownload?: boolean;
        showPreview?: boolean;
    }>();

    const label = props.label ?? "Download";
    const filename = props.filename ?? "download.bin";
    const buttonText = props.buttonText ?? "Download";

    let paramValues = $state<Record<string, string>>({ ...props.params });
    let isLoading = $state(false);
    let error: string | null = $state(null);
    let lastDownload: { size: number; time: Date } | null = null;

    function buildUrl(): string {
        const url = new URL(props.endpoint, window.location.origin);
        Object.entries(paramValues).forEach(([key, val]) => {
            if (val !== undefined && val !== null && val !== "") {
                url.searchParams.append(key, val);
            }
        });
        return url.toString();
    }

    async function download() {
        isLoading = true;
        error = null;

        try {
            const url = buildUrl();
            const res = await fetch(url);

            if (!res.ok) {
                const text = await res.text().catch(() => "");
                throw new Error(`HTTP ${res.status} ${text}`);
            }

            const blob = await res.blob();
            const blobUrl = URL.createObjectURL(blob);

            // Trigger browser download
            const link = document.createElement("a");
            link.href = blobUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(blobUrl);

            lastDownload = { size: blob.size, time: new Date() };

        } catch (e: any) {
            error = e?.message ?? "Download failed";
        } finally {
            isLoading = false;
        }
    }

    $effect(() => {
        if (props.autoDownload) download();
    });

    function sizeFmt(bytes: number) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return Math.round(bytes / 10.24) / 100 + " KB";
        return Math.round(bytes / 10485.76) / 100 + " MB";
    }
</script>

<Card>

    <svelte:fragment slot="header">
        <div class="flex items-center justify-between w-full">
            <span class="font-approachmono text-lg">{label}</span>

            {#if error}
                <Badge variant="error">{error}</Badge>
            {/if}
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">

        {#if Object.keys(paramValues).length > 0}
            <div class="flex flex-col gap-3 mb-4">
                {#each Object.entries(paramValues) as [p, v]}
                    <Input
                        bind:value={paramValues[p]}
                        placeholder={p}
                        class="font-approachmono"
                        on:keydown={(e: KeyboardEvent) => e.key === "Enter" && download()}
                    />
                {/each}
            </div>
        {/if}

        <Button on:click={download} disabled={isLoading}>
            {#if isLoading}
                <Spinner size={16} class="mr-2" />
                Downloading…
            {:else}
                ⬇ {buttonText}
            {/if}
        </Button>

        {#if props.showPreview}
            {#if lastDownload}
                <div class="mt-4 rounded-lg border p-3 bg-[color:var(--surface)] flex items-center gap-3">
                    <span class="text-xl">📄</span>

                    <div class="flex flex-col">
                        <span class="text-sm font-medium text-text">{filename}</span>
                        <span class="text-xs text-text-muted">Size: {sizeFmt(lastDownload.size)}</span>
                        <span class="text-xs text-text-muted">Downloaded: {lastDownload.time.toLocaleString()}</span>
                    </div>
                </div>
            {:else}
                <EmptyState message="No file downloaded yet." />
            {/if}
        {/if}

    </svelte:fragment>
</Card>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
