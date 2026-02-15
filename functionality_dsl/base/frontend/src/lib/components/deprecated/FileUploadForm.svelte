<script lang="ts">
    import Card from "$lib/primitives/Card.svelte";
    import FileInput from "$lib/primitives/FileInput.svelte";
    import Button from "$lib/primitives/Button.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import Spinner from "$lib/primitives/icons/Spinner.svelte";
    import JSONResult from "$lib/primitives/JSONResult.svelte";
    import CheckIcon from "../primitives/icons/CheckIcon.svelte";
    import ErrorIcon from "../primitives/icons/ErrorIcon.svelte";

    const {
        name = "FileUploadForm",
        url,
        label = "Upload File",
        accept = "*",
        maxSize = 52428800,
        submitLabel = "Upload"
    } = $props();

    let childError: string | null = null;
    let ok: boolean = false;


    let file = $state<File | null>(null);
    let busy = $state(false);
    let error = $state<string | null>(null);
    let result = $state<any | null>(null);

    async function submit() {
        if (!file) {
            error = "Please select a file";
            return;
        }

        busy = true;
        error = null;
        result = null;

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(url, {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const errorText = await res.text().catch(() => "");
                throw new Error(errorText || `${res.status} ${res.statusText}`);
            }

            const contentType = res.headers.get("content-type") || "";
            if (contentType.includes("application/json")) {
                result = await res.json();
            } else {
                result = { response: await res.text() };
            }
        } catch (e: any) {
            error = e?.message ?? "Upload failed.";
        } finally {
            busy = false;
        }
    }
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="font-approachmono text-xl flex items-center gap-2">
            {label}
        
            {#if ok}
                <CheckIcon class="text-[var(--green-text)]" size={20} />
            {/if}
        
            {#if childError}
                <ErrorIcon class="text-[var(--edge-light)]" size={20} />
            {/if}
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="file-upload-form font-mono">
            <FileInput
                bind:file
                {accept}
                {maxSize}
                placeholder="Drop a file here or click to browse"
                on:error={(e) => childError = e.detail}
            />

            {#if error}
                <Badge variant="error">{error}</Badge>
            {/if}

            <Button
                on:click={submit}
                disabled={busy || !file}
                variant="primary"
                class="submit-button"
            >
                {#if busy}
                    <Spinner class="spinner" />
                    Uploading...
                {:else}
                    {submitLabel}
                {/if}
            </Button>

            {#if result}
                <div class="result-section">
                    <JSONResult data={result} />
                </div>
            {/if}
        </div>
    </svelte:fragment>
</Card>

<style>
    .file-upload-form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .submit-button {
        align-self: flex-start;
    }

    :global(.submit-button .spinner) {
        width: 1rem;
        height: 1rem;
        margin-right: 0.5rem;
    }

    .result-section {
        margin-top: 0.5rem;
    }
</style>
