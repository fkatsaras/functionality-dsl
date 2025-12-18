const express = require("express");
const app = express();
const PORT = 9001;

app.use(express.json());

// Enable CORS
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  next();
});

// --- In-memory product catalog ---
const products = [
  {
    id: "prod-001",
    name: "Wireless Headphones",
    price: 79.99,
    stock: 45,
    category: "Electronics",
    thumbnail: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=200",
    description: "Premium wireless headphones with active noise cancellation",
    gallery: [
      "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
      "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400"
    ],
    rating: 4.5,
    specs: {
      battery: "30 hours",
      bluetooth: "5.0",
      weight: "250g"
    }
  },
  {
    id: "prod-002",
    name: "Smart Watch",
    price: 199.99,
    stock: 23,
    category: "Electronics",
    thumbnail: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=200",
    description: "Fitness tracker with heart rate monitor and GPS",
    gallery: [
      "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400",
      "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=400"
    ],
    rating: 4.7,
    specs: {
      battery: "7 days",
      waterproof: "5ATM",
      display: "1.4 inch AMOLED"
    }
  },
  {
    id: "prod-003",
    name: "Laptop Backpack",
    price: 49.99,
    stock: 67,
    category: "Accessories",
    thumbnail: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=200",
    description: "Durable backpack with padded laptop compartment",
    gallery: [
      "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400"
    ],
    rating: 4.3,
    specs: {
      capacity: "30L",
      laptop: "Up to 15.6 inch",
      material: "Water-resistant nylon"
    }
  },
  {
    id: "prod-004",
    name: "Mechanical Keyboard",
    price: 129.99,
    stock: 12,
    category: "Electronics",
    thumbnail: "https://images.unsplash.com/photo-1595225476474-87563907a212?w=200",
    description: "RGB mechanical keyboard with Cherry MX switches",
    gallery: [
      "https://images.unsplash.com/photo-1595225476474-87563907a212?w=400",
      "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400"
    ],
    rating: 4.8,
    specs: {
      switches: "Cherry MX Red",
      rgb: "Per-key RGB",
      layout: "Full-size"
    }
  },
  {
    id: "prod-005",
    name: "USB-C Hub",
    price: 39.99,
    stock: 89,
    category: "Accessories",
    thumbnail: "https://images.unsplash.com/photo-1625948515291-69613efd103f?w=200",
    description: "7-in-1 USB-C hub with HDMI and card readers",
    gallery: [
      "https://images.unsplash.com/photo-1625948515291-69613efd103f?w=400"
    ],
    rating: 4.4,
    specs: {
      ports: "7 ports",
      hdmi: "4K@60Hz",
      power: "100W PD"
    }
  },
  {
    id: "prod-006",
    name: "Wireless Mouse",
    price: 29.99,
    stock: 0,
    category: "Electronics",
    thumbnail: "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=200",
    description: "Ergonomic wireless mouse with 6 buttons",
    gallery: [
      "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400"
    ],
    rating: 4.2,
    specs: {
      dpi: "Up to 3200",
      battery: "6 months",
      buttons: "6 programmable"
    }
  }
];

// GET /products - List all products
app.get("/products", (req, res) => {
  console.log(`[PRODUCT-SERVICE] Returning ${products.length} products`);
  res.json(products);
});

// GET /products/:productId - Get single product details
app.get("/products/:productId", (req, res) => {
  const { productId } = req.params;
  const product = products.find(p => p.id === productId);

  if (!product) {
    return res.status(404).json({ error: "Product not found" });
  }

  console.log(`[PRODUCT-SERVICE] Returning product: ${productId}`);
  res.json(product);
});

app.listen(PORT, () => {
  console.log(`Product Service running on http://localhost:${PORT}`);
  console.log(`Total products: ${products.length}`);
  console.log(`In stock: ${products.filter(p => p.stock > 0).length}`);
});
