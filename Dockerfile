# Stage 1: build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/bnt_frontend
COPY bnt_frontend/package*.json ./
RUN npm ci
COPY bnt_frontend/ ./
RUN npm run build

# Stage 2: production image
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Bring in the compiled frontend assets from stage 1
COPY --from=frontend-builder /app/bnt_frontend/dist ./bnt_frontend/dist

RUN chmod +x scripts/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["scripts/entrypoint.sh"]
