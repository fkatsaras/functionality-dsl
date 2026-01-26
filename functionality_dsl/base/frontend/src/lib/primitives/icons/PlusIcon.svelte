<script>
    const { size = 20, class: className = "" } = $props();
</script>

<svg
    width={size}
    height={size}
    viewBox="0 0 20 20"
    fill="none"
    stroke="currentColor"
    stroke-width="1.8"
    stroke-linecap="round"
    stroke-linejoin="round"
    class={`animate-fade-in ${className}`}
>
    <circle cx="10" cy="10" r="8.5" />
    <path d="M10 6.5v7M6.5 10h7" />
</svg>