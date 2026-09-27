FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860
WORKDIR /srv/gateway
RUN useradd --create-home --uid 1000 gateway
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=gateway:gateway app/ ./app/
COPY --chown=gateway:gateway config/ ./config/
COPY --from=frontend-build --chown=gateway:gateway /build/dist ./static/
USER gateway
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
