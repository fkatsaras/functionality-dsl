<script lang="ts">
    import { toastStore, type Toast } from "$lib/stores/toastStore";

    let toasts = $state<Toast[]>([]);
    toastStore.subscribe((v: Toast[]) => toasts = v);
</script>

{#if toasts.length > 0}
    <div class="toast-stack">
        {#each toasts as toast (toast.id)}
            <div class="toast toast--{toast.type}">
                <div class="toast-accent"></div>
                <div class="toast-icon">
                    {#if toast.type === 'success'}
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
                        </svg>
                    {:else if toast.type === 'error'}
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <circle cx="12" cy="12" r="10"/>
                            <path stroke-linecap="round" d="M15 9l-6 6m0-6l6 6"/>
                        </svg>
                    {:else if toast.type === 'authz'}
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                    {:else if toast.type === 'warning'}
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/>
                        </svg>
                    {:else}
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <circle cx="12" cy="12" r="10"/>
                            <path stroke-linecap="round" d="M12 16v-4m0-4h.01"/>
                        </svg>
                    {/if}
                </div>
                <div class="toast-body">
                    <p class="toast-title">{toast.title}</p>
                    <p class="toast-message">{toast.message}</p>
                </div>
                <button class="toast-close" onclick={() => toastStore.remove(toast.id)}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                        <path stroke-linecap="round" d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
        {/each}
    </div>
{/if}

<style>
    .toast-stack {
        position: fixed;
        bottom: 1.5rem;
        right: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        z-index: 9999;
        pointer-events: none;
    }

    .toast {
        display: flex;
        align-items: stretch;
        background: var(--card);
        border: 1px solid var(--edge);
        border-radius: 10px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        min-width: 300px;
        max-width: 420px;
        overflow: hidden;
        pointer-events: all;
        animation: toast-in 0.2s ease;
    }

    @keyframes toast-in {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    .toast-accent {
        width: 4px;
        flex-shrink: 0;
    }

    .toast--warning .toast-accent { background: var(--yellow-text); }
    .toast--error   .toast-accent { background: var(--red-text); }
    .toast--success .toast-accent { background: var(--green-text); }
    .toast--info    .toast-accent { background: var(--accent); }
    .toast--authz   .toast-accent { background: var(--yellow-text); }

    .toast-icon {
        display: flex;
        align-items: center;
        padding: 0.875rem 0.5rem 0.875rem 0.75rem;
        flex-shrink: 0;
    }

    /* LockIcon is w-6 h-6 by default, override to smaller */
    .toast-icon :global(svg) {
        width: 18px;
        height: 18px;
    }

    .toast--warning .toast-icon { color: var(--yellow-text); }
    .toast--error   .toast-icon { color: var(--red-text); }
    .toast--success .toast-icon { color: var(--green-text); }
    .toast--info    .toast-icon { color: var(--accent); }
    .toast--authz   .toast-icon { color: var(--yellow-text); }

    .toast-body {
        flex: 1;
        padding: 0.75rem 0.5rem 0.75rem 0;
        min-width: 0;
    }

    .toast-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: var(--text);
        margin: 0 0 0.2rem 0;
        line-height: 1.3;
    }

    .toast-message {
        font-size: 0.775rem;
        color: var(--text-muted);
        margin: 0;
        line-height: 1.4;
    }

    .toast-close {
        display: flex;
        align-items: flex-start;
        padding: 0.75rem 0.75rem 0 0;
        background: none;
        border: none;
        cursor: pointer;
        color: var(--text-muted);
        flex-shrink: 0;
        transition: color 0.15s;
    }

    .toast-close:hover {
        color: var(--text);
    }
</style>
