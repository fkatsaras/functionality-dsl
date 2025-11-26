<script lang="ts">
    const {
        data,
        class: className = ""
    } = $props<{
        data: any;
        class?: string;
    }>();
</script>

<div class="json-result-container {className}">
    <pre class="text-xs font-approachmono overflow-auto">{JSON.stringify(data, null, 2)}</pre>
</div>

<style>
    .json-result-container {
        padding: 0.75rem;
        background-color: var(--surface);
        border-radius: 0.375rem;
        border: 1px solid var(--edge);
    }

    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }

    pre {
        margin: 0;
        color: var(--text);
    }
</style>
