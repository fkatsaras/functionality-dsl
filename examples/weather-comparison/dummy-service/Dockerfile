FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn

COPY app.py .

EXPOSE 9003

CMD ["python", "app.py"]
