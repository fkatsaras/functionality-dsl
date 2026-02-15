<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import { toastStore } from "$lib/stores/toastStore";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import Card from "$lib/primitives/Card.svelte";
    import PlusIcon from "$lib/primitives/icons/PlusIcon.svelte";
    import EditIcon from "$lib/primitives/icons/EditIcon.svelte";
    import DeleteIcon from "$lib/primitives/icons/DeleteIcon.svelte";
    import SaveIcon from "$lib/primitives/icons/SaveIcon.svelte";
    import XIcon from "$lib/primitives/icons/XIcon.svelte";
    import CreateModal from "$lib/components/modals/CreateModal.svelte";
    import DeleteModal from "$lib/components/modals/DeleteModal.svelte";
    import { formatValue, getInputType, type ColumnInfo } from "$lib/utils/tableFormat";
    import { loadTableData, saveRow, createRow, deleteRow } from "$lib/utils/tableApi";

    const {
        url = null,
        colNames = [],
        columns = [],
        name = "Table",
        operations = [],
        readonlyFields = [],
        allFields = [],
        arrayField = null,
        keyField = null,
        itemMode = false,
    } = $props<{
        url?: string | null;
        colNames?: string[];
        columns?: ColumnInfo[];
        name?: string;
        operations?: string[];
        readonlyFields?: string[];
        allFields?: string[];
        arrayField?: string | null;
        keyField?: string | null;
        itemMode?: boolean;
    }>();

    // Data state
    let entityData = $state<Record<string, any> | null>(null);
    let data = $state<any[]>([]);
    let loading = $state(false);
    let error = $state<string | null>(null);
    let entityKeys = $state<string[]>([]);

    // CRUD state
    let editingRow = $state<number | null>(null);
    let editData = $state<Record<string, any>>({});
    let showCreateForm = $state(false);
    let createFieldErrors = $state<Record<string, string>>({});
    let deleteConfirmRow = $state<number | null>(null);
    let saving = $state(false);
    let actionError = $state<string | null>(null);
    let isPermissionError = $state(false);

    // Auth state
    const initialAuth = authStore.getState();
    let authToken = $state<string | null>(initialAuth.token);
    let authType = $state<string>(initialAuth.authType);
    authStore.subscribe((state) => { authToken = state.token; authType = state.authType; });

    const authConfig = $derived({ authType, authToken });

    // Derived capabilities
    const canCreate = $derived(operations.includes("create"));
    const canUpdate = $derived(operations.includes("update"));
    const canDelete = $derived(operations.includes("delete"));
    const hasActions = $derived(canUpdate || canDelete);
    const editableFields = $derived(allFields.filter(f => !readonlyFields.includes(f)));

    // ============================================================================
    // Load
    // ============================================================================

    async function load() {
        if (!url) { error = "No URL provided"; return; }
        loading = true;
        error = null;
        isPermissionError = false;
        try {
            const result = await loadTableData(url, authConfig, itemMode, arrayField);
            if (result.error) {
                error = result.error;
                isPermissionError = result.isPermissionError;
                data = []; entityData = null; entityKeys = [];
                if (isPermissionError) toastStore.warning("Access Denied", error);
            } else {
                data = result.data;
                entityData = result.entityData;
                entityKeys = result.entityKeys;
            }
        } catch (err: any) {
            error = err?.message ?? "Failed to load data from source.";
            data = []; entityData = null; entityKeys = [];
        } finally {
            loading = false;
        }
    }

    // ============================================================================
    // Edit
    // ============================================================================

    function startEdit(rowIndex: number) {
        editingRow = rowIndex;
        editData = { ...data[rowIndex] };
        actionError = null;
    }

    function cancelEdit() {
        editingRow = null;
        editData = {};
        actionError = null;
    }

    async function saveEdit() {
        if (editingRow === null || !url) return;
        saving = true;
        actionError = null;
        isPermissionError = false;
        try {
            const result = await saveRow(url, authConfig, editData, itemMode, arrayField, entityData, data, editingRow);
            if (result.error) {
                isPermissionError = result.isPermissionError;
                throw new Error(result.error);
            }
            await load();
            editingRow = null;
            editData = {};
        } catch (err: any) {
            actionError = err?.message ?? "Failed to update";
            if (isPermissionError) {
                toastStore.warning("Access Denied", actionError ?? "You don't have permission to update items");
                cancelEdit();
            } else {
                toastStore.error("Update Failed", actionError);
            }
        } finally {
            saving = false;
        }
    }

    // ============================================================================
    // Create
    // ============================================================================

    function openCreateForm() {
        showCreateForm = true;
        actionError = null;
        createFieldErrors = {};
        isPermissionError = false;
    }

    function cancelCreate() {
        showCreateForm = false;
        actionError = null;
        createFieldErrors = {};
        isPermissionError = false;
    }

    async function submitCreate(formData: Record<string, any>) {
        if (!url) return;
        saving = true;
        actionError = null;
        createFieldErrors = {};
        isPermissionError = false;
        try {
            const result = await createRow(url, authConfig, formData, editableFields, itemMode, arrayField, entityData, data);
            isPermissionError = result.isPermissionError;
            createFieldErrors = result.fieldErrors;
            if (result.error) throw new Error(result.error);
            if (!result.success) return;
            await load();
            showCreateForm = false;
        } catch (err: any) {
            actionError = err?.message ?? "Failed to create";
            if (isPermissionError) {
                toastStore.warning("Access Denied", actionError ?? "You don't have permission to create items");
            }
        } finally {
            saving = false;
        }
    }

    // ============================================================================
    // Delete
    // ============================================================================

    function confirmDelete(rowIndex: number) {
        deleteConfirmRow = rowIndex;
        actionError = null;
    }

    function cancelDelete() {
        deleteConfirmRow = null;
        actionError = null;
    }

    async function executeDelete() {
        if (deleteConfirmRow === null || !url) return;
        saving = true;
        actionError = null;
        isPermissionError = false;
        try {
            const result = await deleteRow(url, authConfig, deleteConfirmRow, itemMode, arrayField, entityData, data);
            if (result.error) {
                isPermissionError = result.isPermissionError;
                throw new Error(result.error);
            }
            await load();
            deleteConfirmRow = null;
        } catch (err: any) {
            actionError = err?.message ?? "Failed to delete";
            if (isPermissionError) {
                toastStore.warning("Access Denied", actionError ?? "You don't have permission to delete items");
                deleteConfirmRow = null;
            }
        } finally {
            saving = false;
        }
    }

    // ============================================================================
    // Template helpers
    // ============================================================================

    function getValueByName(row: any, fieldName: string) { return row[fieldName]; }
    function isFieldReadonly(fieldName: string): boolean { return readonlyFields.includes(fieldName); }
    function getColInputType(fieldName: string): string { return getInputType(fieldName, columns); }

    onMount(() => { load(); });
