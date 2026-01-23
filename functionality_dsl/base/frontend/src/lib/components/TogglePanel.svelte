<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import Badge from "$lib/primitives/Badge.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import { spring } from "svelte/motion";

    interface ToggleConfig {
        field: string;
        label: string;
    }

    const props = $props<{
        url: string;
        title?: string;
        toggles: ToggleConfig[];
        name?: string;
        refreshMs?: number;
    }>();

    let states = $state<Record<string, boolean>>({});
    let loading = $state<Record<string, boolean>>({});
    let error = $state<string | null>(null);
    let interval: ReturnType<typeof setInterval> | null = null;

    // Get initial auth state synchronously
    const initialAuth = authStore.getState();
    let authToken = $state<string | null>(initialAuth.token);
    let authType = $state<string>(initialAuth.authType);

    authStore.subscribe((authState) => {
        authToken = authState.token;
        authType = authState.authType;
    });

    // Spring animations for each toggle
    let positions = $state<Record<string, any>>({});

    // Initialize positions for all toggles
    $effect(() => {
        for (const toggle of props.toggles) {
            if (!positions[toggle.field]) {
                positions[toggle.field] = spring(0, { stiffness: 0.2, damping: 0.4 });
            }
            positions[toggle.field].set(states[toggle.field] ? 1 : 0);
        }
    });

    function getAuthHeaders(): { headers: Record<string, string>; fetchOptions: RequestInit } {
        const headers: Record<string, string> = {};
        const fetchOptions: RequestInit = { headers };

        if (authType === 'jwt' && authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        } else if (authType === 'basic' && authToken) {
            headers['Authorization'] = `Basic ${authToken}`;
        } else if (authType === 'session') {
            fetchOptions.credentials = 'include';
        }

        return { headers, fetchOptions };
    }

    async function fetchState() {
        if (!props.url) return;

        try {
            const { headers, fetchOptions } = getAuthHeaders();
            const res = await fetch(props.url, { ...fetchOptions, headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            const data = await res.json();

            // Update states for all toggles
            for (const toggle of props.toggles) {
                states[toggle.field] = !!data[toggle.field];
            }
            error = null;
        } catch (e: any) {
            error = e.message || "Failed to fetch state";
        }
    }

    async function sendToggle(field: string, newValue: boolean) {
        loading[field] = true;
        error = null;

        try {
            const { headers, fetchOptions } = getAuthHeaders();
            headers["Content-Type"] = "application/json";

            const res = await fetch(props.url, {
                ...fetchOptions,
                method: "PUT",
                headers,
                body: JSON.stringify({ [field]: newValue })
            });
            if (!res.ok) throw new Error(await res.text());

            // Fetch updated state
            await fetchState();
        } catch (err) {
            console.error(err);
            error = "Toggle failed";
            states[field] = !newValue; // Revert on error
        } finally {
            loading[field] = false;
        }
    }

    function flip(field: string) {
        const next = !states[field];
        states[field] = next; // Optimistic update
        sendToggle(field, next);
    }

    onMount(() => {
        // Initialize loading states
        for (const toggle of props.toggles) {
            loading[toggle.field] = false;
            states[toggle.field] = false;
        }

        fetchState();

        if (props.refreshMs && props.refreshMs > 0) {
            interval = setInterval(fetchState, props.refreshMs);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    });

    function getTranslateX(field: string): string {
        const pos = positions[field];
        if (pos && typeof pos.current === 'number') {
            return `translateX(${pos.current * 24}px)`;
        }
        return `translateX(${states[field] ? 24 : 0}px)`;
    }
</script>

<Card>
    <svelte:fragment slot="header">
        <div class="flex justify-between items-center w-full">
            <span>{props.title || props.name || "Controls"}</span>
            <div class="flex items-center gap-2">
                {#if error}
                    <Badge class="text-[var(--red-text)]">{error}</Badge>
                {/if}
                <RefreshButton onRefresh={fetchState} />
            </div>
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="toggles-container">
            {#each props.toggles as toggle}
                <div class="toggle-row">
                    <span class="toggle-label" class:active-text={states[toggle.field]}>
                        {toggle.label}
                    </span>

                    <div class="toggle-control">
                        {#if loading[toggle.field]}
                            <span class="loading-indicator">...</span>
                        {/if}

                        <button
                            type="button"
                            role="switch"
                            aria-checked={states[toggle.field]}
                            onclick={() => flip(toggle.field)}
                            class="toggle-switch"
                            class:active={states[toggle.field]}
                            disabled={loading[toggle.field]}
                        >
                            <span
                                class="toggle-knob"
                                style="transform: {getTranslateX(toggle.field)};"
                            />
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    </svelte:fragment>
</Card>

<style>
    .toggles-container {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .toggle-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--edge-soft);
    }

    .toggle-row:last-child {
        border-bottom: none;
    }

    .toggle-label {
        font-family: "Approach Mono", monospace;
        font-size: 0.875rem;
        color: var(--text-muted);
        transition: color 0.15s;
    }

    .toggle-label.active-text {
        color: var(--accent);
        font-weight: 500;
    }

    .toggle-control {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .loading-indicator {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .toggle-switch {
        position: relative;
        width: 3.5rem;
        height: 2rem;
        display: flex;
        align-items: center;
        border-radius: 9999px;
        border: 1px solid var(--edge-soft);
        background: var(--surface-secondary);
        cursor: pointer;
        transition: all 0.15s;
        padding: 0 0.25rem;
    }

    .toggle-switch:hover:not(:disabled) {
        border-color: var(--edge-light);
    }

    .toggle-switch:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .toggle-switch.active {
        background-color: var(--accent);
        border-color: var(--accent);
    }

    .toggle-knob {
        display: inline-block;
        width: 1.5rem;
        height: 1.5rem;
        background: white;
        border-radius: 9999px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        transition: transform 0.15s ease-out;
    }
</style>
