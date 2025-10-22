const express = require("express");
const bodyParser = require("body-parser");

const app = express();
const PORT = 9100;


app.use(bodyParser.json());


// ----------------- In memory stores --------------------------

let users = [
    { id: 1, username: "alice", email: "alice@shop.com", password: "pass123", role: "customer", createdAt: Date.now() - 86400000 * 30 },
    { id: 2, username: "bob", email: "bob@shop.com", password: "pass456", role: "customer", createdAt: Date.now() - 86400000 * 15 },
    { id: 3, username: "admin", email: "admin@shop.com", password: "admin123", role: "admin", createdAt: Date.now() - 86400000 * 60 },
];

let products = [
    { id: 101, name: "Laptop", description: "High-performance laptop", price: 999.99, stock: 15, category: "electronics", createdAt: Date.now() - 86400000 * 20 },
    { id: 102, name: "Mouse", description: "Wireless mouse", price: 29.99, stock: 50, category: "electronics", createdAt: Date.now() - 86400000 * 18 },
    { id: 103, name: "Keyboard", description: "Mechanical keyboard", price: 79.99, stock: 30, category: "electronics", createdAt: Date.now() - 86400000 * 15 },
    { id: 104, name: "Monitor", description: "27-inch 4K monitor", price: 399.99, stock: 10, category: "electronics", createdAt: Date.now() - 86400000 * 10 },
    { id: 105, name: "Desk Chair", description: "Ergonomic office chair", price: 249.99, stock: 8, category: "furniture", createdAt: Date.now() - 86400000 * 5 },
];

let orders = [
  {
    id: 1001,
    userId: 1,
    items: [{ productId: 102, quantity: 1, price: 29.99 }],
    total: 29.99,
    status: "delivered",
    createdAt: Date.now() - 86400000 * 7,
    shippingAddress: "123 Main St, City, Country"
  },
  {
    id: 1002,
    userId: 2,
    items: [{ productId: 101, quantity: 1, price: 999.99 }],
    total: 999.99,
    status: "shipped",
    createdAt: Date.now() - 86400000 * 2,
    shippingAddress: "456 Oak Ave, Town, Country"
  },
];

let carts = [
  { id: 1, userId: 1, items: [{ productId: 101, quantity: 1 }, { productId: 102, quantity: 2 }], createdAt: Date.now() - 3600000 },
  { id: 2, userId: 2, items: [{ productId: 103, quantity: 1 }], createdAt: Date.now() - 7200000 },
];

let reviews = [
  { id: 501, productId: 101, userId: 1, rating: 5, comment: "Excellent laptop!", createdAt: Date.now() - 86400000 * 5 },
  { id: 502, productId: 102, userId: 2, rating: 4, comment: "Good mouse, works well", createdAt: Date.now() - 86400000 * 3 },
  { id: 503, productId: 101, userId: 2, rating: 5, comment: "Best purchase ever!", createdAt: Date.now() - 86400000 * 1 },
];

let wishlist = [
  { userId: 1, productIds: [104, 105] },
  { userId: 2, productIds: [103, 104] },
];


// Helpers
function generateId() {
    return Math.floor(Math.random() * 90000) + 10000;
}

function findById(array, id) {
    return array.find(item => item.id === parseInt(id));
}

// --------- User Endpoints -----------
app.get("/db/users", (req, res) => {
    console.log("[DUMMY] GET /db/users");
    return res.json(users);
});

app.get("/db/users/:id", (req, res) => {
    const user = findById(users, req.params.id);
    if (!user) return res.status(404).json({ error: "User not found" });
    
    console.log(`[DUMMY] GET /db/users/${req.params.id}`);
    res.json(user);
});

app.post("/db/users/register", (req, res) => {
  const { username, email, password, role } = req.body;
  if (!username || !email || !password) {
    return res.status(400).json({ error: "Missing required fields" });
  }
  
  const newUser = {
    id: generateId(),
    username,
    email,
    password,
    role: role || "customer",
    createdAt: Date.now()
  };
  users.push(newUser);
  console.log(`[DUMMY] POST /db/users/register - Created user: ${username}`);
  res.json({ ok: true, user: newUser });
});

app.post("/db/users/login", (req, res) => {
  const { username, password } = req.body;
  const user = users.find(u => u.username === username && u.password === password);
  if (!user) {
    return res.status(401).json({ error: "Invalid credentials" });
  }
  const token = `${user.username}-token-${Date.now()}`;
  console.log(`[DUMMY] POST /db/users/login - User logged in: ${username}`);
  res.json({ ok: true, token, userId: user.id });
});

