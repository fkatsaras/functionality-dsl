<script lang="ts">
  interface Props {
    loading?: boolean;
    ariaLabel?: string;
    title?: string;
    size?: "sm" | "md" | "lg";
    rounded?: boolean;
    externalClass?: string;
  }

  let {
    loading = false,
    ariaLabel = "Refresh",
    title,
    size = "md",
    rounded = true,
    externalClass = "",
  }: Props = $props();

  const paddings = { sm: "p-1.5", md: "p-2", lg: "p-3" }[size];
  const radius = rounded ? "rounded-full" : "rounded-lg";
  const base =
    `${paddings} ${radius} border thin-border bg-[color:var(--surface)] ` +
    `hover:bg-[color:var(--edge-soft)] transition disabled:opacity-60`;
</script>

<button
  type="button"
  aria-label={ariaLabel}
  title={title ?? ariaLabel}
  class={`${base} ${externalClass}`}
  disabled={loading}
  on:click
>
  <!-- Inline SVG  -->
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    class="w-4 h-4"
    class:animate-spin={loading}
  >
    <!-- Refresh arrows (simple, bold) -->
    <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.6M4.6 9A8 8 0 0119 7.5M19 20v-5h-.6m0 0A8 8 0 016 16.5" />
  </svg>
</button>

<style>
  .animate-spin { animation-duration: 800ms; }
</style>