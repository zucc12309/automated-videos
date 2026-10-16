#!/usr/bin/env bash
# Download Kokoro v1.0 (Kokoro-82M weights + voice pack, including am_adam) for the onnxruntime engine and verify checksums.
# Source: github.com/thewh1teagle/kokoro-onnx release "model-files-v1.0" (ONNX conversion of hexgrad/Kokoro-82M, Apache-2.0).
set -euo pipefail
DIR="${KOKORO_ONNX_DIR:-$(cd "$(dirname "$0")/.." && pwd)/data/models/kokoro-onnx}"
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
mkdir -p "$DIR"
# name sha256 (portable to macOS bash 3.2: no associative arrays)
while read -r f sum; do
  if [ ! -f "$DIR/$f" ]; then curl -fL --retry 3 -o "$DIR/$f" "$BASE/$f"; fi
  got=$( (command -v sha256sum >/dev/null && sha256sum "$DIR/$f" || shasum -a 256 "$DIR/$f") | cut -d' ' -f1)
  [ "$got" = "$sum" ] || { echo "checksum mismatch for $f" >&2; exit 1; }
  echo "ok $f"
done <<'LIST'
kokoro-v1.0.onnx 7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5
voices-v1.0.bin bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d
LIST
