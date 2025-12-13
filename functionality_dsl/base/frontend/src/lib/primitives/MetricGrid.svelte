<script lang="ts">
    const { class: className = "" } = $props<{
        class?: string;
    }>();
</script>

<div class={`metric-grid ${className}`}>
    <slot />
</div>

<style>
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 1.5rem;
        padding: 0.5rem 0;
    }

    @media (max-width: 640px) {
        .metric-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }
    }
</style>
