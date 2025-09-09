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

function connect(state: SocketState): string | undefined {
    if (state.refCount <= 0) return;

    try {
        state.ws = new WebSocket(state.fullUrl);

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