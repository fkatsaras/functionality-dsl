<script lang="ts">
    let {
        value = $bindable(),
        class: className = "",
        placeholder = "",
        rows = 6
    } = $props<{
        value: string;
        class?: string;
        placeholder?: string;
        rows?: number;
    }>();
</script>

<textarea
    class="textarea {className}"
    {placeholder}
    {rows}
    bind:value
    on:keydown
/>

<style>
    .textarea {
        padding: 0.65rem 0.75rem;
        border-radius: 8px;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        color: var(--text);
        width: 100%;
        transition: 0.15s ease;
        resize: vertical;
        font-family: inherit;
        font-size: inherit;
        line-height: 1.5;
    }

    .textarea:hover {
        border-color: var(--edge-light);
    }

    .textarea:focus {
        outline: none;
        border-color: var(--edge-light);
        box-shadow: 0 0 0 1px var(--edge-light);
    }
</style>
