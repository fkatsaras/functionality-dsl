<script lang="ts">
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";

    const props = $props<{
        roles: string[];
        apiUrl?: string;
    }>();

    type AuthMode = 'login' | 'register';

    let mode = $state<AuthMode>('login');
    let loginId = $state("");
    let password = $state("");
    let confirmPassword = $state("");
    let selectedRole = $state(props.roles[0] || "user");
    let error = $state<string | null>(null);
    let success = $state<string | null>(null);
    let loading = $state(false);

    // Use relative URLs - Vite proxy handles forwarding to backend
    // VITE_API_URL is for server-side proxy config, not browser requests
    const baseUrl = props.apiUrl || "";

    function switchMode(newMode: AuthMode) {
        mode = newMode;
        error = null;
        success = null;
        password = "";
        confirmPassword = "";
    }

    async function handleLogin() {
        error = null;
        success = null;

        if (!loginId.trim()) {
            error = "Login ID is required";
            return;
        }

        if (!password) {
            error = "Password is required";
            return;
        }

        loading = true;

        try {
            const response = await fetch(`${baseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    login_id: loginId.trim(),
                    password: password,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }

            // Decode token to get user info
            const tokenPayload = parseJWT(data.access_token);
            const roles = tokenPayload.roles || [];
            const userId = tokenPayload.sub || loginId.trim();

            authStore.loginJWT(data.access_token, userId, roles);
            success = "Login successful!";
        } catch (e: any) {
            error = e.message || "Failed to login";
        } finally {
            loading = false;
        }
    }

    async function handleRegister() {
        error = null;
        success = null;

        if (!loginId.trim()) {
            error = "Login ID is required";
            return;
        }

        if (!password) {
            error = "Password is required";
            return;
        }

        if (password.length < 8) {
            error = "Password must be at least 8 characters";
            return;
        }

        if (password !== confirmPassword) {
            error = "Passwords do not match";
            return;
        }

        loading = true;

        try {
            const response = await fetch(`${baseUrl}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    login_id: loginId.trim(),
                    password: password,
                    role: selectedRole,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Registration failed');
            }

            success = "Registration successful! Please login.";
            password = "";
            confirmPassword = "";
            mode = 'login';
        } catch (e: any) {
            error = e.message || "Failed to register";
        } finally {
            loading = false;
        }
    }

    function parseJWT(token: string): any {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
                atob(base64)
                    .split('')
                    .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                    .join('')
            );
            return JSON.parse(jsonPayload);
        } catch {
            return {};
        }
    }

    function handleSubmit() {
        if (mode === 'login') {
            handleLogin();
        } else {
            handleRegister();
        }
    }
</script>

<div class="login-container">
    <Card>
        <svelte:fragment slot="header">
            <div class="auth-tabs">
                <button
                    type="button"
                    class="tab-button"
                    class:active={mode === 'login'}
                    onclick={() => switchMode('login')}
                >
                    Login
                </button>
                <button
                    type="button"
                    class="tab-button"
                    class:active={mode === 'register'}
                    onclick={() => switchMode('register')}
                >
                    Register
                </button>
            </div>
        </svelte:fragment>

        <form class="login-form" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
            <div class="form-group">
                <label for="loginId" class="form-label">
                    {mode === 'login' ? 'Email or Username' : 'Email'}
                </label>
                <input
                    id="loginId"
                    type="text"
                    bind:value={loginId}
                    placeholder={mode === 'login' ? "Enter your email or username" : "Enter your email"}
                    class="form-input"
                    disabled={loading}
                    autocomplete="username"
                />
            </div>

            <div class="form-group">
                <label for="password" class="form-label">Password</label>
                <input
                    id="password"
                    type="password"
                    bind:value={password}
                    placeholder={mode === 'register' ? "Min 8 characters" : "Enter your password"}
                    class="form-input"
                    disabled={loading}
                    autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
            </div>

            {#if mode === 'register'}
                <div class="form-group">
                    <label for="confirmPassword" class="form-label">Confirm Password</label>
                    <input
                        id="confirmPassword"
                        type="password"
                        bind:value={confirmPassword}
                        placeholder="Confirm your password"
                        class="form-input"
                        disabled={loading}
                        autocomplete="off"
                    />
                </div>

                <div class="form-group">
                    <label class="form-label">Register as</label>
                    <div class="roles-grid">
                        {#each props.roles as role}
                            <button
                                type="button"
                                class="role-button"
                                class:selected={selectedRole === role}
                                onclick={() => selectedRole = role}
                                disabled={loading}
                            >
                                <span class="role-checkbox">
                                    {#if selectedRole === role}✓{/if}
                                </span>
                                <span class="role-name">{role}</span>
                            </button>
                        {/each}
                    </div>
                </div>
            {/if}

            {#if error}
                <div class="error-message">
                    {error}
                </div>
            {/if}

            {#if success}
                <div class="success-message">
                    {success}
                </div>
            {/if}

            <button
                type="submit"
                class="login-button"
                disabled={loading}
            >
                {#if loading}
                    {mode === 'login' ? "Logging in..." : "Registering..."}
                {:else}
                    {mode === 'login' ? "Login" : "Register"}
                {/if}
            </button>
        </form>
    </Card>
</div>

<style>
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 1rem;
        font-family: "Approach Mono", monospace;
    }

    .auth-tabs {
        display: flex;
        gap: 0.5rem;
    }

    .tab-button {
        flex: 1;
        padding: 0.75rem 1rem;
        border: none;
        border-radius: 0.5rem;
        background: var(--bg-secondary);
        color: var(--text-muted);
        font-family: "Approach Mono", monospace;
        font-size: 0.875rem;
        font-weight: 500;
        letter-spacing: 0.02em;
        cursor: pointer;
        transition: all 0.2s;
    }

    .tab-button:hover {
        background: var(--bg-tertiary);
    }

    .tab-button.active {
        background: var(--accent);
        color: white;
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
        font-family: "Approach Mono", monospace;
        font-size: 0.875rem;
        font-weight: 500;
        letter-spacing: 0.02em;
        color: var(--text-primary);
    }

    .form-input {
        padding: 0.75rem;
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        background: var(--bg-primary);
        color: var(--text-primary);
        font-family: "Approach Mono", monospace;
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
        font-family: "Approach Mono", monospace;
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
        font-family: "Approach Mono", monospace;
        font-size: 0.875rem;
    }

    .success-message {
        padding: 0.75rem;
        border-radius: 0.5rem;
        background: var(--green-tint);
        color: var(--green-text);
        font-family: "Approach Mono", monospace;
        font-size: 0.875rem;
    }

    .login-button {
        padding: 0.875rem;
        border: none;
        border-radius: 0.5rem;
        background: var(--accent);
        color: white;
        font-family: "Approach Mono", monospace;
        font-size: 0.875rem;
        font-weight: 500;
        letter-spacing: 0.02em;
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
</style>
