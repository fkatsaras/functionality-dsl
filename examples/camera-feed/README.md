# Camera Feed Demo

**What it demonstrates:**
- WebSocket binary data streaming (image frames)
- **Binary data processing** - Real-time image transformations
- Camera component for live video display
- Non-object content types (image/jpeg, type: binary)
- Binary frame transmission over WebSocket
- Real-time video streaming with FDSL
- Using builtin image processing functions (invert, grayscale, resize, rotate)

**Requires dummy service:** Yes - Camera feed simulator that streams PNG images

## How to run

1. **Start the dummy camera service:**
   ```bash
   cd dummy-service
   npm install
   docker compose -f docker-compose.dummycamera.yaml -p thesis up
   ```
   This starts:
   - 1 WebSocket server (port 9700) streaming image frames at 10 fps
   - Loops through 200 PNG frames from the vidf1_33_000.y directory

2. **In a new terminal, generate the backend code:**
   ```bash
   cd ..  # Back to camera-feed directory
   fdsl generate main.fdsl --out generated
   ```

3. **Run the generated application:**
   ```bash
   cd generated
   docker compose -p thesis up
   ```

4. **Access the UI:**
   Open http://localhost:3000 - you'll see the live camera feed component displaying the video stream

## What's happening

1. **Dummy service** (`dummycamera` container):
   - Reads PNG files from `vidf1_33_000.y/` directory
   - Streams them as binary WebSocket frames at 10 fps
   - Loops continuously through all 200 frames

2. **Generated backend** (`CameraServer`):
   - Subscribes to the external WebSocket feed (`ws://dummycamera:9700/camera/feed`)
   - Receives binary image frames
   - **Processes each frame** using `image_invert()` function
   - Re-streams processed frames to frontend clients via `/api/camera/live`

3. **Frontend Camera component**:
   - Connects to backend WebSocket endpoint
   - Receives binary frames (Blob/ArrayBuffer)
   - Creates object URLs and displays in `<img>` element
   - Shows live indicator and handles reconnection

## What you'll learn

- How to stream binary data over WebSocket with FDSL
- Using non-object content types (image/jpeg, image/png)
- Wrapper entities for primitive/binary types
- Building live camera/video applications
- Binary data flow from external sources to UI components
- Handling binary WebSocket frames in backend and frontend

## Binary Processing Features

The example demonstrates real-time image processing using FDSL's builtin binary functions:

```fdsl
// Raw frame from source
Entity ImageFrame
  attributes:
    - frame: binary;
end

// Processed frame with image_invert() function
Entity ProcessedFrame(ImageFrame)
  attributes:
    - frame: binary = image_invert(ImageFrame.frame);
end
```

### Available Binary Functions

**Image Processing:**
- `image_invert(bytes)` - Invert colors (negative effect) ✅ Used in this demo
- `image_grayscale(bytes)` - Convert to grayscale
- `image_resize(bytes, width, height)` - Resize to dimensions
- `image_rotate(bytes, degrees)` - Rotate by angle
- `image_dimensions(bytes)` - Get {width, height} metadata

**Binary Utilities:**
- `binary_size(bytes)` - Get size in bytes
- `binary_encode_base64(bytes)` - Encode to base64 string
- `binary_decode_base64(string)` - Decode from base64

### Try Different Transformations

Edit `main.fdsl` and change the ProcessedFrame entity to try different effects:

```fdsl
// Grayscale effect
Entity ProcessedFrame(ImageFrame)
  attributes:
    - frame: binary = image_grayscale(ImageFrame.frame);
end

// Resize to thumbnail
Entity ProcessedFrame(ImageFrame)
  attributes:
    - frame: binary = image_resize(ImageFrame.frame, 320, 240);
end

// Rotate 90 degrees
Entity ProcessedFrame(ImageFrame)
  attributes:
    - frame: binary = image_rotate(ImageFrame.frame, 90);
end

// Chain multiple transformations
Entity GrayscaleFrame(ImageFrame)
  attributes:
    - frame: binary = image_grayscale(ImageFrame.frame);
end

Entity ProcessedFrame(GrayscaleFrame)
  attributes:
    - frame: binary = image_resize(GrayscaleFrame.frame, 640, 480);
end
```

## Technical notes

- **Content type**: Uses `image/jpeg` content type with `type: binary`
- **Wrapper entity**: `ImageFrame` has single `frame: binary` attribute for binary data
- **Frame rate**: Dummy service sends 10 frames per second (configurable)
- **Loop**: Frames loop continuously - perfect for testing
- **Binary transmission**: WebSocket sends raw binary (no base64 encoding needed)
- **Image processing**: Uses Pillow library (automatically installed via Docker)
- **Performance**: Processing happens on each frame in real-time
