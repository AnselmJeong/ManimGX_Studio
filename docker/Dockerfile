# ManimGX from PyPI, with a GPU to draw on: Mesa's lavapipe on the CPU, or the machine's GPU
# when the container is given one (--device /dev/dri for AMD and Intel, --gpus all for NVIDIA).
#
#   docker run --rm -v "$PWD:/work" ghcr.io/academa-labs/manimgx render scene.py
#
# Build a release with `just build-docker-image VERSION` (VERSION unset: the latest): this folder
# is its context, as it installs ManimGX from PyPI.

# Mount this pinned installer only while adding Python packages.
FROM ghcr.io/astral-sh/uv:0.12.19 AS uv
FROM python:3.14-slim-trixie AS runtime

# Vulkan's loader and Mesa's drivers (lavapipe on the CPU; RADV, ANV, NVK on /dev/dri); NVIDIA's
# driver, which the NVIDIA Container Toolkit mounts in, needs libEGL and libXext to start
RUN apt-get update \
 && apt-get install -y --no-install-recommends libvulkan1 mesa-vulkan-drivers libegl1 libxext6 \
 && rm -rf /var/lib/apt/lists/*

# the python image ships its standard library without bytecode, and every run starts fresh
RUN python -m compileall -q /usr/local/lib

# NVIDIA's Vulkan driver comes with `graphics`, its shader compiler with `compute`; no
# __pycache__ in the mounted project; caches (Mesa's) where any --user can write
ENV NVIDIA_DRIVER_CAPABILITIES=all \
    PYTHONDONTWRITEBYTECODE=1 \
    XDG_CACHE_HOME=/tmp/.cache
WORKDIR /work
ENTRYPOINT ["manimgx"]
CMD ["--help"]

# The release builds from its tested wheels before publishing anything. Runtime dependencies
# follow the same frozen lock; the read-only mount leaves no wheel copies in the final image.
FROM runtime AS release
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=bind,source=wheels,target=/wheels \
    uv pip install --system --no-cache --compile-bytecode --no-deps \
      --require-hashes --requirements /wheels/requirements.txt \
 && uv pip install --system --no-cache --compile-bytecode --no-deps /wheels/*.whl

# The ordinary local command installs an existing PyPI release (unset: the latest).
FROM runtime AS published
ARG VERSION
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    uv pip install --system --no-cache --compile-bytecode "manimgx${VERSION:+==$VERSION}"
