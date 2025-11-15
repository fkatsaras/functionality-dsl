const express = require("express");
const bodyParser = require("body-parser");
const { WebSocketServer } = require("ws");
const REST_PORT = 9500;
const app = express();
app.use(bodyParser.json());
const rand = (min, max) =>
  Math.round((Math.random() * (max - min) + min) * 10) / 10;

// Temperature bounds
const TEMP_FLOOR = 18; // AC target (cooling)
const TEMP_CEILING = 28; // Natural ambient ceiling

// sensor metadata
const sensors = [
  { id: "sensor1", name: "TempSensor-1", model: "TX100", port: 9601 },
  { id: "sensor2", name: "TempSensor-2", model: "TX200", port: 9602 },
  { id: "sensor3", name: "TempSensor-3", model: "TX300", port: 9603 },
  { id: "sensor4", name: "TempSensor-4", model: "TX400", port: 9604 },
];

// --- REST endpoint: list devices ---
app.get("/api/devices", (req, res) => res.json(sensors));
app.listen(REST_PORT, () =>
  console.log(`REST server running on http://dummyiot:${REST_PORT}`)
);

// --- WS servers: one per sensor ---
const wssMap = new Map();
const state = {};        // current readings
let acOn = false;        // global AC state

sensors.forEach((sensor) => {
  const wss = new WebSocketServer({ port: sensor.port });
  console.log(`WS for ${sensor.id} -> ws://dummyiot:${sensor.port}`);
  state[sensor.id] = {
    temp: rand(22, 26), // start somewhere in the middle
    hum: rand(40, 55),
  };
  wss.on("connection", (ws) => {
    console.log(`${sensor.id} connected`);
    const clients = wssMap.get(sensor.id) || new Set();
    clients.add(ws);
    wssMap.set(sensor.id, clients);
    ws.on("close", () => {
      clients.delete(ws);
      if (clients.size === 0) wssMap.delete(sensor.id);
    });
  });
});

// --- dummy AC toggle ---
app.post("/api/device/toggle/ac", (req, res) => {
  const { state: acState } = req.body;
  acOn = acState;
  console.log(`[DUMMY] A/C toggle: ${acState ? "ON (cooling)" : "OFF (rising)"}`);
  res.json({ ok: true, ac_state: acState });
});

// --- global synchronized tick ---
setInterval(() => {
  const now = Date.now();
  sensors.forEach((sensor) => {
    const s = state[sensor.id];
    
    if (acOn) {
      // AC is ON: temperature decreases toward floor
      if (s.temp > TEMP_FLOOR) {
        s.temp = Math.max(TEMP_FLOOR, s.temp - rand(0.2, 0.4));
      } else {
        // At floor, add tiny noise but stay near floor
        s.temp = TEMP_FLOOR + rand(-0.1, 0.1);
      }
    } else {
      // AC is OFF: temperature rises toward ceiling
      if (s.temp < TEMP_CEILING) {
        s.temp = Math.min(TEMP_CEILING, s.temp + rand(0.2, 0.4));
      } else {
        // At ceiling, add tiny noise but stay near ceiling
        s.temp = TEMP_CEILING + rand(-0.1, 0.1);
      }
    }
    
    // Humidity varies independently
    s.hum = rand(s.hum - 0.5, s.hum + 0.5);
    
    const frame = {
      id: sensor.id,
      temp: Math.round(s.temp * 10) / 10, // keep one decimal
      hum: Math.round(s.hum * 10) / 10,
      ts: now,
    };
    
    const clients = wssMap.get(sensor.id);
    if (clients) {
      for (const ws of clients) {
        try {
          ws.send(JSON.stringify(frame));
          console.log(`Sensor ${sensor.id} frame: ${JSON.stringify(frame)}`);
        } catch (err) {
          console.error(err);
        }
      }
    }
  });
}, 1500);
