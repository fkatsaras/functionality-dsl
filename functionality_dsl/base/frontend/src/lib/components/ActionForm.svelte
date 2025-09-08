<script lang="ts">
    import { onMount } from "svelte";

    const {
        name = "ActionForm",
        action,
        method,
        fields = [] as string[],
        pathKey = null as string | null,
        submitLabel = "Submit",
    } = $props<{
        name?: string;
        action: string;
        method?: "POST"|"PUT"|"PATCH"|"DELETE";
        fields?: string[];
        pathKey?: string | null;
        submitLabel?: string;
    }>();

    let model: Record<string, any> = {};
    for (const k of fields) model[k] = "";

    let busy = $state<boolean>(false);
    let error = $state<string | null>(null);
    let ok = $state<string|null>(null);

    function endpoint(): string {
        // We hit the external passthrough
        const base = `/api/external${action.toLowerCase()}`;
        const pathVal = pathKey ? model[pathKey] : null;
        return pathVal != null && `${pathVal}` !== "" ? `${base}/${pathVal}` : base;
    }

    async function submit() {
        error = ok = null;
        busy = true;

        try {
            const body = structuredClone(model);
            // Dont send pathKey twice for PUT/DELETE id in path
            if (pathKey) {
                delete body[pathKey];
            }

            const response = await fetch(endpoint(), {
                method,
                headers: { "Content-Type": "application/json" },
                body: (method === "DELETE" || method === "GET") ? undefined : JSON.stringify(body),
            });

            if (!response.ok) {
                const text = await response.text().catch(() => "");
            }

            ok = "Done.";
        } catch (e: any) {
            error = e?.message ?? "Request failed.";
        } finally {
            busy = false;
        }
    }
</script>

<div class="w-full flex justify-center">
    <form class="w-4/5 space-y-4 rounded-x12 shadow-card table-border bg-[color:var(--card)]" on:submit|preventDefault={submit}>
        <div class="text-center mb-2">
            <h2 class="text-base font-approachmono text-text/90 tracking-tight">{name}</h2>
            <div class="text-[11px] text-text/60 font-approachmono">{method} -> {endpoint()}</div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            {#each fields as key}
            <label class="flex flex-col gap-1">
                <span class="text-xs font-approachmono text-text/70">{key}</span>
                <input class="px-3 py-2 rounded-lg border thin-border bg-[color:var(--surface)] text-text/90 outline-none focus:ring-1" bind:value={model[key]} placeholder={key} />
            </label>
            {/each}
        </div>

        <div class="flex items-center gap-3">
            <button class="px-3 py-1 text-xs rounded-lg border thin-border bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition disabled:opacity-60" type="submit" disabled={busy}> 
                {busy ? 'Working…' : submitLabel}
            </button>
            {#if ok}<span class="text-xs text-green-500">{ok}</span>{/if}
            {#if error}<span class="text-xs text-dag-danger">{error}</span>{/if}    
        </div>
    </form>
</div>

<style>
    .font-approachmono {
      font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }
    .thin-border, .table-border { border-color: var(--edge); }
</style>