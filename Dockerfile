FROM python:3.14.4-slim-trixie@sha256:2ca02f32b4d9d893863367ce07ec1972819f476dd38d8612f2a9cb6a41cbb727
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY requirements-portable.lock ./
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements-portable.lock
COPY . ./
CMD ["python", "-m", "scripts.container_start"]
