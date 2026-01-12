<script lang="ts">
    import StateView from "./StateView.svelte";
    export let message: string = "Something went wrong";
</script>

<StateView message={message} tone="error">
    <svg
        class="w-12 h-12 opacity-70"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
    >
        <circle cx="12" cy="12" r="10" />
        <line x1="8" y1="8" x2="16" y2="16" />
        <line x1="16" y1="8" x2="8" y2="16" />
    </svg>
</StateView>
