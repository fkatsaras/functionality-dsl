<script lang="ts">
    const {
        label = "",
        value = "",
        unit = "",
        class: className = ""
    } = $props<{
        label?: string;
        value?: string | number;
        unit?: string;
        class?: string;
    }>();
</script>

<div class={`flex justify-between items-center py-2 border-b border-[var(--edge)] last:border-b-0 px-5 ${className}`} style="margin-left: -1.25rem; margin-right: -1.25rem; width: calc(100% + 2.5rem);">
    <span class="text-sm text-[var(--text-muted)] font-approachmono">
        {label}
    </span>
    <span class="text-sm text-[var(--text)] font-approachmono">
        {value}{#if unit}<span class="text-[var(--text-muted)] ml-1">{unit}</span>{/if}
    </span>
</div>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
