# Text Processing Example

**Content Type:** `text/plain`

This example demonstrates how to handle plain text content in FDSL, including:
- Accepting `text/plain` request bodies
- Returning `text/plain` responses from external services
- Computing metadata from text content (length, word count)
- Transforming text through external services

## What It Does

1. User submits plain text via the API
2. Text is forwarded to an external transformation service
3. Transformed text is returned with computed metadata:
   - Character count
   - Word count
   - Boolean flag for long texts (>100 chars)

## Key Concepts

- **Content Type Specification**: `text/plain:` in request/response blocks
- **String Type Entities**: Wrapper entities with single string attribute
- **Text Functions**: `len()`, `split()` for text analysis
- **Computed Attributes**: Deriving metadata from text content

## FDSL Snippet

```fdsl
Source<REST> TextTransformService
  url: "http://dummy-text-service:9800/transform"
  method: POST
  request:
    text/plain:
      type: string
      entity: InputText
  response:
    text/plain:
      type: string
      entity: TransformedText
end

Entity TextResult(TransformedText)
  attributes:
    - text: string = TransformedText.content;
    - length: integer = len(TransformedText.content);
    - word_count: integer = len(split(TransformedText.content, " "));
    - is_long: boolean = len(TransformedText.content) > 100;
end
```

## Running the Example

```bash
# Generate code
fdsl generate examples/text-processing/main.fdsl --out examples/text-processing/generated

# Start dummy service (if provided)
cd examples/text-processing/dummy-service
docker compose up -d

# Start the API
cd ../generated
docker compose -p thesis up
```

## Testing

```bash
# Send plain text for transformation
curl -X POST http://localhost:8087/api/text/transform \
  -H "Content-Type: text/plain" \
  -d "Hello World! This is a test of plain text processing."

# Expected response (JSON with metadata)
{
  "text": "HELLO WORLD! THIS IS A TEST OF PLAIN TEXT PROCESSING.",
  "length": 53,
  "word_count": 9,
  "is_long": false
}
```
