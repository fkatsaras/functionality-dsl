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

## CLI Commands

```bash
fdsl validate <file>                    # Validate syntax
fdsl generate <file> --out <dir>        # Generate code
fdsl from-openapi <file> --out <file>   # OpenAPI to FDSL
fdsl from-asyncapi <file> --out <file>  # AsyncAPI to FDSL
```

---

## Documentation

- [Model & Metamodel Diagrams](docs/) - Generated visualizations for all examples

