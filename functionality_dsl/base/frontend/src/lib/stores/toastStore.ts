import { writable } from 'svelte/store';

export type ToastType = 'error' | 'warning' | 'success' | 'info';

export interface Toast {
    id: number;
    type: ToastType;
    title: string;
    message: string;
}

let nextId = 0;

function createToastStore() {
    const { subscribe, update } = writable<Toast[]>([]);

    function add(type: ToastType, title: string, message: string, durationMs = 5000) {
        const id = nextId++;
        update(toasts => [...toasts, { id, type, title, message }]);
        setTimeout(() => remove(id), durationMs);
    }

    function remove(id: number) {
        update(toasts => toasts.filter(t => t.id !== id));
    }

    return {
        subscribe,
        remove,
        error: (title: string, message: string) => add('error', title, message),
        warning: (title: string, message: string) => add('warning', title, message),
        success: (title: string, message: string) => add('success', title, message),
        info: (title: string, message: string) => add('info', title, message),
    };
}

export const toastStore = createToastStore();
