import { authStore } from './stores/authStore';

type Listener = (data: any) => void;

type SocketState = {
    key: string;
    fullUrl: string;
    ws: WebSocket | null;
    listeners: Set<Listener>;
    refCount: number;
    reconnects: number;
    closedByUser: boolean;
    timer: any;
};

const sockets = new Map<string, SocketState>();

function resolveWs(raw: string) {
  if (!raw) return "";
  if (raw.startsWith("ws://") || raw.startsWith("wss://")) return raw;
  // IMPORTANT: path-only => let the browser use the current origin (localhost:5173).
  // Vite will proxy+upgrade to the backend.
  if (raw.startsWith("/")) return raw;

  if (raw.startsWith("http://"))  return "ws://"  + raw.slice(7);
  if (raw.startsWith("https://")) return "wss://" + raw.slice(8);

  return raw;
}

/**
 * Append authentication credentials to WebSocket URL as query parameter.
 * Browsers don't support custom headers for WebSocket, so we use query params.
 *
 * Auth type handling:
 * - JWT: Append token as ?token=xxx
 * - API Key (header): Append as ?token=xxx (browser workaround, backend accepts both)
 * - API Key (query): Append as ?{keyName}=xxx
 * - API Key (cookie): No URL modification needed (cookies sent automatically)
 * - Basic: Credentials are in header, not supported for browser WebSocket
 */
function appendAuthToUrl(url: string): string {
    const state = authStore.getState();
    const separator = url.includes('?') ? '&' : '?';

    // For JWT auth, append token as query parameter
    if (state.authType === 'jwt' && state.token) {
        return `${url}${separator}token=${encodeURIComponent(state.token)}`;
    }

    // For API key auth
    if (state.authType === 'apikey' && state.apiKey) {
        // Cookie-based: cookies are sent automatically by the browser
        if (state.apiKeyLocation === 'cookie') {
            return url;
        }

        // Query-based: use the configured query param name
        if (state.apiKeyLocation === 'query' && state.apiKeyHeader) {
            return `${url}${separator}${encodeURIComponent(state.apiKeyHeader)}=${encodeURIComponent(state.apiKey)}`;
        }

        // Header-based: browsers can't set custom headers for WebSocket
        // Use 'token' as fallback query param (backend accepts both)
        if (state.apiKeyLocation === 'header') {
            return `${url}${separator}token=${encodeURIComponent(state.apiKey)}`;
        }
    }

    // For Basic auth, cookies are sent automatically if using session-like flow
    // Pure Basic auth over WebSocket is not well-supported by browsers
    return url;
}

function connect(state: SocketState): string | undefined {
    if (state.refCount <= 0) return;

    try {
        // Append auth token to URL for authenticated WebSocket connections
        const urlWithAuth = appendAuthToUrl(state.fullUrl);
        state.ws = new WebSocket(urlWithAuth);

        // debugs
        state.ws.onopen = () => {
            state.reconnects = 0;
            for (const cb of state.listeners) {
                try { cb({ __meta: "open" }); } catch {}
            }
        };

        state.ws.onmessage = (ev) => {

            let msg: any = ev.data;
            if (typeof msg === "string") {
                console.debug("[socket][onmessage]", msg);
                try { msg = JSON.parse(msg); } catch { /* Ignore non JSON */ }
            }

            for (const cb of state.listeners) {
                try { cb(msg); } catch { /* Listener errors are isolated */ }
            }
        };

        state.ws.onclose = () => {
            state.ws = null;
            if (state.closedByUser || state.refCount <= 0) return;

            // simple capped backoff
            const delay = Math.min(5000, 300 * Math.pow(2, state.reconnects++));
            state.timer = setTimeout(() => connect(state), delay);
        };

        state.ws.onerror = () => {
            try { state.ws?.close(); } catch {}
        };

        state.reconnects = 0; // reset on successfull opening
    } catch {
        if (!state.closedByUser && state.refCount > 0) {
            const delay = Math.min(5000, 300 * Math.pow(2, state.reconnects++));

            state.timer = setTimeout(() => connect(state), delay)
        }
    }
}

function getOrCreate(rawUrl: string): SocketState {
    const full = resolveWs(rawUrl);
    const key = full; // one connection per resolved URL
    const existing = sockets.get(key);

    if (existing) return existing;

    const st: SocketState = {
        key,
        fullUrl: full,
        ws: null,
        listeners: new Set(),
        refCount: 0,
        reconnects: 0,
        closedByUser: false,
        timer: null,
    };
    sockets.set(key, st);
    return st;
}

/**
 * Subscribe to a WS url. Opens (or reuses) a shared connection.
 * Returns an unsubscribe function that decrements the ref count and
 * closes the ws when nobody is listening.
 */
export function subscribe(rawUrl: string, onData: Listener): () => void {
    const st = getOrCreate(rawUrl);
    st.listeners.add(onData);
    st.refCount++;

    if (!st.ws) {
        st.closedByUser = false;
        connect(st);
    }

    return () => {
        st.listeners.delete(onData);
        st.refCount--;
        if (st.refCount <= 0) {
            st.closedByUser = true;
            clearTimeout(st.timer);
            try {
                st.ws?.close();
            } catch {}

            st.ws = null;
            sockets.delete(st.key);
        }
    }
}

/**
 * Publish a message to a WebSocket url using the shared connection.
 * The connection must already be established via subscribe().
 */
export function publish(rawUrl: string, data: any): void {
    const full = resolveWs(rawUrl);
    const st = sockets.get(full);

    if (!st || !st.ws) {
        console.error(`[ws] Cannot publish to ${rawUrl}: no active connection. Call subscribe() first.`);
        return;
    }

    try {
        st.ws.send(JSON.stringify(data));
    } catch (err) {
        console.error(`[ws] Failed to publish to ${rawUrl}:`, err);
    }
}