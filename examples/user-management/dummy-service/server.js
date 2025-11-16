const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = 9000;

// --- In-memory user storage ---
let users = [
  { id: 1, username: "alice", password: "pass123", email: "alice@example.com" },
  { id: 2, username: "bob", password: "pass456", email: "bob@example.com" },
  { id: 3, username: "charlie", password: "pass789", email: "charlie@example.com" },
];

let nextId = 4;

app.use(bodyParser.json());

// ============================================================
// GET /db/users - Read all users
// ============================================================
app.get("/db/users", (req, res) => {
  console.log(`[DUMMY] GET /db/users`);
  res.json({ users });
});

// ============================================================
// POST /db/users - Write user (just append to array)
// ============================================================
app.post("/db/users", (req, res) => {
  console.log(`[DUMMY] POST /db/users`);
  const newUser = { ...req.body, id: nextId++ };
  users.push(newUser);
  res.json({ ok: true, user: newUser });
});

// ============================================================
// PUT /db/users - Replace entire user list
// ============================================================
app.put("/db/users", (req, res) => {
  console.log(`[DUMMY] PUT /db/users`);
  users = req.body.users || req.body;
  res.json({ ok: true, users });
});

app.listen(PORT, () => {
  console.log(`Dummy DB running on http://localhost:${PORT}`);
  console.log(`Endpoints:`);
  console.log(`  GET  /db/users - Read all users`);
  console.log(`  POST /db/users - Append new user`);
  console.log(`  PUT  /db/users - Replace user list`);
});
