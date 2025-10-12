<script lang="ts">
  import { preventDefault } from 'svelte/legacy';

  import { onMount } from "svelte";

  const {
    name = "ActionForm",
    url,
    method = "POST",
    fields = [] as string[],
    pathKey = null as string | null,
    submitLabel = "Submit",
  } = $props<{
    name?: string;
    url: string;
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
    const base = url.replace(/\/+$/, ""); // strip trailing slash if present
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
      setTimeout(() => {
        ok = null;
      }, 3000);
    } catch (e: any) {
      error = e?.message ?? "Request failed.";
    } finally {
      busy = false;
    }
  }
</script>

<div class="w-full flex justify-center items-center">
  <div class="w-4/5">
    <form
      class="rounded-2xl shadow-card border bg-[color:var(--card)] transition-all duration-300"
      class:border-dag-success={ok && !error}
      class:border-dag-danger={!!error}
      class:table-border={!ok && !error}
      on:submit={preventDefault(submit)}
      aria-live="polite"
    >
      <div class="p-4 pb-3 w-full flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <h2 class="text-xl font-bold font-approachmono text-text/90">{name}</h2>

          {#if ok && !error}
            <svg
              class="w-5 h-5 text-dag-success animate-fade-in"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              role="img"
              aria-label="Success"
            >
              <circle cx="10" cy="10" r="8.5" />
              <path d="M6.5 10.5l2.5 2.5 4.5-5.5" />
            </svg>
          {/if}

          {#if error}
            <svg
              class="w-5 h-5 text-dag-danger animate-fade-in"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              role="img"
              aria-label="Error"
            >
               circle 
              <circle cx="10" cy="10" r="8.5" />
               X 
              <path d="M7.2 7.2l5.6 5.6M12.8 7.2l-5.6 5.6" />
            </svg>
          {/if}
        </div>

      </div>

      <div class="p-4 pt-0 space-y-4">
        {#each fields as key}
          <label class="flex flex-col gap-1.5">
            <span class="text-xs font-approachmono text-text/70 font-medium">{key}</span>
            <input
              class="px-3.5 py-2.5 rounded-lg border thin-border bg-[color:var(--surface)] text-text/90 outline-none transition-all duration-200 focus:ring-2 focus:ring-[color:var(--edge)] focus:border-[color:var(--edge)] hover:border-[color:var(--edge)]/60"
              bind:value={model[key]}
              placeholder={key}
            />
          </label>
        {/each}

        <div class="flex items-center gap-3 pt-2">
          <button
            class="px-4 py-2 text-sm font-medium rounded-lg border thin-border bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-[color:var(--surface)]"
            type="submit"
            disabled={busy}
          >
            {#if busy}
              <div class="spinner" role="status" aria-label="Loading"></div>
            {:else}
              {submitLabel}
            {/if}
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
  
  /* Added fade-in animation for success/error icons */
  @keyframes fade-in {
    from {
      opacity: 0;
      transform: scale(0.8);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
  
  .animate-fade-in {
    animation: fade-in 0.2s ease-out;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
