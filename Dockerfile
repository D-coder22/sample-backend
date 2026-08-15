FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

WORKDIR /app

COPY . /app


CMD ["uv","run","uvicorn","main:app","--app-dir","src/sample_backend","--host","0.0.0.0", "--port","8000", "--workers", "2"]