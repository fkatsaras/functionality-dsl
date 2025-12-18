# File Upload Example

**Content Type:** `multipart/form-data`

This example demonstrates how to handle file uploads in FDSL, including:
- Accepting `multipart/form-data` requests with binary files
- Processing file metadata (filename, size, description)
- Computing file size in different units (bytes, MB)
- Error handling for file size limits

## What It Does

1. User uploads a file with metadata (filename, optional description)
2. File is forwarded to an external storage service
3. Storage service returns upload confirmation with:
   - Unique file ID
   - Download URL
   - File size
   - Upload timestamp
4. API computes additional metadata (size in MB, large file flag)

## Key Concepts

- **Content Type Specification**: `multipart/form-data:` in request block
- **Binary Type**: `file: binary;` attribute for file data
- **Mixed Data Types**: Combining binary (file) with text (metadata) in one entity
- **File Size Validation**: Error handling based on file size
- **Unit Conversion**: Converting bytes to MB with `round()`

## FDSL Snippet

```fdsl
Entity FileUpload
  attributes:
    - file: binary;
    - filename: string;
    - description: string?;
end

Endpoint<REST> UploadFileAPI
  path: "/api/files/upload"
  method: POST
  request:
    multipart/form-data:
      type: object
      entity: FileUpload
  response:
    type: object
    entity: FileUploadResult
  errors:
    - 413: condition: UploadResponse.size > 52428800 "File too large (max 50MB)"
end

Entity FileUploadResult(UploadResponse)
  attributes:
    - size_mb: number = round(UploadResponse.size / 1048576.0, 2);
    - is_large: boolean = UploadResponse.size > 10485760;
end
```

## Running the Example

```bash
# Generate code
fdsl generate examples/file-upload/main.fdsl --out examples/file-upload/generated

# Start dummy storage service (if provided)
cd examples/file-upload/dummy-service
docker compose up -d

# Start the API
cd ../generated
docker compose -p thesis up
```

## Testing

```bash
# Upload a file with metadata
curl -X POST http://localhost:8088/api/files/upload \
  -F "file=@document.pdf" \
  -F "filename=document.pdf" \
  -F "description=Important document"

# Expected response
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "download_url": "https://storage.example.com/files/f47ac10b...",
  "file_size": 2458624,
  "size_mb": 2.34,
  "uploaded": "2025-11-26T14:30:00Z",
  "is_large": false
}
```

## File Size Limits

The example includes validation:
- **Warning threshold**: Files > 10MB marked with `is_large: true`
- **Hard limit**: Files > 50MB rejected with HTTP 413 error
- **Conversion**: Sizes displayed in both bytes and megabytes
