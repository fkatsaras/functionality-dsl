const fs = require("fs");
const path = require("path");
const { WebSocketServer } = require("ws");

const WS_PORT = 9700;
const FRAME_RATE_MS = 100; // 10 fps (100ms between frames)

// Path to image directory (mounted in container at /app/vidf1_33_000.y)
const IMAGE_DIR = path.join(__dirname, "vidf1_33_000.y");

console.log(`[CAMERA] Starting dummy camera feed server...`);
console.log(`[CAMERA] Image directory: ${IMAGE_DIR}`);

// Load all PNG files from the directory
let imageFiles = [];
try {
  const files = fs.readdirSync(IMAGE_DIR);
  imageFiles = files
    .filter((f) => f.endsWith(".png"))
    .sort() // Sort alphabetically to get sequential frames
    .map((f) => path.join(IMAGE_DIR, f));

  console.log(`[CAMERA] Found ${imageFiles.length} image files`);
  if (imageFiles.length === 0) {
    console.error(`[CAMERA] ERROR: No PNG files found in ${IMAGE_DIR}`);
    process.exit(1);
  }
} catch (err) {
  console.error(`[CAMERA] ERROR reading image directory:`, err);
  process.exit(1);
}

// Create WebSocket server
const wss = new WebSocketServer({ port: WS_PORT });
console.log(`[CAMERA] WebSocket server listening on ws://dummycamera:${WS_PORT}/camera/feed`);

const clients = new Set();
let currentFrameIndex = 0;

wss.on("connection", (ws) => {
  console.log(`[CAMERA] Client connected (total: ${clients.size + 1})`);
  clients.add(ws);

  ws.on("close", () => {
    clients.delete(ws);
    console.log(`[CAMERA] Client disconnected (remaining: ${clients.size})`);
  });

  ws.on("error", (err) => {
    console.error(`[CAMERA] WebSocket error:`, err);
    clients.delete(ws);
  });
});

// Stream frames to all connected clients
setInterval(() => {
  if (clients.size === 0) {
    return; // No clients, skip processing
  }

  // Get current frame file
  const frameFile = imageFiles[currentFrameIndex];

  try {
    // Read image as binary buffer
    const frameData = fs.readFileSync(frameFile);

    // Broadcast to all connected clients
    for (const client of clients) {
      try {
        if (client.readyState === 1) { // WebSocket.OPEN
          client.send(frameData); // Send raw binary data
        }
      } catch (err) {
        console.error(`[CAMERA] Error sending to client:`, err);
        clients.delete(client);
      }
    }

    console.log(
      `[CAMERA] Sent frame ${currentFrameIndex + 1}/${imageFiles.length} ` +
      `(${frameData.length} bytes) to ${clients.size} client(s)`
    );
  } catch (err) {
    console.error(`[CAMERA] Error reading frame file:`, err);
  }

  // Move to next frame (loop back to start)
  currentFrameIndex = (currentFrameIndex + 1) % imageFiles.length;
}, FRAME_RATE_MS);

// Graceful shutdown
process.on("SIGINT", () => {
  console.log(`\n[CAMERA] Shutting down...`);
  wss.close();
  process.exit(0);
});
