# FDSL Project Glossary

## Core Concepts

### Entity
Data structure definition with attributes. Can be:
- **Pure Schema Entity**: No expressions, just type declarations (e.g., `ProductRaw`)
- **Transformation Entity**: Has computed attributes with expressions (e.g., `ProductView`)
- **Wrapper Entity**: Single-attribute entity wrapping primitives/arrays (e.g., `OutgoingWrapper`)

### Source
External API/service integration. Types:
- **Source<REST>**: HTTP REST API integration
- **Source<WS>**: WebSocket connection to external service

### APIEndpoint
Internal API endpoint exposed by generated code. Types:
- **APIEndpoint<REST>**: REST endpoint (GET, POST, PUT, DELETE)
- **APIEndpoint<WS>**: WebSocket endpoint (duplex, publish-only, subscribe-only)

### Terminal Entity
The final entity in a transformation chain that gets sent to external targets or clients.

### Chain
Sequence of entity transformations from source to destination.
- **Inbound Chain**: Client -> Server -> External
- **Outbound Chain**: External -> Server -> Client

## WebSocket Terminology

### For APIEndpoint<WS>
- **subscribe**: Data clients RECEIVE (displayed in UI) - OUTBOUND from server
- **publish**: Data clients SEND (from UI to server) - INBOUND to server

### For Source<WS>
- **subscribe**: Data we RECEIVE FROM external - INBOUND to our system
- **publish**: Data we SEND TO external - OUTBOUND from our system

## Data Flow Patterns

### Query Flow (GET)
`External Source -> Pure Schema Entity -> Transformation Entity -> APIEndpoint -> Response`

### Mutation Flow (POST/PUT/DELETE)
`APIEndpoint -> Request Entity -> Transformation Entity -> External Target`

### WebSocket Duplex Flow
**Inbound**: `APIEndpoint.publish -> Wrapper -> Transformation -> Source.publish -> External`
**Outbound**: `External -> Source.subscribe -> Transformation -> APIEndpoint.subscribe -> Client`

## Special Markers

### __WRAP_PAYLOAD__
Special marker in compiled chains indicating a wrapper entity should auto-wrap primitive values from clients.

### Decorators
- **@path**: Attribute populated from APIEndpoint path parameters
- **@query**: Attribute populated from query parameters
- **@header**: Attribute populated from HTTP headers

## Generated Code Structure

### Router
FastAPI router file handling HTTP/WebSocket requests and responses.

### Service
Business logic layer computing entity chains and managing external connections.

### Model
Pydantic models for validation and serialization.

## Type System

### Format Specifications
OpenAPI-aligned format qualifiers: `string<email>`, `number<double>`, `integer<int32>`

### Range Constraints
Type constraints: `string(3..50)`, `integer(18..)`, `array(1..10)`

### Entity References
Using entities as types: `array<Product>`, `object<ProductData>`
