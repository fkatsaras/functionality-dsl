<script lang="ts">
    import { onMount, onDestroy } from "svelte";

    const {
        value = null,
        relative = false,
        format = "datetime",
        class: className = ""
    } = $props<{
        value?: string | number | Date | null;
        relative?: boolean;
        format?: "date" | "time" | "datetime";
        class?: string;
    }>();

    let formattedTime = $state("");
    let interval: ReturnType<typeof setInterval> | null = null;

    function formatTimestamp() {
        if (!value) {
            formattedTime = "—";
            return;
        }

        try {
            const date = typeof value === "string" || typeof value === "number"
                ? new Date(value)
                : value;

            if (isNaN(date.getTime())) {
                formattedTime = "Invalid date";
                return;
            }

            if (relative) {
                formattedTime = getRelativeTime(date);
            } else {
                formattedTime = formatAbsolute(date);
            }
        } catch (e) {
            formattedTime = "Invalid date";
        }
    }

    function getRelativeTime(date: Date): string {
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);

        if (diffSec < 60) return "just now";
        if (diffMin < 60) return `${diffMin}m ago`;
        if (diffHour < 24) return `${diffHour}h ago`;
        if (diffDay < 7) return `${diffDay}d ago`;
        return formatAbsolute(date);
    }

    function formatAbsolute(date: Date): string {
        switch (format) {
            case "date":
                return date.toLocaleDateString();
            case "time":
                return date.toLocaleTimeString();
            case "datetime":
            default:
                return date.toLocaleString();
        }
    }

    onMount(() => {
        formatTimestamp();
        if (relative) {
            // Update every minute for relative timestamps
            interval = setInterval(formatTimestamp, 60000);
        }
    });

    onDestroy(() => {
        if (interval) clearInterval(interval);
    });

    // Re-format when value changes
    $effect(() => {
        if (value !== undefined) {
            formatTimestamp();
        }
    });
</script>

<span class={`font-approachmono text-[var(--text-muted)] text-sm ${className}`}>
    {formattedTime}
</span>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
