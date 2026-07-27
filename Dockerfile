FROM python:3.11-slim

# Unbuffered so container logs appear immediately; no pip cache in the layer.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY pyproject.toml ./
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Run unprivileged. /app/data holds the audit trail and is the only path the
# process writes to; mount a volume there to keep it across upgrades.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app/data
USER appuser

VOLUME ["/app/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

# --workers 1 is REQUIRED, not a stylistic default: task state lives in process
# memory, so a second worker would answer /api/v2/tasks/{id} with 404 at random.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
