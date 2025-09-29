<script lang="ts">
  import { onMount, onDestroy } from "svelte";

  const {
    sinkPath = null,
    wsPath = null,
    label = "Input",
    placeholder = "",
    initial = "",
    submitLabel = "Send",
    name = "InputBox",
  } = $props<{
    sinkPath?: string | null;
    wsPath?: string | null;
    label?: string;
    placeholder?: string;
    initial?: string;
    submitLabel?: string;
    name?: string;
  }>();

  // prefer sinkPath, else wsPath
  const endpointPath = sinkPath || wsPath;

  let value = $state(initial);
  let ws: WebSocket | null = null;
  let connected = $state(false);
  let error = $state<string | null>(null);

  function send() {
    if (ws && connected) {
      try {
        ws.send(JSON.stringify({"text": value}));
        console.log("Sent over WS:", value);
        value = ""; // clear after send
      } catch (err) {
        error = "Send failed";
        console.error("Send error:", err);
      }
    }
  }

  onMount(() => {
    if (!endpointPath) { error = "No sinkPath provided"; return; }

    const wsUrl = endpointPath.startsWith("ws")
      ? endpointPath
      : `${location.protocol === "https:" ? "wss" : "ws"}://${location.hostname}:8080${endpointPath}`;

    ws = new WebSocket(wsUrl);
    ws.onopen = () => { connected = true; error = null; };
    ws.onclose = () => { connected = false; };
    ws.onerror = (e) => { error = "Connection error"; console.error(e); };
  });

  onDestroy(() => { ws?.close(); ws = null; });
</script>

<div class="w-full flex justify-center p-4">
  <div class="w-full max-w-sm">
    <div
      class="rounded-2xl shadow-lg border bg-[color:var(--card)] p-6 flex flex-col gap-4 transition-shadow duration-200 hover:shadow-xl"
      class:border-dag-success={connected}
      class:border-dag-danger={!connected}
    >
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>

        <div
          class="flex items-center gap-2 px-2 py-1 rounded-md border"
          class:border-dag-success={connected}
          class:border-dag-danger={!connected}
        >
          <svg
            class="w-4 h-4"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            aria-hidden="true"
            class:text-dag-success={connected}
            class:text-dag-danger={!connected}
          >
            <circle cx="10" cy="10" r="8.5" />
          </svg>
          <span class="text-xs font-approachmono"
            class:text-dag-success={connected}
            class:text-dag-danger={!connected}>
            {connected ? "LIVE" : "OFF"}
          </span>
        </div>
      </div>

      {#if error}
        <span class="text-xs text-dag-danger font-approachmono bg-red-50 px-2 py-1 rounded">{error}</span>
      {/if}

      <!-- Input row -->
      <div class="flex gap-2">
        <input
          type="text"
          bind:value
          placeholder={placeholder}
          class="border rounded px-3 py-2 flex-1 font-approachmono bg-dag-surface text-text focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          class="px-4 py-2 rounded bg-dag-success text-white font-approachmono transition-colors hover:bg-green-600 disabled:opacity-50"
          on:click={send}
          disabled={!connected}
        >
          {submitLabel}
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
