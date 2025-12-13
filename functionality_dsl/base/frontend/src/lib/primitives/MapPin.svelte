<script lang="ts">
    const {
        x = 0,
        y = 0,
        color = "var(--accent)",
        size = 24,
        label = "",
        class: className = ""
    } = $props<{
        x?: number;
        y?: number;
        color?: string;
        size?: number;
        label?: string;
        class?: string;
    }>();
</script>

<div
    class={`map-pin ${className}`}
    style={`left: ${x}px; top: ${y}px;`}
>
    <!-- Pin icon (location marker) -->
    <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={`filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));`}
    >
        <path
            d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"
            fill={color}
        />
    </svg>

    {#if label}
        <span class="pin-label">{label}</span>
    {/if}
</div>

<style>
    .map-pin {
        position: absolute;
        transform: translate(-50%, -100%);
        cursor: pointer;
        transition: transform 0.2s ease;
        z-index: 10;
    }

    .map-pin:hover {
        transform: translate(-50%, -100%) scale(1.15);
        z-index: 20;
    }

    .pin-label {
        position: absolute;
        top: -8px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--card);
        border: 1px solid var(--edge);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 10px;
        font-family: "Approach Mono", monospace;
        color: var(--text);
        white-space: nowrap;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.2s ease;
    }

    .map-pin:hover .pin-label {
        opacity: 1;
    }
</style>
