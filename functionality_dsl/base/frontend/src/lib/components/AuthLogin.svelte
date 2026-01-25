<script lang="ts">
    import { authStore, type APIKeyLocation } from "$lib/stores/authStore";
    import Card from "$lib/primitives/Card.svelte";
    import ThemeToggle from "$lib/components/ThemeToggle.svelte";

    /**
     * Auth mechanism configuration
     * Each auth mechanism has a type, name, roles, and optional config
     *
     * Types:
     * - jwt: Bearer token (JWT) in Authorization header
     * - basic: HTTP Basic auth
     * - apikey: API key in header, query, or cookie
     */
    interface AuthMechanism {
        type: "jwt" | "apikey" | "basic";
        name: string;
        roles: string[];
        header?: string;           // Key/header name for apikey
        location?: APIKeyLocation; // "header" | "query" | "cookie" for apikey
    }

    const props = $props<{
        authMechanisms: AuthMechanism[];
        apiBase?: string;
    }>();

    // Determine which auth types are available
    const hasJWT = $derived(props.authMechanisms.some(a => a.type === "jwt"));
    const hasBasic = $derived(props.authMechanisms.some(a => a.type === "basic"));
    const hasAPIKey = $derived(props.authMechanisms.some(a => a.type === "apikey"));

    // Check if there's a non-cookie apikey (for optional "I have a key" tab)
    const hasAPIKeyManual = $derived(props.authMechanisms.some(a => a.type === "apikey" && a.location !== "cookie"));

    // All auth types support credential-based login (register/login flow)
    // The auth type determines how credentials are validated and tokens are returned
    const hasCredentialAuth = $derived(hasJWT || hasBasic || hasAPIKey);

    // Primary auth type for determining login behavior
    // Priority: jwt > apikey > basic
    const credentialAuthType = $derived(
        hasJWT ? "jwt" : hasAPIKey ? "apikey" : hasBasic ? "basic" : null
    );

    // ALL roles from ALL auth mechanisms - unified registration
    // Role determines what you can access, auth mechanism determines how credentials are transported
    const allRoles = $derived(
        props.authMechanisms
            .flatMap(a => a.roles || [])
            .filter((r, i, arr) => arr.indexOf(r) === i)
    );

    // For manual API key entry tab (optional "I already have a key" flow)
    const apiKeyConfig = $derived(
        props.authMechanisms.find(a => a.type === "apikey" && a.location !== "cookie") ||
        props.authMechanisms.find(a => a.type === "apikey")
    );
    const apiKeyHeader = $derived(apiKeyConfig?.header || "X-API-Key");
    const apiKeyLocation = $derived(apiKeyConfig?.location || "header");

    // UI State
    type AuthTab = "credentials" | "apikey";
    type CredentialMode = "login" | "register";

    let activeTab = $state<AuthTab>("credentials");
    let credentialMode = $state<CredentialMode>("login");

    // Form fields
    let loginId = $state("");
    let password = $state("");
    let confirmPassword = $state("");
    let selectedRole = $state<string>("");
    let apiKey = $state("");

    // Status
    let error = $state<string | null>(null);
    let success = $state<string | null>(null);
    let loading = $state(false);

    const apiBase = props.apiBase || "";

    // Initialize selected role when allRoles becomes available
    $effect(() => {
        if (allRoles.length > 0 && !selectedRole) {
            selectedRole = allRoles[0];
        }
    });

    // Initialize active tab based on available auth types
    $effect(() => {
        // Only show API key tab as default if there's manual apikey (header/query) and no credential auth
        if (!hasCredentialAuth && hasAPIKeyManual) {
            activeTab = "apikey";
        }
    });

    /**
     * Decode JWT token payload (without verification - that happens server-side)
     * Extracts user_id (sub claim) and roles from the token
     */
    function decodeJWT(token: string): { sub: string; roles: string[] } | null {
        try {
            const parts = token.split('.');
            if (parts.length !== 3) return null;

            // Decode base64url payload (handle URL-safe base64)
            const payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
            const decoded = JSON.parse(atob(payload));

            return {
                sub: decoded.sub || decoded.user_id || '',
                roles: Array.isArray(decoded.roles) ? decoded.roles :
                       decoded.roles ? [decoded.roles] : []
            };
        } catch {
            return null;
        }
    }

    /**
     * Parse error detail from FastAPI/Pydantic validation errors.
     * Handles both string errors and array of validation error objects.
     */
    function parseErrorDetail(detail: unknown): string {
        if (typeof detail === 'string') {
            return detail;
        }
        if (Array.isArray(detail)) {
            return detail
                .map(err => {
                    if (typeof err === 'object' && err !== null) {
                        const msg = (err as any).msg || (err as any).message || JSON.stringify(err);
                        const loc = (err as any).loc;
                        if (Array.isArray(loc) && loc.length > 1) {
                            return `${loc.slice(1).join('.')}: ${msg}`;
                        }
                        return msg;
                    }
                    return String(err);
                })
                .join('; ');
        }
        if (typeof detail === 'object' && detail !== null) {
            return (detail as any).message || (detail as any).msg || JSON.stringify(detail);
        }
        return String(detail);
    }

    function switchTab(tab: AuthTab) {
        activeTab = tab;
        error = null;
        success = null;
    }

    function switchCredentialMode(mode: CredentialMode) {
        credentialMode = mode;
        error = null;
        success = null;
        password = "";
        confirmPassword = "";
    }

    async function handleCredentialLogin() {
        error = null;
        success = null;

        if (!loginId.trim()) {
            error = credentialAuthType === "basic" ? "Username is required" : "Login ID is required";
            return;
        }

        if (!password) {
            error = "Password is required";
            return;
        }

        loading = true;

        try {
            if (credentialAuthType === "basic") {
                // Basic auth - validate by making a test request
                const credentials = btoa(`${loginId.trim()}:${password}`);
                const response = await fetch(`${apiBase}/api/`, {
                    method: 'GET',
                    headers: { 'Authorization': `Basic ${credentials}` }
                });

                if (response.status === 401) {
                    throw new Error('Invalid username or password');
                }

                // For basic auth, use declared roles since server doesn't return them
                authStore.loginBasic(loginId.trim(), password, allRoles);
            } else {
                // JWT and API key auth use the login endpoint
                const response = await fetch(`${apiBase}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',  // Important for cookie-based apikey
                    body: JSON.stringify({
                        login_id: loginId.trim(),
                        password: password
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
                    throw new Error(parseErrorDetail(errorData.detail) || `HTTP ${response.status}`);
                }

                const data = await response.json();

                if (credentialAuthType === "jwt" && data.access_token) {
                    // JWT: decode the token to extract user_id and roles
                    const decoded = decodeJWT(data.access_token);
                    if (decoded) {
                        authStore.loginJWT(data.access_token, decoded.sub || loginId.trim(), decoded.roles);
                    } else {
                        // Fallback if decoding fails - shouldn't happen with valid tokens
                        console.warn('Failed to decode JWT token');
                        authStore.loginJWT(data.access_token, loginId.trim(), []);
                    }
                } else if (credentialAuthType === "apikey" && data.api_key) {
                    // API key auth: server returns api_key, location, key_name, and user info
                    // For cookie-based apikey, server already set the cookie via Set-Cookie header
                    // For header/query-based apikey, we store it for manual injection
                    const keyLocation = (data.location || apiKeyLocation) as APIKeyLocation;
                    const keyName = data.key_name || apiKeyHeader;

                    // Extract actual user role from server response
                    // Server returns user.role (string) or roles (array)
                    const userRoles: string[] = data.roles
                        ? (Array.isArray(data.roles) ? data.roles : [data.roles])
                        : data.user?.role
                            ? [data.user.role]
                            : [];

                    // Store the API key with its location and ACTUAL user roles
                    authStore.loginAPIKey(data.api_key, keyName, loginId.trim(), userRoles, keyLocation);
                }
            }

        } catch (e: any) {
            error = e.message || "Failed to login";
        } finally {
            loading = false;
        }
    }

    async function handleCredentialRegister() {
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

        if (!selectedRole) {
            error = "Please select a role";
            return;
        }

        loading = true;

        try {
            const response = await fetch(`${apiBase}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    login_id: loginId.trim(),
                    password: password,
                    role: selectedRole
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Registration failed' }));
                throw new Error(parseErrorDetail(errorData.detail) || `HTTP ${response.status}`);
            }

            success = "Registration successful! You can now log in.";
            password = "";
            confirmPassword = "";
            credentialMode = "login";

        } catch (e: any) {
            error = e.message || "Failed to register";
        } finally {
            loading = false;
        }
    }

    async function handleAPIKeyLogin() {
        error = null;
        success = null;

        if (!apiKey.trim()) {
            error = "API Key is required";
            return;
        }

        loading = true;

        try {
            // For manual API key entry, store the key directly
            // Role verification happens server-side on each request
            // Manual entry is only for header/query based apikey (not cookie)
            authStore.loginAPIKey(apiKey.trim(), apiKeyHeader, "api-user", allRoles, apiKeyLocation as APIKeyLocation);
        } catch (e: any) {
            error = e.message || "Failed to set API key";
        } finally {
            loading = false;
        }
    }
</script>

<div class="login-container">
    <div class="theme-toggle-wrapper">
        <ThemeToggle />
    </div>
    <div class="card-wrapper">
    <Card>
        <svelte:fragment slot="header">
            {#if hasCredentialAuth && hasAPIKeyManual}
                <!-- Show tabs when both credential auth AND manual API key entry are available -->
                <div class="auth-tabs">
                    <button
                        class="auth-tab"
                        class:active={activeTab === "credentials"}
                        onclick={() => switchTab("credentials")}
                    >
                        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
                        </svg>
                        <span>User Login</span>
                    </button>
                    <button
                        class="auth-tab"
                        class:active={activeTab === "apikey"}
                        onclick={() => switchTab("apikey")}
                    >
                        <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" />
                        </svg>
                        <span>API Key</span>
                    </button>
                </div>
            {:else}
                <div class="single-auth-header">
                    <h2 class="auth-title">
                        {#if hasCredentialAuth}
                            Sign In
                        {:else}
                            API Key Authentication
                        {/if}
                    </h2>
                </div>
            {/if}
        </svelte:fragment>

        <div class="login-form">
            <!-- Credential-based auth (JWT/Basic/APIKey) -->
            {#if activeTab === "credentials" && hasCredentialAuth}
                <!-- Login/Register toggle for session/jwt -->
                {#if credentialAuthType !== "basic"}
                    <div class="mode-tabs">
                        <button
                            class="mode-tab"
                            class:active={credentialMode === "login"}
                            onclick={() => switchCredentialMode("login")}
                        >
                            Login
                        </button>
                        <button
                            class="mode-tab"
                            class:active={credentialMode === "register"}
                            onclick={() => switchCredentialMode("register")}
                        >
                            Register
                        </button>
                    </div>
                {/if}

                <!-- Login ID -->
                <div class="form-group">
                    <label for="loginId" class="form-label">
                        {credentialAuthType === "basic" ? "Username" : "Login ID"}
                    </label>
                    <input
                        id="loginId"
                        type="text"
                        bind:value={loginId}
                        placeholder={credentialAuthType === "basic" ? "Enter your username" : "Enter your login ID"}
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
                        placeholder={credentialMode === "register" ? "Create a password (min 8 chars)" : "Enter your password"}
                        class="form-input"
                        disabled={loading}
                    />
                </div>

                <!-- Confirm Password (register only) -->
                {#if credentialMode === "register"}
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
                    {#if allRoles.length > 0}
                        <div class="form-group">
                            <label class="form-label">Select Role</label>
                            <div class="roles-grid">
                                {#each allRoles as role}
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
                {/if}

                <!-- Submit Button -->
                <button
                    type="button"
                    class="submit-button"
                    onclick={credentialMode === "login" ? handleCredentialLogin : handleCredentialRegister}
                    disabled={loading}
                >
                    {#if loading}
                        {credentialMode === "login" ? "Logging in..." : "Registering..."}
                    {:else}
                        {credentialMode === "login" ? "Login" : "Create Account"}
                    {/if}
                </button>

            <!-- API Key auth (manual entry for header/query based) -->
            {:else if activeTab === "apikey" && hasAPIKeyManual}
                <div class="form-group">
                    <label for="apiKey" class="form-label">API Key</label>
                    <input
                        id="apiKey"
                        type="password"
                        bind:value={apiKey}
                        placeholder="Enter your API key"
                        class="form-input"
                        disabled={loading}
                    />
                    <p class="form-hint">{apiKeyLocation === "header" ? "Header" : "Query param"}: {apiKeyHeader}</p>
                </div>

                {#if allRoles.length > 0}
                    <div class="roles-info">
                        <span class="roles-label">Available roles:</span>
                        <span class="roles-list">{allRoles.join(", ")}</span>
                    </div>
                {/if}

                <button
                    type="button"
                    class="submit-button"
                    onclick={handleAPIKeyLogin}
                    disabled={loading}
                >
                    {loading ? "Validating..." : "Authenticate"}
                </button>
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

            <!-- Info Text -->
            <div class="info-text">
                {#if activeTab === "credentials"}
                    <p class="info-title">
                        {credentialAuthType === "jwt" ? "Token-based" : credentialAuthType === "apikey" ? "API Key" : "Basic"} authentication
                    </p>
                    <p class="info-desc">
                        {#if credentialMode === "login"}
                            {#if credentialAuthType === "jwt"}
                                A JWT token will be issued and stored locally for API authentication.
                            {:else if credentialAuthType === "apikey"}
                                {#if apiKeyLocation === "cookie"}
                                    An API key will be set as a cookie for seamless authentication.
                                {:else}
                                    An API key will be issued for {apiKeyLocation}-based authentication.
                                {/if}
                            {:else}
                                Credentials are validated with each request using HTTP Basic auth.
                            {/if}
                        {:else}
                            Create an account to access protected resources. Your password will be securely hashed.
                        {/if}
                    </p>
                {:else}
                    <p class="info-title">API Key authentication</p>
                    <p class="info-desc">
                        Enter your API key to authenticate. The key will be sent with each request in the <code>{apiKeyHeader}</code> {apiKeyLocation}.
                    </p>
                {/if}
            </div>
        </div>
    </Card>
    </div>
</div>

<style>
    .login-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 2rem 1rem;
        position: relative;
    }

    .theme-toggle-wrapper {
        position: absolute;
        top: 1rem;
        right: 1rem;
    }

    .card-wrapper {
        width: 100%;
        max-width: 380px;
    }

    .card-wrapper :global(.card) {
        max-width: 380px;
        margin: 0 auto;
    }

    .auth-tabs {
        display: flex;
        gap: 0;
        width: 100%;
    }

    .auth-tab {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.75rem;
        border: none;
        background: transparent;
        color: var(--text-muted);
        font-size: 0.85rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        border-bottom: 2px solid transparent;
    }

    .auth-tab:hover {
        color: var(--text);
    }

    .auth-tab.active {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    .tab-icon {
        width: 1.25rem;
        height: 1.25rem;
    }

    .single-auth-header {
        padding: 0.75rem;
        text-align: center;
    }

    .auth-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
    }

    .mode-tabs {
        display: flex;
        gap: 0;
        background: var(--surface);
        border-radius: 0.5rem;
        padding: 0.25rem;
        border: 1px solid var(--edge);
    }

    .mode-tab {
        flex: 1;
        padding: 0.5rem 1rem;
        border: none;
        background: transparent;
        color: var(--text-muted);
        font-size: 0.8rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        border-radius: 0.375rem;
    }

    .mode-tab:hover {
        color: var(--text);
    }

    .mode-tab.active {
        background: var(--accent);
        color: white;
    }

    .login-form {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
        max-width: 360px;
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

    .form-hint {
        font-size: 0.7rem;
        color: var(--text-muted);
        margin: 0;
    }

    .roles-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
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

    .roles-info {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        padding: 0.75rem;
        background: var(--surface);
        border-radius: 0.5rem;
        border: 1px solid var(--edge);
    }

    .roles-label {
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    .roles-list {
        font-size: 0.8rem;
        color: var(--text);
        font-weight: 500;
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
        margin: 0;
    }

    .info-desc code {
        background: var(--edge);
        padding: 0.1rem 0.3rem;
        border-radius: 0.25rem;
        font-size: 0.65rem;
    }
</style>
