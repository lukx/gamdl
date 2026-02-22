# --- Stage 1: Build the Python environment ---
FROM python:3.12-slim AS python-builder

WORKDIR /build
COPY . .
RUN pip install --no-cache-dir --user .

# --- Stage 2: Build Bento4 (mp4decrypt) ---
FROM python:3.12-slim AS bento4-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    cmake \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/axiomatic-systems/Bento4.git /tmp/bento4 && \
    cd /tmp/bento4 && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make mp4decrypt

# --- Stage 3: Build GPAC (MP4Box) ---
FROM python:3.12-slim AS gpac-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    pkg-config \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/gpac/gpac.git /tmp/gpac && \
    cd /tmp/gpac && \
    ./configure --static-bin && \
    make -j$(nproc)

# --- Stage 4: Fetch N_m3u8DL-RE ---
FROM python:3.12-slim AS fetcher

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    jq \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
    N_M3U8_ARCH="linux-x64"; \
    elif [ "$ARCH" = "arm64" ]; then \
    N_M3U8_ARCH="linux-arm64"; \
    else \
    echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    DOWNLOAD_URL=$(curl -s https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest | jq -r ".assets[] | select(.name | contains(\"${N_M3U8_ARCH}\") and (contains(\"musl\") | not)) | .browser_download_url") && \
    curl -L "$DOWNLOAD_URL" -o /tmp/nm3u8.tar.gz && \
    tar -xzf /tmp/nm3u8.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/N_m3u8DL-RE

# --- Final Stage: Runtime ---
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only
# Note: libicu72 is the standard for Debian Bookworm (Python 3.12-slim base)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    libicu76 \
    && rm -rf /var/lib/apt/lists/*

# Copy binaries from previous stages
COPY --from=bento4-builder /tmp/bento4/build/mp4decrypt /usr/local/bin/
COPY --from=gpac-builder /tmp/gpac/bin/gcc/MP4Box /usr/local/bin/
COPY --from=fetcher /usr/local/bin/N_m3u8DL-RE /usr/local/bin/

# Copy Python packages from builder
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

ENTRYPOINT ["gamdl"]
