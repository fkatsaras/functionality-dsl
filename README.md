# Functionality DSL (FDSL)

A declarative domain-specific language for building REST and WebSocket APIs. Generate production-ready FastAPI backends from high-level specifications.

---


## What is FDSL?

Define your data sources, entities, and UI components in a simple syntax. FDSL generates routers, services, authentication, WebSocket handlers, and frontend components.

```fdsl
Source<REST> ProductsAPI
  url: "http://api.example.com/products"
  operations: [read, create, update]
end

Entity Products
  source: ProductsAPI
  attributes:
    - id: integer @readonly;
    - name: string;
    - price: number;
    - stock: integer;
  access: public
end
```

**Generates:** FastAPI router, Pydantic models, service layer, and OpenAPI documentation.

---

## Features

- **Multi-Source Composition** - Aggregate multiple REST/WebSocket sources with computed fields
- **Rich Expressions** - Lambda functions and built-in functions for data transformation
- **WebSocket Support** - Real-time data streams with automatic synchronization
- **Flexible Auth** - HTTP Bearer, Basic, and API Key authentication with RBAC
- **UI Generation** - Svelte components for tables, charts, gauges, and live metrics

---

## Installation

```bash
git clone https://github.com/yourusername/functionality-dsl.git
cd functionality-dsl
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

---

## Quick Start

Create `my-api.fdsl`:

```fdsl
Server MyAPI
  host: "localhost"
  port: 8080
  cors: "*"
end

Source<REST> UsersAPI
  url: "https://jsonplaceholder.typicode.com/users"
  operations: [read]
end

Entity Users
  source: UsersAPI
  attributes:
    - id: integer;
    - name: string;
    - email: string<email>;
  access: public
end
```

Generate and run:

```bash
fdsl generate my-api.fdsl --out generated
cd generated
pip install -r requirements.txt
uvicorn main:app --reload
```

Visit http://localhost:8080/docs

---

## Examples

### E-Commerce
```bash
fdsl generate examples/ecommerce/main.fdsl --out generated
```
Shopping cart with products, orders, WebSocket order tracking, and role-based access control.

### Smart Home
```bash
fdsl generate examples/smart-home/main.fdsl --out generated
```
Multi-device control with REST APIs and real-time monitoring via WebSocket.

### Crypto Ticker
```bash
fdsl generate examples/websocket/crypto-ticker/main.fdsl --out generated
```
Real-time cryptocurrency prices from Binance WebSocket streams.

---

## Core Concepts

**Sources** - External REST APIs or WebSocket streams
```fdsl
Source<REST> PaymentsAPI
  url: "http://payments-service/api"
  operations: [create]
end
```

**Entities** - Data structures with computed fields
```fdsl
Entity OrderSummary(Order)
  attributes:
    - total: number = sum(map(Order.items, i => i["price"] * i["qty"]));
  access: [customer, admin]
end
```

**Authentication** - Multiple auth mechanisms
```fdsl
Auth<http> BearerAuth
  scheme: bearer
end

Role admin uses BearerAuth

Entity SecureData
  source: DataAPI
  attributes: [...]
  access: [admin]
end
```

---

## CLI Commands

```bash
fdsl validate <file>                    # Validate syntax
fdsl generate <file> --out <dir>        # Generate code
fdsl from-openapi <file> --out <file>   # OpenAPI to FDSL
fdsl from-asyncapi <file> --out <file>  # AsyncAPI to FDSL
```

---

## Documentation

- [Examples](examples/) - 40+ working examples
- [Model & Metamodel Diagrams](docs/) - Generated visualizations for all examples

---

## License

MIT License
