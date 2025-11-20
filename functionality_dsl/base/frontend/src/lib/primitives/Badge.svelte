<script>
    const { class: className = "" } = $props();
</script>

<span class={`badge ${className}`}>
    <slot />
</span>
