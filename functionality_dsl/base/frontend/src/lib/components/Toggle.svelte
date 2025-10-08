<script lang="ts">
  const {
    endpointPath,
    label = "Toggle",
    onLabel = "ON",
    offLabel = "OFF",
    field = "state",
    initial = false,
    name = "ToggleSwitch",
  } = $props<{
    endpointPath: string;
    label?: string;
    onLabel?: string;
    offLabel?: string;
    field?: string;
    initial?: boolean;
    name?: string;
  }>();

  let state = $state(initial);
  let loading = $state(false);
  let error = $state<string | null>(null);

  async function sendToggle() {
    loading = true;
    error = null;
    try {
      const res = await fetch(endpointPath, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: state }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg);
      }
    } catch (e) {
      console.error(e);
      error = "Toggle failed";
    } finally {
      loading = false;
    }
  }

  function flip() {
    state = !state;
    sendToggle();
  }
</script>

<div class="w-full flex justify-center p-4">
  <div class="w-full max-w-sm">
    <div
      class="rounded-2xl shadow-lg border bg-[color:var(--card)] p-6 flex flex-col gap-4 transition-shadow duration-200 hover:shadow-xl"
    >
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>
      </div>

      {#if error}
        <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">{error}</span>
      {/if}

      <div class="flex items-center justify-between gap-3">
        <label class="font-approachmono text-text/90">{label}</label>
        <button
          on:click={() => flip()}
          class="px-4 py-2 rounded font-approachmono text-white transition-colors"
          class:bg-dag-success={state}
          class:bg-dag-danger={!state}
          disabled={loading}
        >
          {state ? onLabel : offLabel}
        </button>
      </div>
    </div>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }
</style>
