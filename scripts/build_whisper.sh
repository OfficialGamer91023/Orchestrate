#!/usr/bin/env bash
# Build whisper.cpp and download the base English model.
# Run from the project root: bash scripts/build_whisper.sh

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)/backend"
WHISPER_DIR="$BACKEND_DIR/whisper.cpp"

echo "=== Building whisper.cpp ==="

# Clone if not present
if [ ! -d "$WHISPER_DIR" ]; then
    echo "Cloning whisper.cpp..."
    git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
fi

# Build
cd "$WHISPER_DIR"
echo "Compiling..."
make -j$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)

# Download model
echo "Downloading base.en model..."
bash ./models/download-ggml-model.sh base.en

echo "=== whisper.cpp build complete ==="
echo "Binary: $WHISPER_DIR/main"
echo "Model: $WHISPER_DIR/models/ggml-base.en.bin"
