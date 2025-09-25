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
      style="stroke-width: 2;"
      class={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
    >
    <path
      style="stroke-linecap: round; stroke-linejoin: round;"
      d="M1 4v6h6M23 20v-6h-6M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"
    />
  </svg>
</button>

<style>
  .animate-spin { animation-duration: 800ms; }
</style>