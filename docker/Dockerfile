# ---------------------------------------------------------------------------
# base: runtime essentials shared by every downstream stage.
# ---------------------------------------------------------------------------
FROM ros:humble-ros-base AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    ROS_LOCALHOST_ONLY=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip \
        python3-colcon-common-extensions \
        build-essential \
        git \
        cmake \
        ros-humble-rclpy \
        ros-humble-std-msgs \
        ros-humble-geometry-msgs \
        ros-humble-sensor-msgs \
        ros-humble-nav-msgs \
        ros-humble-example-interfaces \
        ros-humble-lifecycle-msgs \
 && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# dev: adds an isolated venv with linters/test tools on top of base.
# ---------------------------------------------------------------------------
FROM base AS dev

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-venv \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv --system-site-packages /opt/devtools \
 && /opt/devtools/bin/pip install \
        "ruff==0.15.*" \
        "pylint==3.2.*" \
        "pytest==8.*" \
        "hypothesis==6.*"

ENV PATH=/opt/devtools/bin:$PATH

WORKDIR /workspace

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Non-root for safety; workspace volume will be mounted rw.
RUN useradd -m -u 1000 runner && chown -R runner:runner /workspace
USER runner

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
