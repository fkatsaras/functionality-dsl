<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import KeyValue from "$lib/primitives/KeyValue.svelte";
    import JSONResult from "$lib/primitives/JSONResult.svelte";
    import RefreshButton from "$lib/primitives/RefreshButton.svelte";
    import LiveIndicator from "$lib/primitives/LiveIndicator.svelte";
    import EmptyState from "$lib/primitives/icons/EmptyState.svelte";
    import ErrorState from "../primitives/icons/ErrorState.svelte";
    import UnauthorizedState from "../primitives/icons/UnauthorizedState.svelte";
    import { Pencil, X, Check, Lock } from "lucide-svelte";

    const props = $props<{
        // REST mode props
        url?: string;
        refreshMs?: number;
        // WebSocket mode props
        wsUrl?: string;
        // Common props
        fields: string[];
        title?: string;
        highlight?: string;
        // Edit mode props
        operations?: string[];
        readonlyFields?: string[];
    }>();

    let data = $state<Record<string, any> | null>(null);
    let editData = $state<Record<string, any>>({});
    let error = $state<string | null>(null);
    let loading = $state(true);
    let saving = $state(false);
    let editMode = $state(false);
    let interval: ReturnType<typeof setInterval> | null = null;
    let ws: WebSocket | null = null;

    // Get initial auth state synchronously
    const initialAuth = authStore.getState();
    let authToken = $state<string | null>(initialAuth.token);
    let authType = $state<string>(initialAuth.authType);

    // Subscribe to auth store for updates
    authStore.subscribe((state) => {
        authToken = state.token;
        authType = state.authType;
    });

    // Determine mode based on props
    const isWebSocketMode = $derived(!!props.wsUrl);

    // Check if update operation is available
    const canEdit = $derived(
        !isWebSocketMode &&
        props.operations?.includes("update")
    );

    // Check if a field is readonly
    function isReadonly(field: string): boolean {
        return props.readonlyFields?.includes(field) ?? false;
    }

    // Get editable fields (non-readonly fields from the displayed fields)
    const editableFields = $derived(
        props.fields.filter(f => !isReadonly(f))
    );

    // ============================================================================
    // Error parsing helper (handles Pydantic validation errors)
    // ============================================================================
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

    // ============================================================================
    // REST Mode - Fetch data via HTTP
    // ============================================================================
    function getAuthHeaders(): { headers: Record<string, string>; fetchOptions: RequestInit } {
        const headers: Record<string, string> = {};
        const fetchOptions: RequestInit = { headers };

        if (authType === 'jwt' && authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        } else if (authType === 'session') {
            fetchOptions.credentials = 'include';
        }

        return { headers, fetchOptions };
    }

    async function fetchData() {
        if (!props.url) return;

        try {
            const { headers, fetchOptions } = getAuthHeaders();
            const res = await fetch(props.url, { ...fetchOptions, headers });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            data = await res.json();
            error = null;
        } catch (e: any) {
            error = e.message || "Failed to fetch data";
            data = null;
        } finally {
            loading = false;
        }
    }

    // ============================================================================
    // Edit Mode - Save changes via PUT
    // ============================================================================
    function enterEditMode() {
        if (!data || !canEdit) return;
        // Copy current data to edit buffer
        editData = { ...data };
        editMode = true;
    }

    function cancelEdit() {
        editMode = false;
        editData = {};
        error = null;
    }

    async function saveEdit() {
        if (!props.url || !data) return;

        saving = true;
        error = null;

        try {
            const { headers, fetchOptions } = getAuthHeaders();
            headers['Content-Type'] = 'application/json';

            // Build payload with only editable fields (exclude readonly fields)
            const payload: Record<string, any> = {};
            for (const field of editableFields) {
                payload[field] = field in editData ? editData[field] : data[field];
            }

            const res = await fetch(props.url, {
                ...fetchOptions,
                method: 'PUT',
                headers,
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const errBody = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(parseErrorDetail(errBody.detail) || `HTTP ${res.status}`);
            }

            // Update local data with response
            data = await res.json();
            editMode = false;
            editData = {};
        } catch (e: any) {
            error = e.message || "Failed to save";
        } finally {
            saving = false;
        }
    }

    // ============================================================================
    // WebSocket Mode - Subscribe to real-time updates
    // ============================================================================
    function connectWebSocket() {
        if (!props.wsUrl) return;

        try {
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const wsPath = props.wsUrl.startsWith("/") ? props.wsUrl : `/${props.wsUrl}`;
            const fullUrl = `${protocol}//${window.location.host}${wsPath}`;

            ws = new WebSocket(fullUrl);

            ws.onopen = () => {
                loading = false;
                error = null;
            };

            ws.onmessage = (event) => {
                try {
                    const parsed = JSON.parse(event.data);
                    data = parsed;
                    error = null;
                } catch (e) {
                    console.error("Failed to parse WebSocket message:", e);
                }
            };

            ws.onerror = () => {
                error = "WebSocket connection error";
                loading = false;
            };

            ws.onclose = (e) => {
                if (!e.wasClean) {
                    error = "WebSocket connection closed unexpectedly";
                }
                setTimeout(connectWebSocket, 3000);
            };
        } catch (e: any) {
            error = e.message || "Failed to connect WebSocket";
            loading = false;
        }
    }

    // ============================================================================
    // Formatting helpers
    // ============================================================================
    function formatFieldName(field: string): string {
        return field
            .replace(/_/g, " ")
            .replace(/([A-Z])/g, " $1")
            .trim()
            .split(" ")
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(" ");
    }

    function formatValue(val: any): string {
        if (val === null || val === undefined) return "-";
        if (typeof val === "boolean") return val ? "Yes" : "No";
        if (typeof val === "number") return val.toLocaleString();
        return String(val);
    }

    function isComplexValue(val: any): boolean {
        return Array.isArray(val) || (typeof val === "object" && val !== null);
    }

    function getInputType(val: any): string {
        if (typeof val === "number") return "number";
        if (typeof val === "boolean") return "checkbox";
        return "text";
    }

    // JSON edit state for complex fields
    let jsonEditErrors = $state<Record<string, string | null>>({});

    function handleJsonEdit(field: string, value: string) {
        try {
            editData[field] = JSON.parse(value);
            jsonEditErrors[field] = null;
        } catch (e) {
            jsonEditErrors[field] = "Invalid JSON";
        }
    }

    // ============================================================================
    // Lifecycle
    // ============================================================================
    onMount(() => {
        if (isWebSocketMode) {
            connectWebSocket();
        } else {
            fetchData();

            if (props.refreshMs && props.refreshMs > 0) {
                interval = setInterval(fetchData, props.refreshMs);
            }
        }
    });

    onDestroy(() => {
        if (interval) clearInterval(interval);
        if (ws) {
            ws.onclose = null;
            ws.close();
        }
    });
</script>

<Card fullWidth>
    {#snippet header()}
        <div class="card-header">
            <h3 class="card-title">{props.title || ""}</h3>
            <div class="header-actions">
                {#if editMode}
                    <button
                        class="icon-btn cancel"
                        onclick={cancelEdit}
                        disabled={saving}
                        title="Cancel"
                    >
                        <X size={16} />
                    </button>
                    <button
                        class="icon-btn save"
                        onclick={saveEdit}
                        disabled={saving}
                        title="Save"
                    >
                        <Check size={16} />
                    </button>
                {:else if !isWebSocketMode}
                    {#if canEdit}
                        <button
                            class="icon-btn edit"
                            onclick={enterEditMode}
                            disabled={loading || !data}
                            title="Edit"
                        >
                            <Pencil size={14} />
                        </button>
                    {/if}
                    <RefreshButton onRefresh={fetchData} {loading} />
                {:else}
                    <LiveIndicator connected={!error && !loading} size={10} />
                {/if}
            </div>
        </div>
    {/snippet}

    {#if loading}
        <div class="state-container">
            <EmptyState />
        </div>
    {:else if error && error.includes("401")}
        <div class="state-container">
            <UnauthorizedState />
        </div>
    {:else if error && !editMode}
        <div class="state-container">
            <ErrorState message={error} />
        </div>
    {:else if data}
        <div class="fields-container">
            {#if error && editMode}
                <div class="edit-error">{error}</div>
            {/if}
            {#each props.fields as field}
                {@const isHighlight = field === props.highlight}
                {@const readonly = isReadonly(field)}
                {@const isComplex = isComplexValue(data[field])}
                {#if isComplex}
                    <!-- Complex value (object/array) -->
                    <div class="field-block" class:readonly>
                        <div class="field-block-header">
                            <span class="field-label">{formatFieldName(field)}</span>
                            {#if readonly && editMode}
                                <span class="readonly-badge-inline" title="This field is read-only">
                                    <Lock size={12} />
                                </span>
                            {/if}
                        </div>
                        {#if editMode && !readonly}
                            <textarea
                                class="json-input"
                                class:json-error={jsonEditErrors[field]}
                                value={JSON.stringify(editData[field] ?? data[field], null, 2)}
                                oninput={(e) => handleJsonEdit(field, e.currentTarget.value)}
                                disabled={saving}
                                rows={5}
                            ></textarea>
                            {#if jsonEditErrors[field]}
                                <span class="json-error-msg">{jsonEditErrors[field]}</span>
                            {/if}
                        {:else}
                            <JSONResult data={data[field]} />
                        {/if}
                    </div>
                {:else}
                    <!-- Scalar value -->
                    {#if editMode && !readonly}
                        <div class="field-row" class:highlight={isHighlight}>
                            <label class="field-label">{formatFieldName(field)}</label>
                            {#if typeof data[field] === "boolean"}
                                <label class="checkbox-wrapper">
                                    <input
                                        type="checkbox"
                                        checked={editData[field] ?? data[field]}
                                        onchange={(e) => editData[field] = e.currentTarget.checked}
                                        disabled={saving}
                                    />
                                    <span>{editData[field] ?? data[field] ? "Yes" : "No"}</span>
                                </label>
                            {:else if typeof data[field] === "number"}
                                <input
                                    type="number"
                                    class="field-input"
                                    value={editData[field] ?? data[field]}
                                    oninput={(e) => editData[field] = parseFloat(e.currentTarget.value) || 0}
                                    disabled={saving}
                                />
                            {:else}
                                <input
                                    type="text"
                                    class="field-input"
                                    value={editData[field] ?? data[field] ?? ""}
                                    oninput={(e) => editData[field] = e.currentTarget.value}
                                    disabled={saving}
                                />
                            {/if}
                        </div>
                    {:else}
                        <KeyValue
                            label={formatFieldName(field)}
                            value={formatValue(data[field])}
                            class={isHighlight ? "highlight-row" : ""}
                        />
                    {/if}
                {/if}
            {/each}
        </div>
    {:else}
        <EmptyState />
    {/if}
</Card>

<style>
    .card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
    }

    .card-title {
        font-size: 1.125rem;
        font-weight: 500;
        color: var(--text);
    }

    .header-actions {
        display: flex;
        align-items: center;
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
        opacity: 0.5;
        cursor: not-allowed;
    }

    .icon-btn.edit:hover:not(:disabled) {
        border-color: var(--accent);
        color: var(--accent);
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

    .state-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.5rem;
        padding: 2rem 1rem;
    }

    .fields-container {
        display: flex;
        flex-direction: column;
    }

    .field-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        position: relative;
        width: 100%;
    }

    .field-row.highlight {
        background-color: var(--surface-secondary);
        border-radius: 4px;
        padding: 0.25rem 0.5rem;
    }

    .field-row.readonly {
        opacity: 0.7;
    }

    .field-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.03em;
        min-width: 100px;
    }

    .field-input {
        flex: 1;
        padding: 0.5rem;
        border: 1px solid var(--edge);
        border-radius: 4px;
        background: var(--surface);
        color: var(--text);
        font-size: 0.875rem;
    }

    .field-input:focus {
        outline: none;
        border-color: var(--accent);
    }

    .field-input:disabled {
        opacity: 0.6;
    }

    .checkbox-wrapper {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
    }

    .checkbox-wrapper input {
        width: 16px;
        height: 16px;
        cursor: pointer;
    }

    .readonly-badge {
        position: absolute;
        right: 0.25rem;
        color: var(--text-muted);
        opacity: 0.6;
    }

    .edit-error {
        padding: 0.5rem;
        border-radius: 4px;
        background: var(--red-tint, #fef2f2);
        color: var(--red-text, #dc2626);
        font-size: 0.8rem;
        margin-bottom: 0.5rem;
    }

    .field-block {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--edge);
    }

    .field-block:last-child {
        border-bottom: none;
    }

    .field-block.readonly {
        opacity: 0.7;
    }

    .field-block-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .readonly-badge-inline {
        color: var(--text-muted);
        opacity: 0.6;
    }

    .json-input {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid var(--edge);
        border-radius: 4px;
        background: var(--surface);
        color: var(--text);
        font-family: "Approach Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 0.75rem;
        resize: vertical;
        min-height: 80px;
    }

    .json-input:focus {
        outline: none;
        border-color: var(--accent);
    }

    .json-input:disabled {
        opacity: 0.6;
    }

    .json-input.json-error {
        border-color: var(--red-text, #dc2626);
    }

    .json-error-msg {
        font-size: 0.7rem;
        color: var(--red-text, #dc2626);
    }
</style>
