<script lang="ts">
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";

    const props = $props<{
        secret: string;
        roles: string[];
    }>();

    let userId = $state("");
    let selectedRoles = $state<string[]>([]);
    let error = $state<string | null>(null);
    let loading = $state(false);

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
            // Generate JWT token client-side
            const token = await generateToken(userId.trim(), selectedRoles);
            authStore.login(token, userId.trim(), selectedRoles);
        } catch (e: any) {
            error = e.message || "Failed to generate token";
        } finally {
            loading = false;
        }
    }

    async function generateToken(userId: string, roles: string[]): Promise<string> {
        // Create JWT payload
        const now = Math.floor(Date.now() / 1000);
        const payload = {
            sub: userId,
            roles: roles,
            iat: now,
            exp: now + 3600  // 1 hour expiration
        };

        // Encode JWT using simple base64 encoding (HS256 simulation)
        // NOTE: This is a simplified client-side JWT for demo purposes
        // In production, tokens should be generated server-side
        const header = { alg: "HS256", typ: "JWT" };

        const base64UrlEncode = (obj: any) => {
            const json = JSON.stringify(obj);
            const base64 = btoa(json);
            return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
        };

        const headerEncoded = base64UrlEncode(header);
        const payloadEncoded = base64UrlEncode(payload);

        // For client-side demo, we'll use a simple signature
        // In production, this would use proper HMAC-SHA256 with the secret
        const signatureData = `${headerEncoded}.${payloadEncoded}`;
        const signature = await createSignature(signatureData, props.secret);

        return `${headerEncoded}.${payloadEncoded}.${signature}`;
    }

    async function createSignature(data: string, secret: string): Promise<string> {
        // Use Web Crypto API to create HMAC-SHA256 signature
        const encoder = new TextEncoder();
        const key = await crypto.subtle.importKey(
            "raw",
            encoder.encode(secret),
            { name: "HMAC", hash: "SHA-256" },
            false,
            ["sign"]
        );

        const signature = await crypto.subtle.sign(
            "HMAC",
            key,
            encoder.encode(data)
        );

        // Convert to base64url
        const base64 = btoa(String.fromCharCode(...new Uint8Array(signature)));
        return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
    }
</script>

<div class="login-container">
    <Card>
        <svelte:fragment slot="header">
            <h2 class="text-xl font-semibold">Login</h2>
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
                {loading ? "Generating Token..." : "Login"}
            </button>

            <div class="info-text">
                <p class="text-sm text-[var(--text-muted)]">
                    JWT Secret: <code>{props.secret}</code>
                </p>
                <p class="text-xs text-[var(--text-muted)] mt-2">
                    This generates a JWT token client-side for demo purposes.
                    In production, tokens should be issued by your auth server.
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

    code {
        padding: 0.125rem 0.375rem;
        border-radius: 0.25rem;
        background: var(--bg-tertiary);
        font-family: 'Courier New', monospace;
        font-size: 0.8125rem;
    }
</style>
