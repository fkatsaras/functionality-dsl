FROM python:3.11-slim

WORKDIR /app

# Install websockets
RUN pip install --no-cache-dir websockets

# Copy the echo server
COPY ws_auth_echo.py .

# Expose WebSocket port
EXPOSE 8765

# Run the echo server
CMD ["python", "ws_auth_echo.py"]
