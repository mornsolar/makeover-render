# Must match the Blender pinned in CI and on developer machines: 5.2 LTS.
# Committed in Phase 0, exercised from Phase 5.
FROM python:3.12-slim-bookworm

ARG BLENDER_SERIES=5.2
ARG BLENDER_VERSION=5.2.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    RENDER_BLENDER_EXECUTABLE=/opt/blender/blender

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

# libx*/libsm are needed even for headless Blender; ffmpeg encodes in Phase 5.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl xz-utils ffmpeg libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libsm6 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://download.blender.org/release/Blender${BLENDER_SERIES}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
      -o /tmp/blender.tar.xz \
    && mkdir -p /opt/blender \
    && tar -xJf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && /opt/blender/blender --version

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY . .
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 renderer
USER renderer

EXPOSE 8081
CMD ["uv", "run", "--no-dev", "uvicorn", "makeover_render.interfaces.api.app:app", \
     "--host", "0.0.0.0", "--port", "8081"]
