<script lang="ts">
    const {
        value = 0,
        label = "",
        trend = null,
        class: className = ""
    } = $props<{
        value?: number | string;
        label?: string;
        trend?: "up" | "down" | null;
        class?: string;
    }>();

    const trendColors: Record<string, string> = {
        up: "text-[var(--green-text)]",
        down: "text-[var(--red-text)]",
    };

    const trendIcons: Record<string, string> = {
        up: "↑",
        down: "↓",
    };
</script>

<div class={`flex flex-col gap-1 ${className}`}>
    <div class="flex items-baseline gap-2">
        <span class="text-2xl font-medium text-[var(--text)] font-approachmono">
            {value}
        </span>
        {#if trend}
            <span class={`text-sm font-medium ${trendColors[trend]}`}>
                {trendIcons[trend]}
            </span>
        {/if}
    </div>
    <span class="text-xs text-[var(--text-muted)] uppercase tracking-wide font-approachmono">
        {label}
    </span>
</div>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
