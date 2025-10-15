<script lang="ts">
  import { spring } from "svelte/motion";
  import { writable, derived } from "svelte/store";

  const {
    endpointPath,
    label = "Toggle",
    field = "state",
    name = "ToggleSwitch",
  } = $props<{
    endpointPath: string;
    label?: string;
    field?: string;
    name?: string;
  }>();

  // --- Reactive state ---
  const state = writable(false);
  let loading = false;
  let error: string | null = null;

  // --- SPRING animation (0 = off, 1 = on) ---
  const position = spring(0, {
    stiffness: 0.2,
    damping: 0.4,
  });

  // Derived for transform animation
  const translateX = derived(position, ($p) => `translateX(${$p * 24}px)`);

  $effect(() => {
    position.set($state ? 1 : 0);
  });

  async function sendToggle(newValue: boolean) {
    loading = true;
    error = null;
    try {
      const res = await fetch(endpointPath, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: newValue }),
      });
      if (!res.ok) throw new Error(await res.text());
    } catch (e) {
      console.error(e);
      error = "Toggle failed";
    } finally {
      loading = false;
    }
  }

  function flip() {
    state.update((prev) => {
      const next = !prev;
      console.log("State changing:", prev, "→", next); // 🔍
      sendToggle(next);
      return next;
    });
  }
</script>

<div class="w-full flex justify-center p-4">
  <div class="w-full max-w-sm">
    <div
      class="rounded-2xl shadow-lg border bg-[color:var(--card)] p-6 flex flex-col gap-5 transition-all duration-200 hover:shadow-xl"
    >
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>
      </div>

      {#if error}
        <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">
          {error}
        </span>
      {/if}

      <div class="flex items-center justify-between gap-3">
        <label class="font-approachmono text-text/90">{label}</label>

        <button
          type="button"
          role="switch"
          aria-checked={$state}
          on:click={flip}
          class={`relative w-14 h-8 flex items-center rounded-full p-1 focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors duration-300 ${
            $state
              ? 'bg-green-500 focus:ring-green-400'
              : 'bg-gray-400 focus:ring-gray-300'
          }`}
        >
          <span
            class="inline-block w-6 h-6 bg-white rounded-full shadow-md"
            style="transform: {$translateX};"
          ></span>
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
      "Liberation Mono", "Courier New", monospace;
  }

  button:active span {
    transform: scale(0.95);
  }
</style>
