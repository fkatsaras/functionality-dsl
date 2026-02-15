# New REST Data Display Components

This document describes the four new REST-based data display components added to FDSL.

## Component Architecture

All components follow a two-layer pattern:
1. **Primitives** (`lib/primitives/`) - Generic Svelte components with no FDSL logic
2. **FDSL Components** (`lib/components/`) - Entity-bound wrappers that fetch REST data

## Components

### 1. Metric Component

Displays a single numeric value with optional formatting.

**FDSL Syntax:**
```fdsl
Component<Metric> TotalSales
  entity: OrderStats
  field: "total_sales"
  label: "Total Sales"
  format: "currency"
  refreshMs: 5000
end
```

**Props:**
- `entity:` - REST entity to fetch data from (required)
- `field:` - Field name to extract from entity (required)
- `label:` - Display label (optional, defaults to field name)
- `format:` - "number" | "currency" | "percent" (optional, defaults to "number")
- `refreshMs:` - Auto-refresh interval in ms (optional)

**Example Use Case:**
- Display total order count
- Show current inventory value
- Display conversion rate percentage

---

### 2. DataCard Component

Displays multiple fields from an entity in a card layout.

**FDSL Syntax:**
```fdsl
Component<DataCard> UserProfile
  entity: CurrentUser
  fields: ["name", "email", "role", "last_login"]
  title: "User Information"
  highlight: "role"
  refreshMs: 10000
end
```

**Props:**
- `entity:` - REST entity to fetch data from (required)
- `fields:` - List of field names to display (required)
- `title:` - Card title (optional, defaults to entity name)
- `highlight:` - Field name to highlight (optional)
- `refreshMs:` - Auto-refresh interval in ms (optional)

**Features:**
- Auto-formats field names (snake_case -> Title Case)
- Formats values (booleans -> Yes/No, arrays -> [N items], etc.)
- Highlights specified field with background color

**Example Use Case:**
- Display user profile details
- Show product information
- Display order summary

---

### 3. PieChart Component

Displays proportional data as a pie chart with legend.

**FDSL Syntax:**
```fdsl
Component<PieChart> InventoryHealth
  entity: InventoryStats
  slices:
    - field: "in_stock" label: "In Stock" color: "#22c55e"
    - field: "low_stock" label: "Low Stock" color: "#f59e0b"
    - field: "out_of_stock" label: "Out of Stock" color: "#ef4444"
  title: "Inventory Health"
  size: 250
  refreshMs: 5000
end
```

**Props:**
- `entity:` - REST entity to fetch data from (required)
- `slices:` - List of slice definitions (required)
  - Each slice: `field:` (entity field), `label:` (display name), `color:` (hex color)
- `title:` - Chart title (optional, defaults to entity name)
- `size:` - Chart diameter in pixels (optional, default: 200)
- `refreshMs:` - Auto-refresh interval in ms (optional)

**Features:**
- Automatically calculates percentages
- Filters out zero values
- Shows percentages in legend
- SVG-based rendering

**Example Use Case:**
- Inventory status breakdown (in stock / low / out)
- Order status distribution (pending / processing / shipped)
- User role distribution

---

### 4. BarChart Component

Displays data as vertical bars for comparison.

**FDSL Syntax:**
```fdsl
Component<BarChart> OrdersByStatus
  entity: OrderStats
  bars:
    - field: "pending" label: "Pending" color: "#3b82f6"
    - field: "processing" label: "Processing" color: "#f59e0b"
    - field: "shipped" label: "Shipped" color: "#8b5cf6"
    - field: "delivered" label: "Delivered" color: "#22c55e"
  title: "Orders by Status"
  xLabel: "Status"
  yLabel: "Count"
  height: 350
  width: 600
  refreshMs: 5000
end
```

**Props:**
- `entity:` - REST entity to fetch data from (required)
- `bars:` - List of bar definitions (required)
  - Each bar: `field:` (entity field), `label:` (x-axis label), `color:` (optional hex color)
- `title:` - Chart title (optional, defaults to entity name)
- `xLabel:` - X-axis label (optional)
- `yLabel:` - Y-axis label (optional)
- `height:` - Chart height in pixels (optional, default: 300)
- `width:` - Chart width in pixels (optional, default: 500)
- `refreshMs:` - Auto-refresh interval in ms (optional)

**Features:**
- Automatic Y-axis scaling with 5 ticks
- Grid lines for readability
- Value labels on top of bars
- Customizable colors per bar
- SVG-based rendering

**Example Use Case:**
- Compare sales by product category
- Show order counts by status
- Display temperature readings from multiple sensors

---

## Complete Example

Here's an e-commerce dashboard using all four components:

```fdsl
Server EcommerceAPI
  host: "localhost"
  port: 8080
  cors: "*"
  loglevel: debug
end

Source<REST> OrderAPI
  base_url: "http://backend:9000/orders"
  operations: [read]
end

Source<REST> InventoryAPI
  base_url: "http://backend:9000/inventory"
  operations: [read]
end

Entity OrderStats
  source: OrderAPI
  attributes:
    - total_sales: number @readonly;
    - total_orders: integer @readonly;
    - pending: integer @readonly;
    - processing: integer @readonly;
    - shipped: integer @readonly;
    - delivered: integer @readonly;
  access: public
end

Entity InventoryStats
  source: InventoryAPI
  attributes:
    - in_stock: integer @readonly;
    - low_stock: integer @readonly;
    - out_of_stock: integer @readonly;
    - total_value: number @readonly;
  access: public
end

// Single value displays
Component<Metric> TotalSales
  entity: OrderStats
  field: "total_sales"
  label: "Total Sales"
  format: "currency"
  refreshMs: 5000
end

Component<Metric> TotalOrders
  entity: OrderStats
  field: "total_orders"
  label: "Total Orders"
  format: "number"
  refreshMs: 5000
end

// Multi-field card
Component<DataCard> InventoryOverview
  entity: InventoryStats
  fields: ["in_stock", "low_stock", "out_of_stock", "total_value"]
  title: "Inventory Overview"
  highlight: "low_stock"
  refreshMs: 5000
end

// Pie chart
Component<PieChart> InventoryHealth
  entity: InventoryStats
  slices:
    - field: "in_stock" label: "In Stock" color: "#22c55e"
    - field: "low_stock" label: "Low Stock" color: "#f59e0b"
    - field: "out_of_stock" label: "Out of Stock" color: "#ef4444"
  title: "Inventory Health"
  size: 250
  refreshMs: 5000
end

// Bar chart
Component<BarChart> OrdersByStatus
  entity: OrderStats
  bars:
    - field: "pending" label: "Pending" color: "#3b82f6"
    - field: "processing" label: "Processing" color: "#f59e0b"
    - field: "shipped" label: "Shipped" color: "#8b5cf6"
    - field: "delivered" label: "Delivered" color: "#22c55e"
  title: "Orders by Status"
  xLabel: "Status"
  yLabel: "Count"
  height: 350
  width: 600
  refreshMs: 5000
end
```

This generates a complete dashboard with:
- Two metric cards showing total sales and orders
- One data card with inventory details
- One pie chart showing inventory health distribution
- One bar chart comparing order counts by status

All components auto-refresh every 5 seconds.
