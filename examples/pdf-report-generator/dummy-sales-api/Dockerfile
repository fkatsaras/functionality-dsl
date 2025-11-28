FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn

# Copy application
COPY app.py .

# Expose port
EXPOSE 9001

# Run the application
CMD ["python", "app.py"]
