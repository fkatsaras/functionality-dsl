const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = 8001;

// --- In-memory user storage ---
let users = [
  { id: "user-001", email: "alice@example.com", name: "Alice Johnson" },
  { id: "user-002", email: "bob@example.com", name: "Bob Smith" },
  { id: "user-003", email: "carol@example.com", name: "Carol Williams" },
  { id: "user-004", email: "david@example.com", name: "David Brown" },
];

app.use(bodyParser.json());

// Enable CORS for development
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  next();
});

// Get user by ID (GET /users/:userId)
app.get("/users/:userId", (req, res) => {
  const userId = req.params.userId;
  const user = users.find((u) => u.id === userId);

  if (!user) {
    return res.status(404).json({ error: "User not found" });
  }

  console.log(`[USER-SERVICE] Fetched user: ${userId}`);
  res.json(user);
});

// Get all users (GET /users)
app.get("/users", (req, res) => {
  console.log(`[USER-SERVICE] Fetched all users`);
  res.json(users);
});

app.listen(PORT, () => {
  console.log(`User Service running on http://localhost:${PORT}`);
  console.log(`Available users: ${users.map(u => u.id).join(", ")}`);
});
