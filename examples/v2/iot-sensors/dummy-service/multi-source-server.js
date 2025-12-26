const { WebSocketServer } = require("ws");

const rand = (min, max) =>
  Math.round((Math.random() * (max - min) + min) * 10) / 10;

// Shared sensor locations
const locations = ["room-1", "room-2", "room-3"];

// Current state for each location
const state = {};
locations.forEach((loc) => {
  state[loc] = {
    temperature: rand(68, 75), // Fahrenheit
    humidity: rand(40, 60),    // Percentage
  };
});

console.log("=".repeat(70));
console.log("MULTI-SOURCE SENSOR GATEWAY");
console.log("=".repeat(70));

// --- Temperature WebSocket Server (port 9001/temperature) ---
const tempWss = new WebSocketServer({ port: 9001 });
const tempClients = new Set();

console.log("✓ Temperature WS: ws://localhost:9001 (path: /temperature)");

tempWss.on("connection", (ws) => {
  console.log("[TEMP] Client connected");
  tempClients.add(ws);

  ws.on("close", () => {
    tempClients.delete(ws);
    console.log("[TEMP] Client disconnected");
  });

  ws.on("error", (err) => {
    console.error("[TEMP] WebSocket error:", err);
  });
});

// --- Humidity WebSocket Server (port 9002/humidity) ---
const humWss = new WebSocketServer({ port: 9002 });
const humClients = new Set();

console.log("✓ Humidity WS: ws://localhost:9002 (path: /humidity)");

humWss.on("connection", (ws) => {
  console.log("[HUM] Client connected");
  humClients.add(ws);

  ws.on("close", () => {
    humClients.delete(ws);
    console.log("[HUM] Client disconnected");
  });

  ws.on("error", (err) => {
    console.error("[HUM] WebSocket error:", err);
  });
});

console.log("=".repeat(70));
console.log("Emitting sensor data every 2 seconds...");
console.log("=".repeat(70));

// --- Emit sensor readings ---
setInterval(() => {
  const timestamp = new Date().toISOString();

  locations.forEach((locationId, idx) => {
    const sensorId = `sensor-${idx + 1}`;
    const s = state[locationId];

    // Simulate temperature drift
    s.temperature += rand(-0.5, 0.5);
    s.temperature = Math.max(65, Math.min(85, s.temperature)); // Keep in range

    // Simulate humidity drift
    s.humidity += rand(-1, 1);
    s.humidity = Math.max(30, Math.min(70, s.humidity)); // Keep in range

    // Send TEMPERATURE reading to temperature WS
    const tempReading = {
      sensorId,
      locationId,
      temperature: Math.round(s.temperature * 10) / 10,
      timestamp,
    };

    tempClients.forEach((ws) => {
      try {
        ws.send(JSON.stringify(tempReading));
      } catch (err) {
        console.error("[TEMP] Send error:", err);
      }
    });

    // Send HUMIDITY reading to humidity WS (slightly offset for realism)
    setTimeout(() => {
      const humReading = {
        sensorId,
        locationId,
        humidity: Math.round(s.humidity * 10) / 10,
        timestamp,
      };

      humClients.forEach((ws) => {
        try {
          ws.send(JSON.stringify(humReading));
        } catch (err) {
          console.error("[HUM] Send error:", err);
        }
      });

      console.log(
        `[${locationId}] T: ${tempReading.temperature}°F, H: ${humReading.humidity}%`
      );
    }, 500); // 500ms offset between temp and humidity
  });
}, 2000); // Emit every 2 seconds
