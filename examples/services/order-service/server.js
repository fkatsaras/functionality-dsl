const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = 8002;

// --- In-memory order storage ---
let orders = [
  {
    orderId: "ord-001",
    userId: "user-001",
    status: "delivered",
    total: 129.99,
    createdAt: "2025-10-15T10:30:00Z",
    items: [
      { productId: "prod-101", name: "Laptop Bag", price: 49.99, quantity: 1 },
      { productId: "prod-102", name: "Wireless Mouse", price: 29.99, quantity: 2 },
      { productId: "prod-103", name: "USB-C Cable", price: 19.99, quantity: 1 },
    ],
  },
  {
    orderId: "ord-002",
    userId: "user-001",
    status: "shipped",
    total: 599.99,
    createdAt: "2025-10-28T14:22:00Z",
    items: [
      { productId: "prod-201", name: "Mechanical Keyboard", price: 159.99, quantity: 1 },
      { productId: "prod-202", name: "Monitor Stand", price: 89.99, quantity: 1 },
      { productId: "prod-203", name: "Webcam HD", price: 79.99, quantity: 1 },
      { productId: "prod-204", name: "Headphones", price: 269.99, quantity: 1 },
    ],
  },
  {
    orderId: "ord-003",
    userId: "user-001",
    status: "pending",
    total: 45.50,
    createdAt: "2025-11-05T09:15:00Z",
    items: [
      { productId: "prod-301", name: "Screen Cleaner", price: 12.99, quantity: 1 },
      { productId: "prod-302", name: "Cable Organizer", price: 15.99, quantity: 2 },
    ],
  },
  {
    orderId: "ord-004",
    userId: "user-002",
    status: "delivered",
    total: 899.99,
    createdAt: "2025-09-20T16:45:00Z",
    items: [
      { productId: "prod-401", name: "Gaming Chair", price: 399.99, quantity: 1 },
      { productId: "prod-402", name: "Desk Lamp", price: 89.99, quantity: 1 },
      { productId: "prod-403", name: "Footrest", price: 49.99, quantity: 1 },
      { productId: "prod-404", name: "Monitor Arm", price: 129.99, quantity: 1 },
      { productId: "prod-405", name: "Mouse Pad", price: 29.99, quantity: 1 },
      { productId: "prod-406", name: "Wrist Rest", price: 19.99, quantity: 1 },
    ],
  },
  {
    orderId: "ord-005",
    userId: "user-002",
    status: "pending",
    total: 199.99,
    createdAt: "2025-11-08T11:30:00Z",
    items: [
      { productId: "prod-501", name: "External SSD 1TB", price: 119.99, quantity: 1 },
      { productId: "prod-502", name: "USB Hub", price: 39.99, quantity: 2 },
    ],
  },
  {
    orderId: "ord-006",
    userId: "user-003",
    status: "shipped",
    total: 1249.97,
    createdAt: "2025-10-10T08:00:00Z",
    items: [
      { productId: "prod-601", name: "Laptop", price: 1199.99, quantity: 1 },
      { productId: "prod-602", name: "Laptop Sleeve", price: 24.99, quantity: 1 },
      { productId: "prod-603", name: "USB-C Adapter", price: 24.99, quantity: 1 },
    ],
  },
  {
    orderId: "ord-007",
    userId: "user-004",
    status: "delivered",
    total: 349.95,
    createdAt: "2025-09-15T13:20:00Z",
    items: [
      { productId: "prod-701", name: "Office Chair", price: 299.99, quantity: 1 },
      { productId: "prod-702", name: "Cushion", price: 24.99, quantity: 2 },
    ],
  },
];

app.use(bodyParser.json());

// Enable CORS for development
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  next();
});

// Get all orders (no filtering - dumb data source)
app.get("/orders", (_req, res) => {
  console.log(`[ORDER-SERVICE] Returning all ${orders.length} orders`);
  res.json(orders);
});

// Get order by ID (GET /orders/:orderId)
app.get("/orders/:orderId", (req, res) => {
  const orderId = req.params.orderId;
  const order = orders.find((o) => o.orderId === orderId);

  if (!order) {
    return res.status(404).json({ error: "Order not found" });
  }

  console.log(`[ORDER-SERVICE] Fetched order: ${orderId}`);
  res.json(order);
});

app.listen(PORT, () => {
  console.log(`Order Service running on http://localhost:${PORT}`);
  console.log(`Total orders: ${orders.length}`);
  const userOrders = {};
  orders.forEach((o) => {
    userOrders[o.userId] = (userOrders[o.userId] || 0) + 1;
  });
  console.log(`Orders by user:`, userOrders);
});
