<script lang="ts">
    interface Props {
        loading?: boolean;
        ariaLabel?: string;
        size?: "sm" | "md" | "lg";
        rounded?: boolean;
        externalClass?: string;
        onRefresh?: () => void;
    }

    const props = $props<Props>();

    // Derived
    const loading   = $derived(props.loading ?? false);
    const ariaLabel = $derived(props.ariaLabel ?? "Refresh");
    const size      = $derived(props.size ?? "md");
    const rounded   = $derived(props.rounded ?? true);
    const external  = $derived(props.externalClass ?? "");
    const onRefresh = $derived(props.onRefresh ?? (() => {}));

    const paddingsMap = { sm: "p-1.5", md: "p-2", lg: "p-3" } as const;
    const paddings    = $derived(paddingsMap[size]);
    const radius      = $derived(rounded ? "rounded-full" : "rounded-lg");

    const base = $derived(
        `${paddings} ${radius} 
         hover:bg-[color:var(--edge-soft)] transition disabled:opacity-60 
         outline-none focus:outline-none`
    );
</script>

<button
    type="button"
    aria-label={ariaLabel}
    class={`${base} ${external}`}
    disabled={loading}
    on:click={() => {
        if (!loading) onRefresh();
    }}
>
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        class={`w-4 h-4 ${loading ? "spin" : ""}`}
    >
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
        <path d="M3 3v5h5"/>
    </svg>
</button>

<style>
    .spin {
        animation: spin 0.65s linear infinite;
    }

    @keyframes spin {
        100% {
            transform: rotate(-360deg);
        }
    }
</style>
