<script lang="ts">
    import { authStore } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import ThemeToggle from "$lib/components/ThemeToggle.svelte";

    const props = $props<{
        roles: string[];
        apiBase?: string;
    }>();

    // Form state
    let mode = $state<"login" | "register">("login");
    let loginId = $state("");
    let password = $state("");
    let confirmPassword = $state("");
    let selectedRole = $state<string>(props.roles[0] || "");
    let error = $state<string | null>(null);
    let success = $state<string | null>(null);
    let loading = $state(false);

    const apiBase = props.apiBase || "";

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
            const response = await fetch(`${apiBase}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    login_id: loginId.trim(),
                    password: password
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();

            // Update auth store with session info
            authStore.loginSession(data.user_id, data.roles);

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

        if (password.length < 6) {
            error = "Password must be at least 6 characters";
            return;
        }

        if (password !== confirmPassword) {
            error = "Passwords do not match";
            return;
        }

        if (!selectedRole) {
            error = "Please select a role";
            return;
        }

        loading = true;

        try {
            const response = await fetch(`${apiBase}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    login_id: loginId.trim(),
                    password: password,
                    role: selectedRole
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Registration failed' }));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            // Registration successful - switch to login mode
            success = "Registration successful! You can now log in.";
            password = "";
            confirmPassword = "";
            mode = "login";

        } catch (e: any) {
            error = e.message || "Failed to register";
        } finally {
            loading = false;
        }
    }

    function switchMode(newMode: "login" | "register") {
        mode = newMode;
        error = null;
        success = null;
        password = "";
        confirmPassword = "";
    }
</script>

<div class="login-container">
    <div class="theme-toggle-wrapper">
        <ThemeToggle />
    </div>
    <Card>
        <svelte:fragment slot="header">
            <div class="header-tabs">
                <button
                    class="tab-button"
                    class:active={mode === "login"}
                    onclick={() => switchMode("login")}
                >
                    Login
                </button>
                <button
                    class="tab-button"
                    class:active={mode === "register"}
                    onclick={() => switchMode("register")}
                >
                    Register
                </button>
            </div>
        </svelte:fragment>

        <div class="login-form">
            <!-- Login ID -->
            <div class="form-group">
                <label for="loginId" class="form-label">Login ID</label>
                <input
                    id="loginId"
                    type="text"
                    bind:value={loginId}
                    placeholder="Enter your login ID (email, username, etc.)"
                    class="form-input"
                    disabled={loading}
                />
            </div>

            <!-- Password -->
            <div class="form-group">
                <label for="password" class="form-label">Password</label>
                <input
                    id="password"
                    type="password"
                    bind:value={password}
                    placeholder={mode === "register" ? "Create a password (min 6 chars)" : "Enter your password"}
                    class="form-input"
                    disabled={loading}
                />
            </div>

            <!-- Confirm Password (register only) -->
            {#if mode === "register"}
                <div class="form-group">
                    <label for="confirmPassword" class="form-label">Confirm Password</label>
                    <input
                        id="confirmPassword"
                        type="password"
                        bind:value={confirmPassword}
                        placeholder="Confirm your password"
                        class="form-input"
                        disabled={loading}
                    />
                </div>

                <!-- Role Selection (register only) -->
                <div class="form-group">
                    <label class="form-label">Select Role</label>
                    <div class="roles-grid">
                        {#each props.roles as role}
                            <button
                                type="button"
                                class="role-button"
                                class:selected={selectedRole === role}
                                onclick={() => selectedRole = role}
                                disabled={loading}
                            >
                                <span class="role-radio">
                                    {#if selectedRole === role}
                                        <span class="radio-dot"></span>
                                    {/if}
                                </span>
                                <span class="role-name">{role}</span>
                            </button>
                        {/each}
                    </div>
                </div>
            {/if}

            <!-- Success Message -->
            {#if success}
                <div class="success-message">
                    {success}
                </div>
            {/if}

            <!-- Error Message -->
            {#if error}
                <div class="error-message">
                    {error}
                </div>
            {/if}

            <!-- Submit Button -->
            <button
                type="button"
                class="submit-button"
                onclick={mode === "login" ? handleLogin : handleRegister}
                disabled={loading}
            >
                {#if loading}
                    {mode === "login" ? "Logging in..." : "Registering..."}
                {:else}
                    {mode === "login" ? "Login" : "Create Account"}
                {/if}
            </button>

            <!-- Info Text -->
            <div class="info-text">
                <p class="info-title">Session-based authentication</p>
                <p class="info-desc">
                    {#if mode === "login"}
                        Your session is stored server-side. A cookie will be set to identify your session.
                    {:else}
                        Create an account to access protected resources. Your password will be securely hashed.
                    {/if}
                </p>
            </div>
        </div>
    </Card>
</div>

<style>
    .login-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 1rem;
        position: relative;
    }

    .theme-toggle-wrapper {
        position: absolute;
        top: 1rem;
        right: 1rem;
    }

    .header-tabs {
        display: flex;
        gap: 0;
        width: 100%;
    }

    .tab-button {
        flex: 1;
        padding: 0.75rem;
        border: none;
        background: transparent;
        color: var(--text-muted);
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        border-bottom: 2px solid transparent;
    }

    .tab-button:hover {
        color: var(--text);
    }

    .tab-button.active {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    .login-form {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
        max-width: 400px;
        width: 100%;
        padding-top: 0.5rem;
    }

    .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .form-label {
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--text);
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .form-input {
        padding: 0.75rem;
        border: 1px solid var(--edge);
        border-radius: 0.5rem;
        background: var(--surface);
        color: var(--text);
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

    .form-input::placeholder {
        color: var(--text-muted);
    }

    .roles-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 0.5rem;
    }

    .role-button {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 0.75rem;
        border: 1px solid var(--edge);
        border-radius: 0.5rem;
        background: var(--surface);
        color: var(--text);
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .role-button:hover:not(:disabled) {
        border-color: var(--accent);
    }

    .role-button.selected {
        border-color: var(--accent);
        background: var(--accent);
        color: white;
    }

    .role-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .role-radio {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 1rem;
        height: 1rem;
        border: 2px solid var(--edge);
        border-radius: 50%;
        flex-shrink: 0;
    }

    .role-button.selected .role-radio {
        border-color: white;
    }

    .radio-dot {
        width: 0.4rem;
        height: 0.4rem;
        background: white;
        border-radius: 50%;
    }

    .role-name {
        flex: 1;
        text-align: left;
        text-transform: capitalize;
    }

    .success-message {
        padding: 0.75rem;
        border-radius: 0.5rem;
        background: var(--green-tint);
        color: var(--green-text);
        font-size: 0.8rem;
        border: 1px solid var(--green-text);
    }

    .error-message {
        padding: 0.75rem;
        border-radius: 0.5rem;
        background: var(--red-tint);
        color: var(--red-text);
        font-size: 0.8rem;
        border: 1px solid var(--red-text);
    }

    .submit-button {
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

    .submit-button:hover:not(:disabled) {
        opacity: 0.9;
    }

    .submit-button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .info-text {
        padding: 0.75rem;
        border-radius: 0.5rem;
        background: var(--surface);
        border: 1px solid var(--edge-soft);
    }

    .info-title {
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--text);
        margin-bottom: 0.25rem;
    }

    .info-desc {
        font-size: 0.7rem;
        color: var(--text-muted);
        line-height: 1.4;
    }
</style>
