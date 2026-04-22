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
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    /bin/uv sync --frozen --no-install-project --extra server

# --- 2. Install Project (Frequent Change Layer) ---
COPY . .

# Install the project package itself into the environment with server dependencies.
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    /bin/uv sync --frozen --extra server

# ==============================================================================
# STAGE II: RUNNER (The Production Artifact)
# ==============================================================================
FROM python:3.13-slim-bookworm

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
    PYTHONPATH="/app/src:$PYTHONPATH"

WORKDIR /app

# --- The Transplant ---
COPY --from=builder --chown=lich:lich /app/.venv /app/.venv
COPY --from=builder --chown=lich:lich /app/src /app/src

# --- Layer 4: THE GREAT SEAL (Immutability) ---
# We strip write access (-w) from the entire /app directory.
# Reference: ADR 09 [Security] - Layer 4.
# This ensures that even the 'Magus' (User 1000) cannot modify the Vessel's brain at runtime.
RUN chmod -R a-w /app

# --- Domain and Sphere Preparation ---
# We create the skeletal structure of the Crypt and Codex.
RUN mkdir -p /home/lich/.config/lychd \
             /home/lich/.local/share/lychd/lab \
             /home/lich/.local/share/lychd/extensions \
             /home/lich/library \
             /home/lich/work

# --- THE PERMISSION BRIDGE (Agnosticism) ---
# We make the internal home directory world-writable (777).
#
# WHY? Identity Symmetry (ADR 08/09). 
# At runtime, the Rune Scribe overrides the user to match the host Magus (UID 1000).
# If this directory were hard-owned by 'lich' (1001), the Magus (1000) would be 
# locked out of the internal skeleton before host volumes are mounted. 
# 777 ensures the "Suit of Armor" fits any UID that steps into it.
RUN chmod -R 777 /home/lich && \
    chown -R lich:lich /home/lich

# --- Layer 1: The Fail-Secure Default ---
# Reference: ADR 09 [Security].
# By default, we run as 'lich' (1001). 
# 1. If run manually (GHCR): Runs as 1001. Non-root, but "Unbound" from host files.
# 2. If run via LychD Rune: The Quadlet 'User=%U' overrides this to UID 1000.
#    Combined with 'keep-id', we achieve the "Double Non-Root Bridge."
USER lich

# The threshold of the Sepulcher.
EXPOSE 8000

# The Final Awakening.
CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000", "lychd.app:create_app"]