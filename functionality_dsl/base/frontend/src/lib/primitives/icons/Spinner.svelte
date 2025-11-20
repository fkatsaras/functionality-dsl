<script>
    const { size = 20, class: className = "" } = $props();
</script>

<div
    class={`spinner ${className}`}
    style={`width:${size}px; height:${size}px;`}
    role="status"
    aria-label="Loading"
></div>

<style>
    .spinner {
        border: 3px solid var(--edge-soft);
        border-top-color: var(--text);
        border-radius: 50%;
        animation: spin 0.5s linear infinite;
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }
</style>
