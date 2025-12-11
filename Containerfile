# ==============================================================================
# 0. THE ASTRAL PLANE
# ==============================================================================
# We define an alias 'uv' for the image containing the uv binary.
# This allows us to "borrow" the tool later without downloading it into our layers.
FROM ghcr.io/astral-sh/uv:0.5.22 AS uv

# ==============================================================================
# STAGE I: BUILDER
# ==============================================================================
FROM python:3.13-slim-bookworm AS builder

# Configure uv for container usage:
# - LINK_MODE=copy: Essential for cache mounts (hardlinks fail across filesystems).
# - COMPILE_BYTECODE: Compiles .pyc files for faster startup.
# - PYTHON_DOWNLOADS=0: Use the system python, don't download a managed one.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=1

WORKDIR /app

# --- 1. Install Dependencies (Cached Layer) ---
# We mount the 'uv' binary and cache directories to install libs without copying source files yet.
# This layer is reused unless uv.lock or pyproject.toml changes.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    /bin/uv sync --frozen --no-install-project --extra server

# --- 2. Install Project (Frequent Change Layer) ---
# Copy the actual source code. This breaks cache whenever you change code.
COPY . .

# Install the project package itself into the environment with server dependencies.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    /bin/uv sync --frozen --extra server

# ==============================================================================
# STAGE II: RUNNER (The Production Artifact)
# ==============================================================================
FROM python:3.13-slim-bookworm

# --- Security Setup ---
# Create a dedicated group (gid 1001) and user (uid 1001).
# We never run as root to limit the blast radius if the container is compromised.
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --uid 1001 --gid 1001 appuser

WORKDIR /app

# --- The Transplant ---
# Copy the Virtual Environment (libraries + app) from the builder stage.
# We change ownership to appuser immediately.
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/src /app/src

# --- Environment Activation ---
# Add the venv/bin to PATH. This means typing 'granian' works automatically
# without needing to source anything or type absolute paths.
ENV PATH="/app/.venv/bin:$PATH"
# Tell Litestar/Granian where the application factory is.
ENV LITESTAR_APP="lychd.main:app"

# Drop privileges to the non-root user.
USER appuser

# Document that the service listens on port 8000.
EXPOSE 8000

# Start the high-performance ASGI server.
CMD ["granian", "--host", "0.0.0.0", "--port", "8000", "lychd.main:app"]
