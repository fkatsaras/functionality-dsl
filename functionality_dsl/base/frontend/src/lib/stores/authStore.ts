import { writable, get } from 'svelte/store';

export type AuthType = 'jwt' | 'apikey' | 'basic';
export type APIKeyLocation = 'header' | 'query' | 'cookie';

export interface AuthState {
    authType: AuthType;
    token: string | null;           // For JWT auth (and Basic auth base64 credentials)
    apiKey: string | null;          // For API key auth
    apiKeyHeader: string | null;    // Header/query/cookie name for API key
    apiKeyLocation: APIKeyLocation | null;  // Where to send the API key
    userId: string | null;
    roles: string[];
    isAuthenticated: boolean;
}

const STORAGE_KEY = 'fdsl_auth';

// Initialize from localStorage if available
function getInitialState(): AuthState {
    const defaultState: AuthState = {
        authType: 'jwt',
        token: null,
        apiKey: null,
        apiKeyHeader: null,
        apiKeyLocation: null,
        userId: null,
        roles: [],
        isAuthenticated: false
    };

    if (typeof window === 'undefined') {
        return defaultState;
    }

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
        try {
            const parsed = JSON.parse(stored);
            return {
                ...defaultState,
                ...parsed,
                isAuthenticated: !!(parsed.token || parsed.userId || parsed.apiKey)
            };
        } catch {
            return defaultState;
        }
    }

    return defaultState;
}

function createAuthStore() {
    const { subscribe, set, update } = writable<AuthState>(getInitialState());

    return {
        subscribe,

        /**
         * Set the authentication type (jwt or session)
         */
        setAuthType: (authType: AuthType) => {
            update(state => ({ ...state, authType }));
        },

        /**
         * Login with JWT token (client-side token storage)
         */
        loginJWT: (token: string, userId: string, roles: string[]) => {
            const state: AuthState = {
                authType: 'jwt',
                token,
                apiKey: null,
                apiKeyHeader: null,
                apiKeyLocation: null,
                userId,
                roles,
                isAuthenticated: true
            };
            set(state);
            if (typeof window !== 'undefined') {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
            }
        },

        /**
         * Login with API key (store key for header/query injection, or just track for cookie)
         * @param apiKey - The API key value
         * @param keyName - The header name, query param name, or cookie name
         * @param userId - User identifier
         * @param roles - User roles
         * @param location - Where the key is sent: "header", "query", or "cookie"
         */
        loginAPIKey: (apiKey: string, keyName: string, userId: string, roles: string[], location: APIKeyLocation = 'header') => {
            const state: AuthState = {
                authType: 'apikey',
                token: null,
                apiKey,
                apiKeyHeader: keyName,
                apiKeyLocation: location,
                userId,
                roles,
                isAuthenticated: true
            };
            set(state);
            if (typeof window !== 'undefined') {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
            }
        },

        /**
         * Login with HTTP Basic auth (store base64-encoded credentials)
         * Basic auth is stateless - credentials are sent with every request
         */
        loginBasic: (username: string, password: string, roles: string[]) => {
            // Encode credentials as base64 for the Authorization header
            const credentials = btoa(`${username}:${password}`);
            const state: AuthState = {
                authType: 'basic',
                token: credentials,  // Store base64 encoded credentials in token field
                apiKey: null,
                apiKeyHeader: null,
                apiKeyLocation: null,
                userId: username,
                roles,
                isAuthenticated: true
            };
            set(state);
            if (typeof window !== 'undefined') {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
            }
        },

        /**
         * Legacy login method (for backwards compatibility with JWT)
         */
        login: (token: string, userId: string, roles: string[]) => {
            const state: AuthState = {
                authType: 'jwt',
                token,
                apiKey: null,
                apiKeyHeader: null,
                apiKeyLocation: null,
                userId,
                roles,
                isAuthenticated: true
            };
            set(state);
            if (typeof window !== 'undefined') {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
            }
        },

        /**
         * Logout - clears local state
         * For cookie-based API key auth, also clears the cookie via server endpoint
         */
        logout: async () => {
            const currentState = get({ subscribe });

            // For cookie-based apikey auth, call server logout to clear the cookie
            if (currentState.authType === 'apikey' && currentState.apiKeyLocation === 'cookie') {
                try {
                    await fetch('/auth/logout', {
                        method: 'POST',
                        credentials: 'include'  // Include cookies
                    });
                } catch (e) {
                    console.error('Logout request failed:', e);
                }
            }

            const state: AuthState = {
                authType: currentState.authType,
                token: null,
                apiKey: null,
                apiKeyHeader: null,
                apiKeyLocation: null,
                userId: null,
                roles: [],
                isAuthenticated: false
            };
            set(state);
            if (typeof window !== 'undefined') {
                localStorage.removeItem(STORAGE_KEY);
            }
        },

        /**
         * Check if user has a specific role
         */
        hasRole: (role: string): boolean => {
            const state = get({ subscribe });
            return state.roles.includes(role);
        },

        /**
         * Check if user has any of the specified roles
         */
        hasAnyRole: (roles: string[]): boolean => {
            const state = get({ subscribe });
            return roles.some(role => state.roles.includes(role) || role === 'public');
        },

        /**
         * Get the current auth state
         */
        getState: (): AuthState => {
            return get({ subscribe });
        }
    };
}

export const authStore = createAuthStore();
