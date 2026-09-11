# ==============================================================================
# 0. THE ASTRAL PLANE
# ==============================================================================
# We define an alias 'uv' for the image containing the uv binary.
# This allows us to "borrow" the tool later without downloading it into our layers.
FROM ghcr.io/astral-sh/uv:0.12.10 AS uv

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
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    /bin/uv sync --frozen --no-dev --no-install-project --no-editable

# --- 2. Install Project (Frequent Change Layer) ---
COPY pyproject.toml uv.lock README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY scripts/generate_python_third_party_notices.py ./scripts/
COPY src ./src

# Install the project non-editably so the environment does not point back to /app/src.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    /bin/uv sync --frozen --no-dev --no-editable

# Inventory the exact Python environment that will cross the image boundary. The
# pure-Python psycopg package uses the runner's system libpq; its bundled-binary
# distribution remains forbidden until its transitive native payload is audited.
RUN /app/.venv/bin/python scripts/generate_python_third_party_notices.py \
    --output /app/PYTHON_THIRD_PARTY_NOTICES.txt \
    --forbid-distribution psycopg-binary

# ==============================================================================
# STAGE II: RUNNER (The Production Artifact)
# ==============================================================================
FROM python:3.13-slim-bookworm

ARG VCS_REF=unknown
LABEL org.opencontainers.image.source="https://github.com/hexanomicon/lychd" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="MPL-2.0"

# Psycopg deliberately uses the pure-Python implementation plus Debian's
# dynamically loaded libpq. Debian retains the package copyright record under
# /usr/share/doc/libpq5/copyright.
RUN apt-get update && \
    apt-get install --yes --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# --- Layer 1: The Prisoner (Identity Setup) ---
# We create a dedicated, unprivileged system user.
# Reference: ADR 09 [Security] - Layer 1.
RUN groupadd --system --gid 1001 lich && \
    useradd --system --uid 1001 --gid 1001 --create-home --home-dir /home/lich lich

# --- Geography (XDG Standards) ---
# We establish Path Symmetry (ADR 13). Regardless of the UID running the process,
# the application logic always looks for its soul in /home/lich.
ENV HOME=/home/lich \
    XDG_CONFIG_HOME=/home/lich/.config \
    XDG_DATA_HOME=/home/lich/.local/share \
    PATH="/app/.venv/bin:$PATH" \
    LITESTAR_APP="lychd.app:create_app" \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# --- The Transplant ---
COPY --from=builder --chown=root:root /app/.venv /app/.venv
COPY --from=builder --chown=root:root /app/LICENSE /app/LICENSE
COPY --from=builder --chown=root:root /app/THIRD_PARTY_NOTICES.md /app/THIRD_PARTY_NOTICES.md
COPY --from=builder --chown=root:root /app/PYTHON_THIRD_PARTY_NOTICES.txt /app/PYTHON_THIRD_PARTY_NOTICES.txt

# --- Layer 4: THE GREAT SEAL (Immutability) ---
# We strip write access (-w) from the entire /app directory.
# Reference: ADR 09 [Security] - Layer 4.
# Root owns the files: neither UID 1000 nor the image's UID 1001 can chmod them writable.
RUN chmod -R a-w /app

# --- Domain and Sphere Preparation ---
# We create the skeletal structure of the Crypt and Codex.
RUN mkdir -p /home/lich/.config/lychd \
             /home/lich/.local/share/lychd/lab \
             /home/lich/.local/share/lychd/extensions \
             /home/lich/library \
             /home/lich/work

# Generated units mount exact host-owned writable paths and provide temporary
# filesystem storage. The image home is traversable; it is not a writable bridge.
RUN chmod -R 755 /home/lich

# --- Layer 1: The Fail-Secure Default ---
# Reference: ADR 09 [Security].
# By default, we run as 'lich' (1001). 
# 1. If run manually (GHCR): Runs as 1001. Non-root, but "Unbound" from host files.
# 2. Generated Quadlets select the invoking host UID with 'User=%U'.
#    Pod-level keep-id maps that UID; mount access remains separately declared.
USER lich

# The threshold of the Sepulcher.
EXPOSE 8000

# The Final Awakening.
CMD ["granian", "--interface", "asgi", "--factory", "--workers", "1", "--host", "0.0.0.0", "--port", "8000", "lychd.app:create_app"]
