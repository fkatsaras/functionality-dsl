<script lang="ts">
  import { onMount } from "svelte";

  const {
    name = "ActionForm",
    action,
    method = "POST",
    fields = [] as string[],
    pathKey = null as string | null,
    submitLabel = "Submit",
  } = $props<{
    name?: string;
    action: string;
    method?: "POST" | "PUT" | "PATCH" | "DELETE" | "GET";
    fields?: string[];
    pathKey?: string | null;
    submitLabel?: string;
  }>();

  let model: Record<string, any> = {};
  for (const k of fields) model[k] = "";

  let busy = $state<boolean>(false);
  let error = $state<string | null>(null);
  let ok = $state<string | null>(null);

  function endpoint(): string {
    const base = `/api/external${action.toLowerCase()}`;
    const pathVal = pathKey ? model[pathKey] : null;
    return pathVal != null && `${pathVal}` !== "" ? `${base}/${pathVal}` : base;
  }

  async function submit() {
    error = ok = null;
    busy = true;

    try {
      const body = structuredClone(model);
      if (pathKey) delete body[pathKey];

      const res = await fetch(endpoint(), {
        method,
        headers: { "Content-Type": "application/json" },
        body: (method === "DELETE" || method === "GET") ? undefined : JSON.stringify(body),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `${res.status} ${res.statusText}`);
      }

      ok = "Done.";
    } catch (e: any) {
      error = e?.message ?? "Request failed.";
    } finally {
      busy = false;
    }
  }
</script>

<div class="w-full flex justify-center items-center">
  <div class="w-4/5">
    <!-- Card -->
    <form
      class="rounded-2xl shadow-card border bg-[color:var(--card)] transition-colors"
      class:border-dag-success={ok && !error}
      class:border-dag-danger={!!error}
      class:table-border={!ok && !error}
      on:submit|preventDefault={submit}
      aria-live="polite"
    >
      <!-- Header -->
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>

          <!-- Success tick (custom SVG) -->
          {#if ok && !error}
            <svg
              class="w-5 h-5 text-dag-success"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              role="img"
              aria-label="Success"
            >
              <!-- circle -->
              <circle cx="10" cy="10" r="8.5" />
              <!-- check -->
              <path d="M6.5 10.5l2.5 2.5 4.5-5.5" />
            </svg>
          {/if}

          <!-- Error cross (custom SVG) -->
          {#if error}
            <svg
              class="w-5 h-5 text-dag-danger"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              role="img"
              aria-label="Error"
            >
              <!-- circle -->
              <circle cx="10" cy="10" r="8.5" />
              <!-- X -->
              <path d="M7.2 7.2l5.6 5.6M12.8 7.2l-5.6 5.6" />
            </svg>
          {/if}
        </div>

      </div>

      <!-- Body -->
      <div class="p-4 pt-0 space-y-4">
        {#each fields as key}
          <label class="flex flex-col gap-1">
            <span class="text-xs font-approachmono text-text/70">{key}</span>
            <input
              class="px-3 py-2 rounded-lg border thin-border bg-[color:var(--surface)] text-text/90 outline-none focus:ring-1 focus:ring-[color:var(--edge)]"
              bind:value={model[key]}
              placeholder={key}
            />
          </label>
        {/each}

        <!-- Footer actions -->
        <div class="flex items-center gap-3">
          <button
            class="px-3 py-1 text-xs rounded-lg border thin-border bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition disabled:opacity-60"
            type="submit"
            disabled={busy}
          >
            {busy ? "Working…" : submitLabel}
          </button>
        </div>
      </div>
    </form>
  </div>
</div>

<style>
  .font-approachmono {
    font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
      "Liberation Mono", "Courier New", monospace;
  }
  .thin-border, .table-border { border-color: var(--edge); }
</style>