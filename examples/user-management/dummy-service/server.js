const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = 9000;

// --- In-memory user storage (simple DB) ---
let users = [
  { id: 1, username: "alice", password: "pass123", email: "alice@example.com" },
  { id: 2, username: "bob", password: "secret456", email: "bob@example.com" },
  { id: 3, username: "charlie", password: "hello789", email: "charlie@example.com" },
];

let nextId = 4;

app.use(bodyParser.json());

// ====== SIMPLE CRUD OPERATIONS (No business logic) ======

// GET /db/users - List all users
app.get("/db/users", (req, res) => {
  console.log(`[DB] GET /db/users - Returning ${users.length} users`);
  res.json({ users });
});

// GET /db/users/:id - Get single user
app.get("/db/users/:id", (req, res) => {
  const id = parseInt(req.params.id);
  const user = users.find((u) => u.id === id);

  if (!user) {
    console.log(`[DB] GET /db/users/${id} - Not found`);
    return res.status(404).json({ error: "User not found" });
  }

  console.log(`[DB] GET /db/users/${id} - Found ${user.username}`);
  res.json(user);
});

// POST /db/users - Create new user
app.post("/db/users", (req, res) => {
  const { username, password, email } = req.body;

  if (!username || !password || !email) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const newUser = {
    id: nextId++,
    username,
    password,
    email,
  };

  users.push(newUser);
  console.log(`[DB] POST /db/users - Created user ${newUser.id}: ${username}`);
  res.status(201).json(newUser);
});

// PATCH /db/users/:id - Update user
app.patch("/db/users/:id", (req, res) => {
  const id = parseInt(req.params.id);
  const user = users.find((u) => u.id === id);

  if (!user) {
    console.log(`[DB] PATCH /db/users/${id} - Not found`);
    return res.status(404).json({ error: "User not found" });
  }

  const { username, email, password } = req.body;
  if (username !== undefined) user.username = username;
  if (email !== undefined) user.email = email;
  if (password !== undefined) user.password = password;

  console.log(`[DB] PATCH /db/users/${id} - Updated ${user.username}`);
  res.json(user);
});

// DELETE /db/users/:id - Delete user
app.delete("/db/users/:id", (req, res) => {
  const id = parseInt(req.params.id);
  const index = users.findIndex((u) => u.id === id);

  if (index === -1) {
    console.log(`[DB] DELETE /db/users/${id} - Not found`);
    return res.status(404).json({ error: "User not found" });
  }

  const deleted = users.splice(index, 1)[0];
  console.log(`[DB] DELETE /db/users/${id} - Deleted ${deleted.username}`);
  res.json({ ok: true, message: `User ${id} deleted` });
});

app.listen(PORT, () => {
  console.log(`[DB] User database running on http://localhost:${PORT}`);
  console.log(`[DB] Initial users: ${users.length}`);
});
