# Camera Feed Demo

**What it demonstrates:**
- WebSocket binary data streaming (image frames)
- Camera component for live video display
- Non-object content types (image/jpeg)
- Binary frame transmission over WebSocket
- Real-time video streaming with FDSL

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
   - Re-streams them to frontend clients via `/api/camera/live`

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

## Technical notes

- **Content type**: Uses `image/jpeg` content type (works for PNG too since it's binary)
- **Wrapper entity**: `ImageFrame` has single `frame: string` attribute for binary data
- **Frame rate**: Dummy service sends 10 frames per second (configurable)
- **Loop**: Frames loop continuously - perfect for testing
- **Binary transmission**: WebSocket sends raw binary (no base64 encoding needed)
