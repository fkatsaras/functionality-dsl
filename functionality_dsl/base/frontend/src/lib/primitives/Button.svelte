<script>
    const { 
        type = "button", 
        class: className = "", 
        disabled = false 
    } = $props();
</script>

<button
    type={type}
    disabled={disabled}
    class={`btn ${className}`}
    on:click
>
    <slot />
</button>


<style>
    .btn {
        font-weight: 300;
        padding: 0.55rem 1rem;
        border-radius: 8px;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
        color: var(--text);
        transition: 0.15s ease background, 0.15s ease transform;
    }

    .btn:hover:not(:disabled) {
        background: var(--edge-soft);
    }

    .btn:active:not(:disabled) {
        transform: scale(0.97);
    }

    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }


</style>
