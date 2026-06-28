# MediClaim backend image.
#
# Uses a standard Debian-based Python image (not Nixpacks) so that the system
# libraries required by OpenCV — which PaddleOCR pulls in transitively — are
# installed on the normal loader path. This permanently fixes:
#   ImportError: libGL.so.1: cannot open shared object file
FROM python:3.11-slim

# System libraries needed at runtime:
#   libgl1          -> provides libGL.so.1 (OpenCV)
#   libglib2.0-0    -> provides libgthread-2.0.so.0 (OpenCV)
#   libgomp1        -> OpenMP runtime used by PaddlePaddle/OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application code (build context is the backend/ directory).
COPY . .

# Railway injects $PORT at runtime; default to 8000 for local runs.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