// ============================================================================
//                           PRODUCT ENDPOINTS
// ============================================================================

app.get("/db/products", (req, res) => {
  console.log("[DUMMY] GET /db/products");
  res.json(products);
});

app.get("/db/products/:id", (req, res) => {
  const product = findById(products, req.params.id);
  if (!product) return res.status(404).json({ error: "Product not found" });
  console.log(`[DUMMY] GET /db/products/${req.params.id}`);
  res.json(product);
});

app.post("/db/products", (req, res) => {
  const { name, description, price, stock, category } = req.body;
  if (!name || price === undefined || stock === undefined) {
    return res.status(400).json({ error: "Missing required fields" });
  }
  
  const newProduct = {
    id: generateId(),
    name,
    description: description || "",
    price: parseFloat(price),
    stock: parseInt(stock),
    category: category || "general",
    createdAt: Date.now()
  };
  products.push(newProduct);
  console.log(`[DUMMY] POST /db/products - Created product: ${name}`);
  res.json({ ok: true, product: newProduct });
});

app.patch("/db/products/:id", (req, res) => {
  const product = findById(products, req.params.id);
  if (!product) return res.status(404).json({ error: "Product not found" });
  
  const { name, description, price, stock, category } = req.body;
  if (name !== undefined) product.name = name;
  if (description !== undefined) product.description = description;
  if (price !== undefined) product.price = parseFloat(price);
  if (stock !== undefined) product.stock = parseInt(stock);
  if (category !== undefined) product.category = category;
  
  console.log(`[DUMMY] PATCH /db/products/${req.params.id}`);
  res.json({ ok: true, product });
});

app.delete("/db/products/:id", (req, res) => {
  const before = products.length;
  products = products.filter(p => p.id !== parseInt(req.params.id));
  if (products.length === before) {
    return res.status(404).json({ error: "Product not found" });
  }
  console.log(`[DUMMY] DELETE /db/products/${req.params.id}`);
  res.json({ ok: true, message: "Product deleted" });
});

// ============================================================================
//                           CART ENDPOINTS
// ============================================================================

app.get("/db/carts/user/:userId", (req, res) => {
  const cart = carts.find(c => c.userId === parseInt(req.params.userId));
  console.log(`[DUMMY] GET /db/carts/user/${req.params.userId}`);
  res.json(cart || { userId: parseInt(req.params.userId), items: [], createdAt: Date.now() });
});

app.post("/db/carts", (req, res) => {
  const { userId, productId, quantity } = req.body;
  if (!userId || !productId || !quantity) {
    return res.status(400).json({ error: "Missing required fields" });
  }
  
  let cart = carts.find(c => c.userId === userId);
  if (!cart) {
    cart = { id: generateId(), userId, items: [], createdAt: Date.now() };
    carts.push(cart);
  }
  
  const existingItem = cart.items.find(item => item.productId === productId);
  if (existingItem) {
    existingItem.quantity += quantity;
  } else {
    cart.items.push({ productId, quantity });
  }
  
  console.log(`[DUMMY] POST /db/carts - Added to cart for user ${userId}`);
  res.json({ ok: true, cart });
});

app.delete("/db/carts/user/:userId/product/:productId", (req, res) => {
  const cart = carts.find(c => c.userId === parseInt(req.params.userId));
  if (!cart) return res.status(404).json({ error: "Cart not found" });
  
  cart.items = cart.items.filter(item => item.productId !== parseInt(req.params.productId));
  console.log(`[DUMMY] DELETE cart item for user ${req.params.userId}`);
  res.json({ ok: true, cart });
});

app.delete("/db/carts/user/:userId", (req, res) => {
  const before = carts.length;
  carts = carts.filter(c => c.userId !== parseInt(req.params.userId));
  console.log(`[DUMMY] DELETE /db/carts/user/${req.params.userId}`);
  res.json({ ok: true, message: "Cart cleared" });
});

// ============================================================================
//                           ORDER ENDPOINTS
// ============================================================================

app.get("/db/orders", (req, res) => {
  console.log("[DUMMY] GET /db/orders");
  res.json(orders);
});

app.get("/db/orders/user/:userId", (req, res) => {
  const userOrders = orders.filter(o => o.userId === parseInt(req.params.userId));
  console.log(`[DUMMY] GET /db/orders/user/${req.params.userId}`);
  res.json(userOrders);
});

