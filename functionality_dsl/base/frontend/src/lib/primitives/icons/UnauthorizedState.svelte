<script lang="ts">
    import StateView from "./StateView.svelte";
    export let message: string = "You are not authorized to view this";
</script>

<StateView message={message} tone="warning">
    <svg
        class="w-12 h-12 opacity-70"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
    >
        <rect x="3" y="11" width="18" height="10" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
</StateView>
