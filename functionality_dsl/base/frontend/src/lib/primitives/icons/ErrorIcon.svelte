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
    <path d="M7.2 7.2l5.6 5.6M12.8 7.2l-5.6 5.6" />
</svg>
