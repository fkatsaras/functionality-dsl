<script lang="ts">
    const {
        connected = false,
        size = 12,      // diameter in px
        class: className = ""
    } = $props<{
        connected?: boolean;
        size?: number;
        class?: string;
    }>();
</script>

<span
    class={`inline-block rounded-full ${className}`}
    style={`
        width:${size}px;
        height:${size}px;
        background:${connected ? '#16a34a' : '#dc2626'};
        box-shadow:
            0 0 6px ${connected ? 'rgba(22,163,74,0.8)' : 'rgba(220,38,38,0.8)'},
            inset 0 0 4px ${connected ? 'rgba(255,255,255,0.5)' : 'rgba(255,255,255,0.5)'};
    `}
></span>