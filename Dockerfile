# ─────────────────────────────────────────────────────────────
# Spotify → YouTube Sync — Docker Image
# ─────────────────────────────────────────────────────────────
# Build:  docker build -t spotify-to-youtube-music-sync .
# Run:    docker run --env-file .env spotify-to-youtube-music-sync
#
# Required environment variables (pass via --env-file or -e):
#   SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
#   YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
#   PLAYLIST_ID
#
# Optional:
#   PROCESSED_FILE (default: /data/processed_tracks.json)
#   SEARCH_SUFFIX, MAX_RETRIES, RETRY_BASE_DELAY
#
# Mount a volume for persistent state:
#   docker run --env-file .env -v $(pwd)/data:/data spotify-to-youtube-music-sync
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim

LABEL org.opencontainers.image.title="Spotify → YouTube Sync"
LABEL org.opencontainers.image.description="Automatically mirror Spotify Liked Songs to a YouTube playlist"
LABEL org.opencontainers.image.source="https://github.com/Aakashm18/spotify-to-youtube-music-sync"
LABEL org.opencontainers.image.licenses="MIT"

# System hardening: run as non-root
RUN groupadd -r syncuser && useradd --no-log-init -r -g syncuser syncuser

WORKDIR /app

# Install Python dependencies first (layer cache optimisation)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY youtube.py remove_duplicates.py ./
COPY scripts/ ./scripts/

# Create a writable directory for state persistence
# Mount -v /host/path:/data to persist processed_tracks.json across runs
RUN mkdir -p /data && chown syncuser:syncuser /data

USER syncuser

# Default: point state file to the /data volume
ENV PROCESSED_FILE=/data/processed_tracks.json

# Entry point — pass CLI args as CMD overrides
# e.g. docker run spotify-to-youtube-music-sync --dry-run --verbose
ENTRYPOINT ["python", "youtube.py"]
CMD []
