FROM python:3.11-slim

WORKDIR /app

# Copy and install Python dependencies (cached layer)
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

# Copy application code
COPY . .

ENV DEPLOYMENT_MODE=render

EXPOSE 8001

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
