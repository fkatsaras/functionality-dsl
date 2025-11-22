<script>
    let {
        value = $bindable(""),
        class: className = "",
        type = "text",
        placeholder = ""
    } = $props();
</script>

<input
    class={`input ${className}`}
    type={type}
    placeholder={placeholder}
    bind:value
    on:keydown
/>

<style>
    .input {
        padding: 0.65rem 0.75rem;
        border-radius: 8px;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        color: var(--text);
        width: 100%;
        transition: 0.15s ease;
    }

    .input:hover {
        border-color: var(--edge-light);
    }

    .input:focus {
        outline: none;
        border-color: var(--edge-light);
        box-shadow: 0 0 0 1px var(--edge-light);
    }
</style>
