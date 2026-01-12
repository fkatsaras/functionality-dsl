<script lang="ts">
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";

    const props = $props<{
        roles: string[];
        apiBase?: string;
    }>();

    let userId = $state("");
    let selectedRoles = $state<string[]>([]);
    let error = $state<string | null>(null);
    let loading = $state(false);

    const apiBase = props.apiBase || "";

    function toggleRole(role: string) {
        if (selectedRoles.includes(role)) {
            selectedRoles = selectedRoles.filter(r => r !== role);
        } else {
            selectedRoles = [...selectedRoles, role];
        }
    }

    async function handleLogin() {
        error = null;

        if (!userId.trim()) {
            error = "User ID is required";
            return;
        }

        if (selectedRoles.length === 0) {
            error = "Please select at least one role";
            return;
        }

        loading = true;

        try {
            // Call the server login endpoint
            const response = await fetch(`${apiBase}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',  // Include cookies in request/response
                body: JSON.stringify({
                    user_id: userId.trim(),
                    roles: selectedRoles
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            // Update auth store with session info (no token needed - cookie is set by server)
            authStore.loginSession(data.user_id, data.roles);

        } catch (e: any) {
            error = e.message || "Failed to login";
        } finally {
            loading = false;
        }
    }

    async function handleLogout() {
        loading = true;
        try {
            await authStore.logout();
        } finally {
            loading = false;
        }
    }
</script>

<div class="login-container">
    <Card>
        <svelte:fragment slot="header">
            <h2 class="text-xl font-semibold">Session Login</h2>
        </svelte:fragment>

        <div class="login-form">
            <div class="form-group">
                <label for="userId" class="form-label">User ID</label>
                <input
                    id="userId"
                    type="text"
                    bind:value={userId}
                    placeholder="Enter your user ID"
                    class="form-input"
                    disabled={loading}
                />
            </div>

            <div class="form-group">
                <label class="form-label">Roles</label>
                <div class="roles-grid">
                    {#each props.roles as role}
                        <button
                            type="button"
                            class="role-button"
                            class:selected={selectedRoles.includes(role)}
                            onclick={() => toggleRole(role)}
                            disabled={loading}
                        >
                            <span class="role-checkbox">
                                {#if selectedRoles.includes(role)}✓{/if}
                            </span>
                            <span class="role-name">{role}</span>
                        </button>
                    {/each}
                </div>
            </div>

            {#if error}
                <div class="error-message">
                    {error}
                </div>
            {/if}

            <button
                type="button"
                class="login-button"
                onclick={handleLogin}
                disabled={loading}
            >
                {loading ? "Logging in..." : "Login"}
            </button>

            <div class="info-text">
                <p class="text-sm text-[var(--text-muted)]">
                    Session-based authentication
                </p>
                <p class="text-xs text-[var(--text-muted)] mt-2">
                    Your session is stored server-side. A cookie will be set to identify your session.
                </p>
            </div>
        </div>
    </Card>
</div>

<style>
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 1rem;
    }

    .login-form {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        max-width: 400px;
        width: 100%;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .form-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--text-primary);
    }

    .form-input {
        padding: 0.75rem;
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        background: var(--bg-primary);
        color: var(--text-primary);
        font-size: 0.875rem;
        transition: border-color 0.2s;
    }

    .form-input:focus {
        outline: none;
        border-color: var(--accent);
    }

    .form-input:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .roles-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 0.75rem;
    }

    .role-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem;
        border: 2px solid var(--border);
        border-radius: 0.5rem;
        background: var(--bg-primary);
        color: var(--text-primary);
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .role-button:hover:not(:disabled) {
        border-color: var(--accent);
        background: var(--bg-secondary);
    }

    .role-button.selected {
        border-color: var(--accent);
        background: var(--accent-light);
    }

    .role-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .role-checkbox {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 1.25rem;
        height: 1.25rem;
        border: 2px solid var(--border);
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: bold;
        color: var(--accent);
    }

    .role-button.selected .role-checkbox {
        border-color: var(--accent);
        background: var(--accent);
        color: white;
    }

    .role-name {
        flex: 1;
        text-align: left;
        text-transform: capitalize;
    }

    .error-message {
        padding: 0.75rem;
        border-radius: 0.5rem;
        background: var(--red-bg);
        color: var(--red-text);
        font-size: 0.875rem;
    }

    .login-button {
        padding: 0.875rem;
        border: none;
        border-radius: 0.5rem;
        background: var(--accent);
        color: white;
        font-size: 0.875rem;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.2s;
    }

    .login-button:hover:not(:disabled) {
        opacity: 0.9;
    }

    .login-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .info-text {
        padding: 0.75rem;
        border-radius: 0.5rem;
        background: var(--bg-secondary);
    }
</style>
