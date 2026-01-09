import { writable, get } from 'svelte/store';

export type AuthType = 'jwt' | 'session';

export interface AuthState {
    authType: AuthType;
    token: string | null;      // For JWT auth
    userId: string | null;
    roles: string[];
    isAuthenticated: boolean;
}

const STORAGE_KEY = 'fdsl_auth';

// Initialize from localStorage if available (JWT) or check session (Session)
function getInitialState(): AuthState {
    const defaultState: AuthState = {
        authType: 'jwt',
        token: null,
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
                isAuthenticated: !!(parsed.token || parsed.userId)
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
         * Login with session (server sets cookie, we just store user info)
         */
        loginSession: (userId: string, roles: string[]) => {
            const state: AuthState = {
                authType: 'session',
                token: null,  // Session auth doesn't use tokens
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
         * Legacy login method (for backwards compatibility with JWT)
         */
        login: (token: string, userId: string, roles: string[]) => {
            const state: AuthState = {
                authType: 'jwt',
                token,
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
         * Logout - clears local state (for session auth, also call server logout)
         */
        logout: async () => {
            const currentState = get({ subscribe });

            // For session auth, call the server logout endpoint
            if (currentState.authType === 'session') {
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
