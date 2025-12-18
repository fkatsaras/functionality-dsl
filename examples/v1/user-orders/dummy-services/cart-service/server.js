const express = require("express");
const WebSocket = require("ws");
const app = express();
const PORT = 9002;
const WS_PORT = 9003;

app.use(express.json());

// Enable CORS
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, DELETE");
  res.header("Access-Control-Allow-Headers", "Content-Type, X-Session-ID");
  next();
});

// --- In-memory cart storage (session-based) ---
const carts = new Map();

// Helper to get cart for session
function getCart(sessionId) {
  if (!carts.has(sessionId)) {
    carts.set(sessionId, {
      sessionId,
      items: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });
  }
  return carts.get(sessionId);
}

// POST /cart/add - Add item to cart
app.post("/cart/add", (req, res) => {
  const sessionId = req.headers["x-session-id"] || "default-session";
  const { productId, productName, price, quantity } = req.body;

  if (!productId || !productName || !price || !quantity) {
    return res.status(400).json({
      error: "productId, productName, price, and quantity required"
    });
  }

  const cart = getCart(sessionId);

  // Check if item already exists
  const existingItem = cart.items.find(item => item.productId === productId);

  if (existingItem) {
    existingItem.quantity += quantity;
  } else {
    cart.items.push({
      productId,
      productName,
      price,
      quantity,
      addedAt: new Date().toISOString()
    });
  }

  cart.updatedAt = new Date().toISOString();

  console.log(`[CART-SERVICE] Added to cart ${sessionId}: ${productName} x${quantity}`);

  // Broadcast cart update via WebSocket
  broadcastCartUpdate(sessionId, cart);

  res.json(cart);
});

// GET /cart - Get cart for session
app.get("/cart", (req, res) => {
  const sessionId = req.headers["x-session-id"] || "default-session";
  const cart = getCart(sessionId);

  console.log(`[CART-SERVICE] Fetched cart ${sessionId}: ${cart.items.length} items`);
  res.json(cart);
});

// DELETE /cart/items/:productId - Remove item from cart
app.delete("/cart/items/:productId", (req, res) => {
  const sessionId = req.headers["x-session-id"] || "default-session";
  const { productId } = req.params;

  const cart = getCart(sessionId);
  cart.items = cart.items.filter(item => item.productId !== productId);
  cart.updatedAt = new Date().toISOString();

  console.log(`[CART-SERVICE] Removed from cart ${sessionId}: ${productId}`);

  // Broadcast cart update via WebSocket
  broadcastCartUpdate(sessionId, cart);

  res.json(cart);
});

app.listen(PORT, () => {
  console.log(`Cart Service (REST) running on http://localhost:${PORT}`);
});

// ============================================
// WebSocket Server for Real-Time Cart Updates
// ============================================
// PER-SESSION MODE: Clients subscribe with sessionId, receive only THEIR updates
// This mirrors real-world cart APIs (secure & efficient)

const wss = new WebSocket.Server({ port: WS_PORT });
const sessions = new Map(); // sessionId -> WebSocket

wss.on("connection", (ws, req) => {
  let sessionId = null;

  console.log("[CART-WS] Client connected");

  ws.on("message", (message) => {
    try {
      const messageStr = message.toString();

      // Parse subscription message (can be plain string or JSON wrapper)
      let receivedSessionId;
      try {
        const data = JSON.parse(messageStr);
        // Support wrapper entity format: {"value": "session1"}
        receivedSessionId = data.value || data.sessionId || data;
      } catch {
        // Plain string session ID
        receivedSessionId = messageStr.replace(/^"|"$/g, '');
      }

      if (receivedSessionId) {
        sessionId = receivedSessionId;
        sessions.set(sessionId, ws);

        console.log(`[CART-WS] Session ${sessionId} subscribed`);

        // Send current cart state immediately
        const cart = getCart(sessionId);
        ws.send(JSON.stringify({
          type: "cart_update",
          sessionId,
          cart,
          itemCount: cart.items.length,
          total: cart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0),
          timestamp: new Date().toISOString()
        }));
      }
    } catch (err) {
      console.error("[CART-WS] Error parsing subscription message:", err);
    }
  });

  ws.on("close", () => {
    if (sessionId) {
      sessions.delete(sessionId);
      console.log(`[CART-WS] Session ${sessionId} disconnected`);
    }
  });

  ws.on("error", (err) => {
    console.error("[CART-WS] WebSocket error:", err);
  });
});

// Helper to send cart update to specific subscribed session
function broadcastCartUpdate(sessionId, cart) {
  const ws = sessions.get(sessionId);
  if (ws && ws.readyState === WebSocket.OPEN) {
    const message = JSON.stringify({
      type: "cart_update",
      sessionId,
      cart,
      itemCount: cart.items.length,
      total: cart.items.reduce((sum, item) => sum + (item.price * item.quantity), 0),
      timestamp: new Date().toISOString()
    });

    console.log(`[CART-WS] Sending update to session ${sessionId}`);
    ws.send(message);
  }
}

console.log(`Cart WebSocket Service running on ws://localhost:${WS_PORT}`);
console.log(`PER-SESSION MODE: Clients send sessionId to subscribe to their cart updates`);
