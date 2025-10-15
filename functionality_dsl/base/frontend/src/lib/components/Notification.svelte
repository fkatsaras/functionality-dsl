<script lang="ts">
  import { onMount } from "svelte";

  const {
    endpointPath,
    refreshMs = 3000,
    visibleMs = 4000
  } = $props<{
    endpointPath: string;
    refreshMs?: number;
    visibleMs?: number;
  }>();

  let message: string | null = null;
  let visible = false;
  let timer: ReturnType<typeof setInterval> | null = null;
  let hideTimer: ReturnType<typeof setTimeout> | null = null;

  async function fetchNotification() {
    try {
      const res = await fetch(endpointPath, { method: "GET" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data?.error) {
        message = data.error;
        visible = true;
        clearTimeout(hideTimer!);
        hideTimer = setTimeout(() => (visible = false), visibleMs);
      }
    } catch (e) {
      // avoid noisy console spam if endpoint unavailable
      console.debug("[Notification] fetch skipped or failed:", e);
    }
  }

  onMount(() => {
    fetchNotification();
    timer = setInterval(fetchNotification, refreshMs);
    return () => {
      clearInterval(timer!);
      clearTimeout(hideTimer!);
    };
  });
</script>

{#if visible && message}
  <div
    class="fixed bottom-6 right-6 z-50 flex items-center gap-2
           bg-red-50 border border-red-200 text-dag-danger rounded-lg
           px-3 py-2 shadow-lg animate-fade-in"
    role="alert"
    aria-live="assertive"
  >
    <!--  icon -->
    <svg
      class="w-5 h-5 text-dag-danger"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <circle cx="10" cy="10" r="8.5" />
      <path d="M7.2 7.2l5.6 5.6M12.8 7.2l-5.6 5.6" />
    </svg>
    <span class="font-approachmono text-sm">{message}</span>
  </div>
{/if}

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
      "Liberation Mono", "Courier New", monospace;
  }

  @keyframes fade-in {
    0% {
      opacity: 0;
      transform: translateY(10px) scale(0.95);
    }
    20% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
    80% {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
    100% {
      opacity: 0;
      transform: translateY(10px) scale(0.95);
    }
  }

  .animate-fade-in {
    animation: fade-in 4s ease-in-out forwards;
  }
</style>
