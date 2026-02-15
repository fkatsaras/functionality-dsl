<script lang="ts">
    import { X } from "lucide-svelte";

    interface ColumnInfo {
        name: string;
        type?: {
            baseType: string;
        };
    }

    const {
        fields = [],
        columns = [],
        saving = false,
        actionError = null,
        isPermissionError = false,
        fieldErrors = {},
        onSubmit,
        onCancel,
    } = $props<{
        fields?: string[];
        columns?: ColumnInfo[];
        saving?: boolean;
        actionError?: string | null;
        isPermissionError?: boolean;
        fieldErrors?: Record<string, string>;
        onSubmit?: (data: Record<string, any>) => void;
        onCancel?: () => void;
    }>();

    let formData = $state<Record<string, any>>({});

    function toCamelLabel(field: string): string {
        return field.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
    }

    function getInputType(fieldName: string): string {
        const col = columns.find(c => c.name === fieldName);
        if (!col?.type) return "text";
        switch (col.type.baseType) {
            case "integer":
            case "number":
                return "number";
            case "boolean":
                return "checkbox";
            default:
                return "text";
        }
    }

    function handleSubmit() {
        onSubmit?.(formData);
    }

    function handleCancel() {
        formData = {};
        onCancel?.();
    }

    // Reset form data when fields change (new form opened)
    $effect(() => {
        if (fields.length > 0) {
            formData = {};
        }
    });
</script>

<div class="create-modal-overlay" onclick={handleCancel}>
    <div class="create-modal" onclick={(e) => e.stopPropagation()}>
        <div class="create-modal-header">
            <h4>New Entry</h4>
            <button class="icon-btn cancel" onclick={handleCancel} disabled={saving}>
                <X size={16} />
            </button>
        </div>
        {#if actionError && !isPermissionError}
            <div class="action-error">{actionError}</div>
        {/if}
        <div class="create-modal-fields">
            {#each fields as field}
                <div class="form-field">
                    <label for="create-{field}">{toCamelLabel(field)}</label>
                    {#if getInputType(field) === "checkbox"}
                        <input
                            id="create-{field}"
                            type="checkbox"
                            checked={formData[field] || false}
                            onchange={(e) => formData[field] = e.currentTarget.checked}
                            disabled={saving}
                        />
                    {:else if getInputType(field) === "number"}
                        <input
                            id="create-{field}"
                            type="number"
                            value={formData[field] || ""}
                            oninput={(e) => formData[field] = parseFloat(e.currentTarget.value) || 0}
                            disabled={saving}
                            class={fieldErrors[field] ? "input-error" : ""}
                        />
                    {:else}
                        <input
                            id="create-{field}"
                            type="text"
                            value={formData[field] || ""}
                            oninput={(e) => formData[field] = e.currentTarget.value}
                            disabled={saving}
                            class={fieldErrors[field] ? "input-error" : ""}
                        />
                    {/if}
                    {#if fieldErrors[field]}
                        <span class="field-error">{fieldErrors[field]}</span>
                    {/if}
                </div>
            {/each}
        </div>
        <div class="create-modal-actions">
            <button class="btn-secondary" onclick={handleCancel} disabled={saving}>Cancel</button>
            <button class="btn-primary" onclick={handleSubmit} disabled={saving}>
                {saving ? "Creating..." : "Create"}
            </button>
        </div>
    </div>
</div>

<style>
    .create-modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
    }

    .create-modal {
        background: var(--surface);
        border: 1px solid var(--edge);
        border-radius: 12px;
        padding: 1.5rem;
        width: 90%;
        max-width: 640px;
        max-height: 80vh;
        overflow-y: auto;
    }

    .create-modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.25rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--edge);
    }

    .create-modal-header h4 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
    }

    .create-modal-fields {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
    }

    .create-modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--edge);
    }

    .form-field {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }

    .form-field label {
        font-size: 0.75rem;
        font-weight: 500;
        font-family: "Approach Mono", ui-monospace, monospace;
        color: var(--text-muted);
    }

    .form-field input[type="text"],
    .form-field input[type="number"] {
        padding: 0.5rem;
        border: 1px solid var(--edge);
        border-radius: 4px;
        background: var(--surface);
        color: var(--text);
        font-size: 0.875rem;
    }

    .form-field input:focus {
        outline: none;
        border-color: var(--accent);
    }

    .form-field input.input-error {
        border-color: var(--red-text, #dc2626);
    }

    .form-field input.input-error:focus {
        border-color: var(--red-text, #dc2626);
        box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.15);
    }

    .field-error {
        font-size: 0.72rem;
        color: var(--red-text, #dc2626);
        font-family: "Approach Mono", ui-monospace, monospace;
    }

    .action-error {
        background: var(--red-tint, #fef2f2);
        color: var(--red-text, #dc2626);
        border: 1px solid var(--red-text, #dc2626);
        border-radius: 6px;
        padding: 0.5rem 0.75rem;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }

    .icon-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: 1px solid var(--edge);
        border-radius: 6px;
        background: var(--surface);
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .icon-btn.cancel {
        border-color: var(--red-text, #dc2626);
        color: var(--red-text, #dc2626);
    }

    .icon-btn.cancel:hover:not(:disabled) {
        background: var(--red-text, #dc2626);
        color: white;
    }

    .icon-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-primary,
    .btn-secondary {
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn-primary {
        background: var(--accent);
        color: white;
        border: none;
    }

    .btn-primary:hover:not(:disabled) {
        opacity: 0.9;
    }

    .btn-secondary {
        background: transparent;
        color: var(--text-muted);
        border: 1px solid var(--edge);
    }

    .btn-secondary:hover:not(:disabled) {
        border-color: var(--text-muted);
    }

    .btn-primary:disabled,
    .btn-secondary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
</style>
