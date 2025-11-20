<script lang="ts">
    export let message: string = "Nothing to show";
</script>

<div class="flex flex-col items-center justify-center text-text-muted py-20 gap-4">
    <!-- Icon -->
    <svg
        class="w-12 h-12 text-text-muted opacity-50"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
    >
        <circle cx="12" cy="12" r="10" />
        <line x1="7" y1="7" x2="17" y2="17" />
    </svg>

    <!-- Message -->
    <div class="font-approachmono text-base opacity-80">
        {message}
    </div>
</div>

<style>
    .font-approachmono {
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
            "Liberation Mono", "Courier New", monospace;
    }
</style>
