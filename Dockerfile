FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PRUSASLICER_PATH=/usr/local/bin/prusa-slicer

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl wget bash \
        libgl1 libglu1-mesa libgtk-3-0 libwebkit2gtk-4.0-37 \
        libxkbcommon0 libdbus-1-3 libegl1 libopengl0 \
        libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
        fuse libfuse2 \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    PS_VERSION="2.7.4"; \
    PS_URL="https://github.com/prusa3d/PrusaSlicer/releases/download/version_${PS_VERSION}/PrusaSlicer-${PS_VERSION}+linux-x64-GTK3-202404050928.AppImage"; \
    wget -qO /tmp/PrusaSlicer.AppImage "$PS_URL"; \
    chmod +x /tmp/PrusaSlicer.AppImage; \
    cd /opt && /tmp/PrusaSlicer.AppImage --appimage-extract >/dev/null; \
    mv /opt/squashfs-root /opt/prusaslicer; \
    ln -sf /opt/prusaslicer/AppRun /usr/local/bin/prusa-slicer; \
    rm -f /tmp/PrusaSlicer.AppImage

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x scripts/start.sh

EXPOSE 8000

CMD ["./scripts/start.sh"]