app.get("/db/orders/:id", (req, res) => {
  const order = findById(orders, req.params.id);
  if (!order) return res.status(404).json({ error: "Order not found" });
  console.log(`[DUMMY] GET /db/orders/${req.params.id}`);
  res.json(order);
});

app.post("/db/orders", (req, res) => {
  const { userId, items, total, shippingAddress } = req.body;
  if (!userId || !items || !total) {
    return res.status(400).json({ error: "Missing required fields" });
  }
  
  const newOrder = {
    id: generateId(),
    userId,
    items,
    total: parseFloat(total),
    status: "pending",
    shippingAddress: shippingAddress || "",
    createdAt: Date.now()
  };
  orders.push(newOrder);
  console.log(`[DUMMY] POST /db/orders - Created order for user ${userId}`);
  res.json({ ok: true, order: newOrder });
});

app.patch("/db/orders/:id", (req, res) => {
  const order = findById(orders, req.params.id);
  if (!order) return res.status(404).json({ error: "Order not found" });
  
  const { status, shippingAddress } = req.body;
  if (status) order.status = status;
  if (shippingAddress) order.shippingAddress = shippingAddress;
  
  console.log(`[DUMMY] PATCH /db/orders/${req.params.id}`);
  res.json({ ok: true, order });
});

// ============================================================================
//                           REVIEW ENDPOINTS
// ============================================================================

app.get("/db/reviews/product/:productId", (req, res) => {
  const productReviews = reviews.filter(r => r.productId === parseInt(req.params.productId));
  console.log(`[DUMMY] GET /db/reviews/product/${req.params.productId}`);
  res.json(productReviews);
});

app.post("/db/reviews", (req, res) => {
  const { productId, userId, rating, comment } = req.body;
  if (!productId || !userId || rating === undefined) {
    return res.status(400).json({ error: "Missing required fields" });
  }
  
  const newReview = {
    id: generateId(),
    productId,
    userId,
    rating: parseInt(rating),
    comment: comment || "",
    createdAt: Date.now()
  };
  reviews.push(newReview);
  console.log(`[DUMMY] POST /db/reviews - Created review for product ${productId}`);
  res.json({ ok: true, review: newReview });
});

// ============================================================================
//                           WISHLIST ENDPOINTS
// ============================================================================

app.get("/db/wishlist/user/:userId", (req, res) => {
  const userWishlist = wishlist.find(w => w.userId === parseInt(req.params.userId));
  console.log(`[DUMMY] GET /db/wishlist/user/${req.params.userId}`);
  res.json(userWishlist || { userId: parseInt(req.params.userId), productIds: [] });
});

app.post("/db/wishlist", (req, res) => {
  const { userId, productId } = req.body;
  if (!userId || !productId) {
    return res.status(400).json({ error: "Missing required fields" });
  }
  
  let userWishlist = wishlist.find(w => w.userId === userId);
  if (!userWishlist) {
    userWishlist = { userId, productIds: [] };
    wishlist.push(userWishlist);
  }
  
  if (!userWishlist.productIds.includes(productId)) {
    userWishlist.productIds.push(productId);
  }
  
  console.log(`[DUMMY] POST /db/wishlist - Added product ${productId} to user ${userId} wishlist`);
  res.json({ ok: true, wishlist: userWishlist });
});

app.delete("/db/wishlist/user/:userId/product/:productId", (req, res) => {
  const userWishlist = wishlist.find(w => w.userId === parseInt(req.params.userId));
  if (!userWishlist) return res.status(404).json({ error: "Wishlist not found" });
  
  userWishlist.productIds = userWishlist.productIds.filter(id => id !== parseInt(req.params.productId));
  console.log(`[DUMMY] DELETE wishlist item for user ${req.params.userId}`);
  res.json({ ok: true, wishlist: userWishlist });
});

// ============================================================================
//                           SERVER START
// ============================================================================

app.listen(PORT, () => {
  console.log(`\n========================================`);
  console.log(`E-Commerce Dummy DB Server`);
  console.log(`Running on http://localhost:${PORT}`);
  console.log(`========================================\n`);
  console.log("Available stores:");
  console.log(`  - ${users.length} users`);
  console.log(`  - ${products.length} products`);
  console.log(`  - ${carts.length} carts`);
  console.log(`  - ${orders.length} orders`);
  console.log(`  - ${reviews.length} reviews`);
  console.log(`  - ${wishlist.length} wishlists\n`);
});







