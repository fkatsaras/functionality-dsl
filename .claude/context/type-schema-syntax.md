# Type/Schema Syntax - Request/Response/Subscribe/Publish Blocks

## Overview

As of the latest update, all `request:`, `response:`, `subscribe:`, and `publish:` blocks **MUST** explicitly specify both a `type:` and `schema:` field.

## Syntax

```fdsl
response:
  type: <string|number|integer|boolean|array|object>
  schema: EntityName
```

## Validation Rules

### 1. Both Fields Required

Both `type:` and `schema:` are **mandatory** in all request/response/subscribe/publish blocks.

### 2. Type Compatibility with Schema Entity

#### For Primitive/Array Types

When `type` is `string`, `number`, `integer`, `boolean`, or `array`:
- The schema entity **MUST have EXACTLY ONE attribute**
- This is a wrapper entity that wraps the primitive/array value

**Example - Correct:**
```fdsl
Entity ArrayWrapper
  attributes:
    - items: array;
end

Source<REST> DataSource
  url: "https://api.example.com/data"
  verb: GET
  response:
    type: array
    schema: ArrayWrapper
end
```

**Example - Incorrect:**
```fdsl
Entity BadWrapper
  attributes:
    - items: array;
    - count: integer;  // ← ERROR: Wrapper must have exactly ONE attribute
end

Source<REST> DataSource
  url: "https://api.example.com/data"
  verb: GET
  response:
    type: array
    schema: BadWrapper  // ← Will fail validation
end
```

#### For Object Type

When `type` is `object`:
- The schema entity can have any number of attributes
- Entity attributes are populated with the object's fields by name

**Example:**
```fdsl
Entity UserData
  attributes:
    - id: string;
    - name: string;
    - email: string;
end

Source<REST> UserAPI
  url: "https://api.example.com/user"
  verb: GET
  response:
    type: object
    schema: UserData
end
```

## Complete Examples

### REST Endpoint with Array Response

```fdsl
// Schema wrapper for array
Entity ProductsWrapper
  attributes:
    - items: array<Product>;
end

Source<REST> ProductsAPI
  url: "https://api.example.com/products"
  verb: GET
  response:
    type: array
    schema: ProductsWrapper
end

// Transformation entity (can have multiple attributes)
Entity ProductsView(ProductsWrapper)
  attributes:
    - products: array = ProductsWrapper.items;
    - count: integer = len(ProductsWrapper.items);
end

APIEndpoint<REST> GetProducts
  path: "/api/products"
  verb: GET
  response:
    type: object
    schema: ProductsView
end
```

### WebSocket with Primitive Value

```fdsl
// Wrapper for string primitive
Entity MessageWrapper
  attributes:
    - value: string;
end

Entity ProcessedMessage(MessageWrapper)
  attributes:
    - text: string = upper(MessageWrapper.value);
end

APIEndpoint<WS> ChatEndpoint
  channel: "/api/chat"
  publish:
    type: string         // Client sends primitive string
    schema: MessageWrapper
  subscribe:
    type: object         // Client receives processed object
    schema: ProcessedMessage
end
```

### POST Endpoint with Request Body

```fdsl
Entity CreateUserRequest
  attributes:
    - name: string;
    - email: string;
    - age: integer;
end

Entity CreatedUserResponse
  attributes:
    - id: string;
    - name: string;
    - email: string;
    - createdAt: string;
end

APIEndpoint<REST> CreateUser
  path: "/api/users"
  verb: POST
  request:
    type: object
    schema: CreateUserRequest
  response:
    type: object
    schema: CreatedUserResponse
end
```

## Validation Error Messages

If validation fails, you'll see errors like:

```
Source<REST> 'DataSource' response has type='array' but schema entity
'BadWrapper' has 2 attribute(s). Wrapper entities for primitive/array
types must have EXACTLY ONE attribute.
```

## Migration from Old Syntax

**Old syntax (no type field):**
```fdsl
response:
  schema: ProductList
```

**New syntax (required type field):**
```fdsl
response:
  type: array
  schema: ProductList
```

## Quick Reference

| Type | Entity Constraint | Use Case |
|------|------------------|----------|
| `string` | Exactly 1 attribute | Primitive string responses |
| `number` | Exactly 1 attribute | Primitive number responses |
| `integer` | Exactly 1 attribute | Primitive integer responses |
| `boolean` | Exactly 1 attribute | Primitive boolean responses |
| `array` | Exactly 1 attribute | Array responses (wrapper) |
| `object` | Any number of attributes | Object/complex responses |

## Notes

- The type field aligns with OpenAPI type specifications
- Wrapper entities are automatically populated by the framework
- Transformation entities (with parents) can have any number of attributes regardless of type
- Only the **immediate schema entity** referenced in the block is validated for attribute count
