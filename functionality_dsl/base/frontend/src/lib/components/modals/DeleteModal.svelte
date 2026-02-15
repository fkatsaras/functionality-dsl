<script lang="ts">
    import { AlertTriangle, Lock } from "lucide-svelte";

    const {
        saving = false,
        actionError = null,
        isPermissionError = false,
        onConfirm,
        onCancel,
    } = $props<{
        saving?: boolean;
        actionError?: string | null;
        isPermissionError?: boolean;
        onConfirm?: () => void;
        onCancel?: () => void;
    }>();
</script>

<div class="delete-modal-overlay" onclick={onCancel}>
    <div class="delete-modal" onclick={(e) => e.stopPropagation()}>
        <div class="delete-modal-icon">
            <AlertTriangle size={32} />
        </div>
        <h4>Confirm Delete</h4>
        <p>Are you sure you want to delete this item? This action cannot be undone.</p>
        {#if actionError}
            <div class={isPermissionError ? "permission-error" : "action-error"}>
                {#if isPermissionError}
                    <Lock size={14} />
                {/if}
                <span>{actionError}</span>
            </div>
        {/if}
        <div class="delete-modal-actions">
            <button class="btn-secondary" onclick={onCancel} disabled={saving}>Cancel</button>
            <button class="btn-danger" onclick={onConfirm} disabled={saving}>
                {saving ? "Deleting..." : "Delete"}
            </button>
        </div>
    </div>
</div>

<style>
    .delete-modal-overlay {
        position: fixed;
        inset: 0;
        background: var(--overlay);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
    }

    .delete-modal {
        background: var(--surface);
        border: 1px solid var(--edge);
        border-radius: 12px;
        padding: 1.5rem;
        max-width: 400px;
        text-align: center;
    }

    .delete-modal-icon {
        color: var(--red-text);
        margin-bottom: 1rem;
    }

    .delete-modal h4 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text);
        margin: 0 0 0.5rem 0;
    }

    .delete-modal p {
        font-size: 0.875rem;
        color: var(--text-muted);
        margin: 0 0 1rem 0;
    }

    .delete-modal-actions {
        display: flex;
        justify-content: center;
        gap: 0.75rem;
    }

    .action-error {
        padding: 0.5rem;
        border-radius: 4px;
        background: var(--red-tint);
        color: var(--red-text);
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }

    .permission-error {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        background: var(--yellow-tint);
        color: var(--yellow-text);
        font-size: 0.8rem;
        margin-bottom: 1rem;
        border: 1px solid var(--yellow-text);
    }

    .btn-secondary,
    .btn-danger {
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn-secondary {
        background: transparent;
        color: var(--text-muted);
        border: 1px solid var(--edge);
    }

    .btn-secondary:hover:not(:disabled) {
        border-color: var(--text-muted);
    }

    .btn-danger {
        background: var(--red-text);
        color: white;
        border: none;
    }

    .btn-danger:hover:not(:disabled) {
        opacity: 0.9;
    }

    .btn-secondary:disabled,
    .btn-danger:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>
