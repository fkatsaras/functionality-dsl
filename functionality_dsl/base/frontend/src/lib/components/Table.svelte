<script lang="ts">
    import { onMount } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import Card from "$lib/primitives/Card.svelte";
    import PlusIcon from "$lib/primitives/icons/PlusIcon.svelte";
    import { Pencil, Trash2, X, Check, AlertTriangle, Lock } from "lucide-svelte";

    interface ColumnInfo {
        name: string;
        type?: {
            baseType: string;
            format?: string;
            min?: number;
            max?: number;
            exact?: number;
            nullable?: boolean;
        };
    }

    const {
        url = null,
        colNames = [],
        columns = [],
        name = "Table",
        operations = [],
        readonlyFields = [],
        allFields = [],
        // Item mode props for array field CRUD
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

    // Full entity data (for itemMode, this is the parent entity used for PUT)
    let entityData = $state<Record<string, any> | null>(null);
    // Items to display in table (extracted from arrayField in itemMode)
    let data = $state<any[]>([]);
    let loading = $state(false);
    let error = $state<string | null>(null);
    let entityKeys = $state<string[]>([]);

    // CRUD state
    let editingRow = $state<number | null>(null);
    let editData = $state<Record<string, any>>({});
    let showCreateForm = $state(false);
    let createData = $state<Record<string, any>>({});
    let deleteConfirmRow = $state<number | null>(null);
    let saving = $state(false);
    let actionError = $state<string | null>(null);
    let isPermissionError = $state(false);  // Track if error is a 403 permission error

    // Get initial auth state synchronously
    const initialAuth = authStore.getState();
    let authToken = $state<string | null>(initialAuth.token);
    let authType = $state<string>(initialAuth.authType);

    // Subscribe to auth store for updates
    authStore.subscribe((state) => {
        authToken = state.token;
        authType = state.authType;
    });

    // Derived: which operations are available
    const canCreate = $derived(operations.includes("create"));
    const canUpdate = $derived(operations.includes("update"));
    const canDelete = $derived(operations.includes("delete"));
    const hasActions = $derived(canUpdate || canDelete);

    // Get editable fields (non-readonly)
    const editableFields = $derived(
        allFields.filter(f => !readonlyFields.includes(f))
    );

    function getAuthHeaders(): { headers: Record<string, string>; fetchOptions: RequestInit } {
        const headers: Record<string, string> = {};
        const fetchOptions: RequestInit = { headers };

        if (authType === 'jwt' && authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        } else if (authType === 'basic' && authToken) {
            // For Basic auth, authToken contains base64-encoded credentials
            headers['Authorization'] = `Basic ${authToken}`;
        } else if (authType === 'session') {
            fetchOptions.credentials = 'include';
        }

        return { headers, fetchOptions };
    }

    async function load() {
        const finalUrl = url || "";
        if (!finalUrl) {
            error = "No URL provided";
            return;
        }

        loading = true;
        error = null;
        isPermissionError = false;

        try {
            const { headers, fetchOptions } = getAuthHeaders();
            const response = await fetch(finalUrl, { ...fetchOptions, headers });
            if (!response.ok) {
                // Check for permission error (403)
                if (response.status === 403) {
                    isPermissionError = true;
                    const errBody = await response.json().catch(() => ({ detail: "Forbidden" }));
                    throw new Error(errBody.detail || "You don't have permission to view this data");
                }
                throw new Error(`${response.status} ${response.statusText}`);
            }

            const json = await response.json();

            // Item mode: store full entity, extract items from arrayField
            if (itemMode && arrayField) {
                entityData = json;
                data = json[arrayField] || [];
                if (data.length > 0 && typeof data[0] === "object") {
                    entityKeys = Object.keys(data[0]);
                }
            } else {
                // Entity mode: heuristic extraction (backwards compatible)
                entityData = null;

                if (Array.isArray(json)) {
                    if (
                        json.length === 1 &&
                        typeof json[0] === "object" &&
                        Object.keys(json[0]).length === 1
                    ) {
                        const firstKey = Object.keys(json[0])[0];
                        data = json[0][firstKey];
                    } else {
                        data = json;
                    }
                } else if (json && typeof json === "object") {
                    const keys = Object.keys(json);
                    if (keys.length === 1) {
                        const first = json[keys[0]];
                        if (Array.isArray(first)) {
                            data = first;
                        } else if (first && typeof first === "object") {
                            const innerKeys = Object.keys(first);
                            if (innerKeys.length === 1 && Array.isArray(first[innerKeys[0]])) {
                                data = first[innerKeys[0]];
                            } else {
                                throw new Error("Expected object with single array field inside entity.");
                            }
                        } else {
                            throw new Error("Expected entity object or array.");
                        }
                    } else {
                        const arrayKey = keys.find(k => Array.isArray(json[k]));
                        if (arrayKey) {
                            data = json[arrayKey];
                        } else {
                            throw new Error("Expected single entity key or an object with an array field.");
                        }
                    }
                }

                if (data.length > 0 && typeof data[0] === "object") {
                    entityKeys = Object.keys(data[0]);
                }
            }
        } catch (err: any) {
            error = err?.message ?? "Failed to load data from source.";
            data = [];
            entityData = null;
            entityKeys = [];
        } finally {
            loading = false;
        }
    }

    // ============================================================================
    // CRUD Operations
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
            const { headers, fetchOptions } = getAuthHeaders();
            headers['Content-Type'] = 'application/json';

            let payload: any;

            if (itemMode && arrayField && entityData) {
                // Item mode: update item in array, PUT entire entity
                const updatedItems = [...data];
                updatedItems[editingRow] = editData;
                payload = {
                    ...entityData,
                    [arrayField]: updatedItems
                };
            } else {
                // Entity mode: PUT the edited data directly
                payload = editData;
            }

            const response = await fetch(url, {
                ...fetchOptions,
                method: 'PUT',
                headers,
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errBody = await response.json().catch(() => ({ detail: response.statusText }));
                // Parse error detail (may be string or array from Pydantic)
                const errorDetail = parseErrorDetail(errBody.detail);
                // Check for permission error (403)
                if (response.status === 403) {
                    isPermissionError = true;
                    throw new Error(errorDetail || "You don't have permission to update items");
                }
                throw new Error(errorDetail || `HTTP ${response.status}`);
            }

            // Refresh data after successful update
            await load();
            editingRow = null;
            editData = {};
        } catch (err: any) {
            actionError = err?.message ?? "Failed to update";
        } finally {
            saving = false;
        }
    }

    function openCreateForm() {
        showCreateForm = true;
        // Initialize with empty values for editable fields
        createData = {};
        for (const field of editableFields) {
            createData[field] = "";
        }
        actionError = null;
        isPermissionError = false;
    }

    function cancelCreate() {
        showCreateForm = false;
        createData = {};
        actionError = null;
        isPermissionError = false;
    }

    async function submitCreate() {
        if (!url) return;

        saving = true;
        actionError = null;
        isPermissionError = false;

        try {
            const { headers, fetchOptions } = getAuthHeaders();
            headers['Content-Type'] = 'application/json';

            let method: string;
            let payload: any;

            if (itemMode && arrayField && entityData) {
                // Item mode: add item to array, PUT entire entity
                const updatedItems = [...data, createData];
                payload = {
                    ...entityData,
                    [arrayField]: updatedItems
                };
                method = 'PUT';  // PUT the whole entity, not POST
            } else {
                // Entity mode: POST the new data
                payload = createData;
                method = 'POST';
            }

            const response = await fetch(url, {
                ...fetchOptions,
                method,
                headers,
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errBody = await response.json().catch(() => ({ detail: response.statusText }));
                // Parse error detail (may be string or array from Pydantic)
                const errorDetail = parseErrorDetail(errBody.detail);
                // Check for permission error (403)
                if (response.status === 403) {
                    isPermissionError = true;
                    throw new Error(errorDetail || "You don't have permission to create items");
                }
                throw new Error(errorDetail || `HTTP ${response.status}`);
            }

            // Refresh data after successful create
            await load();
            showCreateForm = false;
            createData = {};
        } catch (err: any) {
            actionError = err?.message ?? "Failed to create";
        } finally {
            saving = false;
        }
    }

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
            const { headers, fetchOptions } = getAuthHeaders();
            headers['Content-Type'] = 'application/json';

            let method: string;
            let payload: any;

            if (itemMode && arrayField && entityData) {
                // Item mode: remove item from array, PUT entire entity
                const updatedItems = data.filter((_, idx) => idx !== deleteConfirmRow);
                payload = {
                    ...entityData,
                    [arrayField]: updatedItems
                };
                method = 'PUT';  // PUT the whole entity, not DELETE
            } else {
                // Entity mode: DELETE with row data
                payload = data[deleteConfirmRow];
                method = 'DELETE';
            }

            const response = await fetch(url, {
                ...fetchOptions,
                method,
                headers,
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errBody = await response.json().catch(() => ({ detail: response.statusText }));
                // Parse error detail (may be string or array from Pydantic)
                const errorDetail = parseErrorDetail(errBody.detail);
                // Check for permission error (403)
                if (response.status === 403) {
                    isPermissionError = true;
                    throw new Error(errorDetail || "You don't have permission to delete items");
                }
                throw new Error(errorDetail || `HTTP ${response.status}`);
            }

            // Refresh data after successful delete
            await load();
            deleteConfirmRow = null;
        } catch (err: any) {
            actionError = err?.message ?? "Failed to delete";
        } finally {
            saving = false;
        }
    }

    // ============================================================================
    // Helpers
    // ============================================================================

    /**
     * Parse error detail from API response (handles Pydantic validation errors)
     */
    function parseErrorDetail(detail: any): string {
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail)) {
            // Pydantic validation errors are arrays of {loc, msg, type}
            return detail.map((err: any) => {
                if (typeof err === 'string') return err;
                if (err.msg) {
                    const field = err.loc?.slice(1).join('.') || '';
                    return field ? `${field}: ${err.msg}` : err.msg;
                }
                return JSON.stringify(err);
            }).join(', ');
        }
        if (typeof detail === 'object' && detail !== null) {
            return detail.msg || detail.message || JSON.stringify(detail);
        }
        return String(detail);
    }

    function getValueByName(row: any, fieldName: string) {
        return row[fieldName];
    }

    function formatValue(value: any, column: ColumnInfo): string {
        if (value === null || value === undefined) {
            return column.type?.nullable ? "null" : "—";
        }

        const typeInfo = column.type;
        if (!typeInfo) return String(value);

        switch (typeInfo.baseType) {
            case "integer":
            case "number":
                if (typeof value === "number") {
                    if (typeInfo.baseType === "number") {
                        return value.toFixed(2);
                    }
                    return String(value);
                }
                return String(value);

            case "boolean":
                return value ? "✓" : "✗";

            case "string":
                if (typeInfo.format) {
                    switch (typeInfo.format) {
                        case "date":
                            if (typeof value === "string") {
                                try {
                                    const date = new Date(value);
                                    return date.toLocaleDateString();
                                } catch {
                                    return String(value);
                                }
                            }
                            return String(value);
                        case "time":
                            return String(value);
                        case "email":
                        case "uri":
                        case "image":
                            return String(value);
                        default:
                            return String(value);
                    }
                }
                return String(value);

            case "array":
                if (Array.isArray(value)) {
                    return `[${value.length} items]`;
                }
                return String(value);

            case "object":
                if (typeof value === "object") {
                    return "{...}";
                }
                return String(value);

            default:
                return String(value);
        }
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

    function isFieldReadonly(fieldName: string): boolean {
        return readonlyFields.includes(fieldName);
    }

    onMount(() => {
        load();
    });
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
                {#if error}
                    <div class={isPermissionError ? "header-permission-error" : "header-error"}>
                        {#if isPermissionError}
                            <Lock size={12} />
                        {/if}
                        <span>{error}</span>
                    </div>
                {/if}
                <RefreshButton onRefresh={load} loading={loading} />
            </div>
        </div>
    </svelte:fragment>

    <svelte:fragment slot="children">
        <!-- Create Form (Inline) -->
        {#if showCreateForm}
            <div class="crud-form">
                <div class="crud-form-header">
                    <h4>Create New {name}</h4>
                    <button class="icon-btn cancel" onclick={cancelCreate} disabled={saving}>
                        <X size={16} />
                    </button>
                </div>
                {#if actionError}
                    <div class={isPermissionError ? "permission-error" : "action-error"}>
                        {#if isPermissionError}
                            <Lock size={14} />
                        {/if}
                        <span>{actionError}</span>
                    </div>
                {/if}
                <div class="crud-form-fields">
                    {#each editableFields as field}
                        <div class="form-field">
                            <label for="create-{field}">{field}</label>
                            {#if getInputType(field) === "checkbox"}
                                <input
                                    id="create-{field}"
                                    type="checkbox"
                                    checked={createData[field] || false}
                                    onchange={(e) => createData[field] = e.currentTarget.checked}
                                    disabled={saving}
                                />
                            {:else if getInputType(field) === "number"}
                                <input
                                    id="create-{field}"
                                    type="number"
                                    value={createData[field] || ""}
                                    oninput={(e) => createData[field] = parseFloat(e.currentTarget.value) || 0}
                                    disabled={saving}
                                />
                            {:else}
                                <input
                                    id="create-{field}"
                                    type="text"
                                    value={createData[field] || ""}
                                    oninput={(e) => createData[field] = e.currentTarget.value}
                                    disabled={saving}
                                />
                            {/if}
                        </div>
                    {/each}
                </div>
                <div class="crud-form-actions">
                    <button class="btn-secondary" onclick={cancelCreate} disabled={saving}>Cancel</button>
                    <button class="btn-primary" onclick={submitCreate} disabled={saving}>
                        {saving ? "Creating..." : "Create"}
                    </button>
                </div>
            </div>
        {/if}

        <!-- Delete Confirmation Modal -->
        {#if deleteConfirmRow !== null}
            <div class="delete-confirm-overlay">
                <div class="delete-confirm-modal">
                    <div class="delete-confirm-icon">
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
                    <div class="delete-confirm-actions">
                        <button class="btn-secondary" onclick={cancelDelete} disabled={saving}>Cancel</button>
                        <button class="btn-danger" onclick={executeDelete} disabled={saving}>
                            {saving ? "Deleting..." : "Delete"}
                        </button>
                    </div>
                </div>
            </div>
        {/if}

        <div class="overflow-x-auto w-full">
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
                                            {:else if getInputType(fieldName) === "checkbox"}
                                                <input
                                                    type="checkbox"
                                                    checked={editData[fieldName] || false}
                                                    onchange={(e) => editData[fieldName] = e.currentTarget.checked}
                                                    disabled={saving}
                                                    class="edit-checkbox"
                                                />
                                            {:else if getInputType(fieldName) === "number"}
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
                                                <Check size={14} />
                                            </button>
                                            <button
                                                class="icon-btn cancel"
                                                onclick={cancelEdit}
                                                disabled={saving}
                                                title="Cancel"
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                        {#if actionError}
                                            <div class={isPermissionError ? "permission-error-inline" : "action-error-inline"}>
                                                {#if isPermissionError}
                                                    <Lock size={12} />
                                                {/if}
                                                <span>{actionError}</span>
                                            </div>
                                        {/if}
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
                                                        <Pencil size={14} />
                                                    </button>
                                                {/if}
                                                {#if canDelete}
                                                    <button
                                                        class="icon-btn delete"
                                                        onclick={() => confirmDelete(i)}
                                                        disabled={editingRow !== null || showCreateForm}
                                                        title="Delete"
                                                    >
                                                        <Trash2 size={14} />
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
        border: 1px solid var(--edge);
        border-radius: 6px;
        background: var(--surface);
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
        border-color: var(--red-text, #dc2626);
        color: var(--red-text, #dc2626);
    }

    .icon-btn.save {
        border-color: var(--green-text, #16a34a);
        color: var(--green-text, #16a34a);
    }

    .icon-btn.save:hover:not(:disabled) {
        background: var(--green-text, #16a34a);
        color: white;
    }

    .icon-btn.cancel {
        border-color: var(--red-text, #dc2626);
        color: var(--red-text, #dc2626);
    }

    .icon-btn.cancel:hover:not(:disabled) {
        background: var(--red-text, #dc2626);
        color: white;
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
        box-shadow: 0 0 0 2px rgba(var(--accent-rgb, 99, 102, 241), 0.2);
    }

    .edit-checkbox {
        width: 16px;
        height: 16px;
        cursor: pointer;
    }

    /* Create button (accent-colored plus icon) */
    .create-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: none;
        border-radius: 6px;
        background: transparent;
        color: var(--accent);
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

    /* Inline CRUD Form */
    .crud-form {
        background: var(--surface-secondary);
        border: 1px solid var(--edge);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .crud-form-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--edge);
    }

    .crud-form-header h4 {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
    }

    .crud-form-fields {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .crud-form-actions {
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
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.03em;
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


    .btn-primary,
    .btn-secondary,
    .btn-danger {
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

    .btn-danger {
        background: var(--red-text, #dc2626);
        color: white;
        border: none;
    }

    .btn-danger:hover:not(:disabled) {
        opacity: 0.9;
    }

    .btn-primary:disabled,
    .btn-secondary:disabled,
    .btn-danger:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    /* Delete Confirmation */
    .delete-confirm-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
    }

    .delete-confirm-modal {
        background: var(--surface);
        border: 1px solid var(--edge);
        border-radius: 12px;
        padding: 1.5rem;
        max-width: 400px;
        text-align: center;
    }

    .delete-confirm-icon {
        color: var(--red-text, #dc2626);
        margin-bottom: 1rem;
    }

    .delete-confirm-modal h4 {
        font-size: 1.125rem;
        font-weight: 600;
        color: var(--text);
        margin: 0 0 0.5rem 0;
    }

    .delete-confirm-modal p {
        font-size: 0.875rem;
        color: var(--text-muted);
        margin: 0 0 1rem 0;
    }

    .delete-confirm-actions {
        display: flex;
        justify-content: center;
        gap: 0.75rem;
    }

    /* Error messages */
    .action-error {
        padding: 0.5rem;
        border-radius: 4px;
        background: var(--red-tint, #fef2f2);
        color: var(--red-text, #dc2626);
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }

    .action-error-inline {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.7rem;
        color: var(--red-text, #dc2626);
        margin-top: 0.25rem;
    }

    /* Permission error styles (yellow/warning) */
    .permission-error {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        background: var(--yellow-tint, #fefce8);
        color: var(--yellow-text, #a16207);
        font-size: 0.8rem;
        margin-bottom: 1rem;
        border: 1px solid var(--yellow-text, #a16207);
    }

    .permission-error-inline {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.7rem;
        color: var(--yellow-text, #a16207);
        margin-top: 0.25rem;
    }

    /* Header errors */
    .header-error {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: var(--red-tint, #fef2f2);
        color: var(--red-text, #dc2626);
        font-size: 0.75rem;
    }

    .header-permission-error {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: var(--yellow-tint, #fefce8);
        color: var(--yellow-text, #a16207);
        border: 1px solid var(--yellow-text, #a16207);
        font-size: 0.75rem;
    }

    /* Create Modal */
    .modal-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
    }

    .modal-content {
        background: var(--surface);
        border: 1px solid var(--edge);
        border-radius: 12px;
        padding: 1.5rem;
        min-width: 400px;
        max-width: 600px;
        max-height: 80vh;
        overflow-y: auto;
    }

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--edge);
    }

    .modal-header h4 {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
    }

    .modal-form-fields {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--edge);
    }
</style>
