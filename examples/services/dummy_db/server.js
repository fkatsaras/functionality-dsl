const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = 9000;

// --- In-memory user storage ---
let users = [
  { id: 1, username: "dummy1", password: "dummypass1", email: "dummy@email.com" },
  { id: 2, username: "dummy2", password: "dummypass2", email: "dummy2@email.com" },
  { id: 3, username: "dummy3", password: "dummypass3", email: "dummy3@email.com" },
];

app.use(bodyParser.json());

// Helper for random IDs
function generateId() {
  return Math.floor(Math.random() * 9000) + 1000;
}

// Register new user (POST)
app.post("/db/users/register", (req, res) => {
  const data = req.body.user || req.body;
  if (!data.username || !data.email || !data.password) {
    return res.status(400).json({ ok: false, message: "Missing user fields" });
  }

  const newUser = {
    id: generateId(),
    username: data.username,
    password: data.password,
    email: data.email,
  };
  users.push(newUser);

  console.log(`[DUMMY] Registered new user: ${newUser.username}`);
  res.json({ ok: true, message: "User registered (dummy)", user: newUser });
});

// Get all users (GET)
app.get("/db/users", (req, res) => {
  res.json(users);
});

// Login (POST)
app.post("/db/users/login", (req, res) => {
  const { username, password } = req.body;
  const match = users.find(
    (u) => u.username === username && u.password === password
  );
  if (!match) {
    return res
      .status(401)
      .json({ ok: false, message: "Invalid credentials (dummy)" });
  }

  const token = `${match.username}-dummy-token`;
  console.log(`[DUMMY] Login successful for ${username}`);
  res.json({ ok: true, token });
});

// Forgot password (POST) — record reset request
let resetRequests = [];

app.post("/db/users/forgot-password", (req, res) => {
  const { email } = req.body;
  const user = users.find((u) => u.email === email);
  if (!user) {
    return res.status(404).json({ ok: false, message: "Email not found" });
  }

  const token = Buffer.from(`${email}-${Date.now()}`).toString("base64");
  resetRequests.push({ email, token });
  console.log(`[DUMMY] Forgot password request for ${email} (token ${token})`);

  res.json({
    ok: true,
    message: "Password reset request recorded (dummy)",
    token,
  });
});

// Reset password (PUT) — actually updates stored user
app.put("/db/users/reset-password", (req, res) => {
  const { email, newPassword } = req.body;
  const user = users.find((u) => u.email === email);
  if (!user) {
    return res.status(404).json({ ok: false, message: "User not found" });
  }

  user.password = newPassword;
  console.log(`[DUMMY] Password reset for ${email}`);

  res.json({
    ok: true,
    message: `Password updated for ${email} (dummy)`,
    user,
  });
});

// Update user (PATCH)
app.patch("/db/users/:id", (req, res) => {
  const id = parseInt(req.params.id);
  const user = users.find((u) => u.id === id);
  if (!user) {
    return res.status(404).json({ ok: false, message: "User not found" });
  }

  const { email, password } = req.body;
  if (email) user.email = email;
  if (password) user.password = password;

  console.log(`[DUMMY] Updated user ${id}`);
  res.json({ ok: true, message: `User ${id} updated`, user });
});


// Delete user (DELETE)
app.delete("/db/users/:id", (req, res) => {
  const id = parseInt(req.params.id);
  const before = users.length;
  users = users.filter((u) => u.id !== id);

  if (users.length === before) {
    return res.status(404).json({ ok: false, message: "User not found" });
  }

  console.log(`[DUMMY] Deleted user ${id}`);
  res.json({ ok: true, message: `User ${id} deleted` });
});



app.listen(PORT, () => {
  console.log(`Dummy DB running on http://localhost:${PORT}`);
});

