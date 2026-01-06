<script lang="ts">
    export let message: string;
    export let tone: "neutral" | "error" | "warning" = "neutral";
</script>

<div class="state-view" data-tone={tone}>
    <slot />
    <div class="state-message font-approachmono">
        {message}
    </div>
</div>

<style>
    .state-view {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 2rem 1rem;
        text-align: center;
        color: var(--text-muted);
    }

    .state-view[data-tone="error"] {
        color: var(--red-text);
    }

    .state-view[data-tone="warning"] {
        color: var(--warning-text);
    }

    .state-message {
        font-size: 0.95rem;
        opacity: 0.85;
    }

    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, monospace;
    }
</style>
