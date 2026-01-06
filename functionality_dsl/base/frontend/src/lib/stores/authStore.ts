import { writable } from 'svelte/store';

export interface AuthState {
    token: string | null;
    userId: string | null;
    roles: string[];
}

const STORAGE_KEY = 'fdsl_auth';

// Initialize from localStorage if available
function getInitialState(): AuthState {
    if (typeof window === 'undefined') {
        return { token: null, userId: null, roles: [] };
    }

    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
        try {
            return JSON.parse(stored);
        } catch {
            return { token: null, userId: null, roles: [] };
        }
    }

    return { token: null, userId: null, roles: [] };
}

function createAuthStore() {
    const { subscribe, set, update } = writable<AuthState>(getInitialState());

    return {
        subscribe,
        login: (token: string, userId: string, roles: string[]) => {
            const state = { token, userId, roles };
            set(state);
            if (typeof window !== 'undefined') {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
            }
        },
        logout: () => {
            const state = { token: null, userId: null, roles: [] };
            set(state);
            if (typeof window !== 'undefined') {
                localStorage.removeItem(STORAGE_KEY);
            }
        },
        hasRole: (role: string): boolean => {
            let currentRoles: string[] = [];
            subscribe(state => {
                currentRoles = state.roles;
            })();
            return currentRoles.includes(role);
        },
        hasAnyRole: (roles: string[]): boolean => {
            let currentRoles: string[] = [];
            subscribe(state => {
                currentRoles = state.roles;
            })();
            return roles.some(role => currentRoles.includes(role) || role === 'public');
        }
    };
}

export const authStore = createAuthStore();