</script>

<Card class="table-card" fullWidth={true}>
    <svelte:fragment slot="header">
        <div class="flex items-center justify-between w-full">
            <span>{name}</span>

            <div class="flex items-center gap-2">
                {#if canCreate}
                    <button
                        class="create-btn"
                        onclick={openCreateForm}
                        disabled={showCreateForm || editingRow !== null}
                        title="Create new"
                    >
                        <PlusIcon size={18} />
                    </button>
                {/if}
                {#if error && !isPermissionError}
                    <div class="header-error">
                        <span>{error}</span>
                    </div>
                {/if}
                <RefreshButton onRefresh={load} loading={loading} />
            </div>
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <div class="overflow-x-auto -mx-5">
            <table class="min-w-full border-collapse text-sm font-mono">
                <thead class="bg-[color:var(--surface)] sticky top-0 z-10">
                    <tr>
                        {#each colNames as displayName}
                            <th class="text-left px-3 py-2 border-b border-[color:var(--edge)] font-mono text-text/90 tracking-wide">
                                {displayName}
                            </th>
                        {/each}
                        {#if hasActions}
                            <th class="text-center px-3 py-2 border-b border-[color:var(--edge)] font-mono text-text/90 tracking-wide w-24">
                                Actions
                            </th>
                        {/if}
                    </tr>
                </thead>

                <tbody>
                    {#if data.length === 0}
                        <tr>
                            <td colspan={colNames.length + (hasActions ? 1 : 0)} class="h-10 text-center text-text/50">
                                {loading ? "Loading..." : "No data"}
                            </td>
                        </tr>
                    {:else}
                        {#each data as row, i (`row-${i}`)}
                            {#if editingRow === i}
                                <!-- Edit Mode Row -->
                                <tr class="bg-[color:var(--surface-secondary)]">
                                    {#each colNames as displayName, position}
                                        {@const column = columns[position] || { name: displayName, type: { baseType: "string" } }}
                                        {@const fieldName = column.name}
                                        {@const isReadonly = isFieldReadonly(fieldName)}
                                        <td class="px-3 py-2 border-b border-[color:var(--edge)]">
                                            {#if isReadonly}
                                                <span class="text-text/50">{formatValue(row[fieldName], column)}</span>
                                            {:else if getColInputType(fieldName) === "checkbox"}
                                                <input
                                                    type="checkbox"
                                                    checked={editData[fieldName] || false}
                                                    onchange={(e) => editData[fieldName] = e.currentTarget.checked}
                                                    disabled={saving}
                                                    class="edit-checkbox"
                                                />
                                            {:else if getColInputType(fieldName) === "number"}
                                                <input
                                                    type="number"
                                                    value={editData[fieldName] ?? ""}
                                                    oninput={(e) => editData[fieldName] = parseFloat(e.currentTarget.value) || 0}
                                                    disabled={saving}
                                                    class="edit-input"
                                                />
                                            {:else}
                                                <input
                                                    type="text"
                                                    value={editData[fieldName] ?? ""}
                                                    oninput={(e) => editData[fieldName] = e.currentTarget.value}
                                                    disabled={saving}
                                                    class="edit-input"
                                                />
                                            {/if}
                                        </td>
                                    {/each}
                                    <td class="px-3 py-2 border-b border-[color:var(--edge)] text-center">
                                        <div class="action-btns">
                                            <button
                                                class="icon-btn save"
                                                onclick={saveEdit}
                                                disabled={saving}
                                                title="Save"
                                            >
                                                <SaveIcon size={14} />
                                            </button>
                                            <button
                                                class="icon-btn cancel"
                                                onclick={cancelEdit}
                                                disabled={saving}
                                                title="Cancel"
                                            >
                                                <XIcon size={14} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            {:else}
                                <!-- Normal Row -->
                                <tr class="odd:bg-transparent even:bg-[color:var(--surface)] hover:bg-[color:var(--edge-soft)] transition-colors">
                                    {#each colNames as displayName, position}
                                        {@const column = columns[position] || { name: displayName, type: { baseType: "string" } }}
                                        {@const rawValue = getValueByName(row, column.name)}

                                        <td class="px-3 py-2 border-b border-[color:var(--edge)] text-text/90 font-mono">
                                            {#if column.type?.format === "image" && rawValue}
                                                <img src={String(rawValue)} class="max-w-24 max-h-24 object-contain rounded" />
                                            {:else if column.type?.format === "binary" && rawValue}
                                                <img src={`data:image/png;base64,${String(rawValue)}`} class="max-w-24 max-h-24 object-contain rounded" />
                                            {:else if column.type?.format === "uri" && rawValue && (String(rawValue).match(/\.(jpg|jpeg|png|gif|webp)$/i))}
                                                <img src={String(rawValue)} class="max-w-24 max-h-24 object-contain rounded" />
                                            {:else}
                                                {formatValue(rawValue, column)}
                                            {/if}
                                        </td>
                                    {/each}
                                    {#if hasActions}
                                        <td class="px-3 py-2 border-b border-[color:var(--edge)] text-center">
                                            <div class="action-btns">
                                                {#if canUpdate}
                                                    <button
                                                        class="icon-btn edit"
                                                        onclick={() => startEdit(i)}
                                                        disabled={editingRow !== null || showCreateForm}
                                                        title="Edit"
                                                    >
                                                        <EditIcon size={14} />
                                                    </button>
                                                {/if}
                                                {#if canDelete}
                                                    <button
                                                        class="icon-btn delete"
                                                        onclick={() => confirmDelete(i)}
                                                        disabled={editingRow !== null || showCreateForm}
                                                        title="Delete"
                                                    >
                                                        <DeleteIcon size={14} />
                                                    </button>
                                                {/if}
                                            </div>
                                        </td>
                                    {/if}
                                </tr>
                            {/if}
                        {/each}
                    {/if}
                </tbody>
            </table>
        </div>
    </svelte:fragment>
</Card>

<!-- Create Modal - rendered outside Card to avoid transform stacking context -->
{#if showCreateForm}
    <CreateModal
        fields={editableFields}
        columns={columns}
        saving={saving}
        actionError={actionError}
        isPermissionError={isPermissionError}
        fieldErrors={createFieldErrors}
        onSubmit={submitCreate}
        onCancel={cancelCreate}
    />
{/if}

<!-- Delete Modal - rendered outside Card to avoid transform stacking context -->
{#if deleteConfirmRow !== null}
    <DeleteModal
        saving={saving}
        actionError={actionError}
        isPermissionError={isPermissionError}
        onConfirm={executeDelete}
        onCancel={cancelDelete}
    />
{/if}

<style>
    table {
        width: 100%;
        border-spacing: 0;
    }

    thead th {
        background: var(--surface-secondary);
        border-bottom: 2px solid var(--edge);
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.03em;
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
        color: var(--text);
    }

    th {
        background: var(--surface);
        font-size: 0.8rem;
        font-weight: 600;
        user-select: none;
    }

    td {
        font-size: 0.8rem;
    }

    /* Action buttons */
    .action-btns {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }

    .icon-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 6px;
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .icon-btn:hover:not(:disabled) {
        border-color: var(--accent);
        color: var(--accent);
    }

    .icon-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    .icon-btn.edit:hover:not(:disabled) {
        border-color: var(--accent);
        color: var(--accent);
    }

    .icon-btn.delete:hover:not(:disabled) {
        border-color: var(--red-text);
        color: var(--red-text);
    }

    .icon-btn.save:hover:not(:disabled) {
        color: var(--green-text);
    }

    .icon-btn.cancel:hover:not(:disabled) {
        color: var(--red-text);
    }

    /* Create button (icon only, accent style) */
    .icon-btn.create {
        border-color: var(--accent);
        background: var(--accent);
        color: white;
    }

    .icon-btn.create:hover:not(:disabled) {
        opacity: 0.9;
        border-color: var(--accent);
        background: var(--accent);
        color: white;
    }

    /* Edit input in table */
    .edit-input {
        width: 100%;
        padding: 0.35rem 0.5rem;
        border: 1px solid var(--accent);
        border-radius: 4px;
        background: var(--surface);
        color: var(--text);
        font-size: 0.8rem;
        font-family: inherit;
    }

    .edit-input:focus {
        outline: none;
        border-color: var(--accent);
        box-shadow: 0 0 0 2px var(--accent-subtle);
    }

    .edit-checkbox {
        width: 16px;
        height: 16px;
        cursor: pointer;
    }

    /* Create button */
    .create-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 6px;
        background: transparent;
        color: var(--text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .create-btn:hover:not(:disabled) {
        background: var(--edge-soft);
        transform: scale(1.05);
    }

    .create-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    /* Error messages */
    .action-error {
        padding: 0.5rem;
        border-radius: 4px;
        background: var(--red-tint);
        color: var(--red-text);
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }

    .action-error-inline {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.7rem;
        color: var(--red-text);
        margin-top: 0.25rem;
    }

    /* Permission error styles (yellow/warning) */
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

    .permission-error-inline {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.7rem;
        color: var(--yellow-text);
        margin-top: 0.25rem;
    }

    /* Header errors */
    .header-error {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: var(--red-tint);
        color: var(--red-text);
        font-size: 0.75rem;
    }

    .header-permission-error {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: var(--yellow-tint);
        color: var(--yellow-text);
        border: 1px solid var(--yellow-text);
        font-size: 0.75rem;
    }

</style>
