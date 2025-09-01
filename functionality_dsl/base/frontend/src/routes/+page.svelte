<script lang="ts">
  // Auto-discover generated components under src/lib/generated/*.svelte
  // (Your generator writes them there.)
  const modules = import.meta.glob('/src/lib/components/*.svelte', { eager: true }) as Record<string, any>;
  const generated = Object.entries(modules)
    .map(([path, mod]) => ({ path, Comp: mod.default }))
    .sort((a, b) => a.path.localeCompare(b.path));
</script>

<div class="min-h-screen p-6">
  <header class="mb-6 flex items-center justify-between">
    <h1 class="text-lg font-approachmono text-text/90">FDSL Components</h1>
    <a href="/docs" class="text-xs text-accent hover:text-accentSoft underline">Docs</a>
  </header>

  {#if generated.length === 0}
    <div class="text-text-muted">No generated components found yet.</div>
  {:else}
    <div class="grid gap-6 md:grid-cols-2">
      {#each generated as g}
        <section class="rounded-xl2 shadow-card border table-border bg-card p-3">
          <div class="mb-2 text-xs font-approachmono text-text-muted">{g.path.split('/').pop()}</div>
          <div class="bg-[color:var(--surface)] rounded-lg p-2">
            <svelte:component this={g.Comp} />
          </div>
        </section>
      {/each}
    </div>
  {/if}
</div>
