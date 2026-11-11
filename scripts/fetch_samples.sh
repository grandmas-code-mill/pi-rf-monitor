#!/usr/bin/env bash
# fetch_samples.sh: download the reference IQ recordings into data/samples/ (SCRUM-20).
#
# Run from anywhere inside a clone of the repo:
#   bash scripts/fetch_samples.sh
# Skips files that are already downloaded, then verifies every file against
# scripts/samples.sha256 and exits with an error if any checksum doesn't match.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLES_DIR="$REPO_DIR/data/samples"
CHECKSUMS="$REPO_DIR/scripts/samples.sha256"

# file name -> download URL
declare -A SAMPLES=(
  [fm_rds_250k_1Msamples.iq]="https://raw.githubusercontent.com/777arc/498x/master/fm_rds_250k_1Msamples.iq"
  [modes1.bin]="https://raw.githubusercontent.com/antirez/dump1090/master/testfiles/modes1.bin"
)

log() { printf '==> %s\n' "$*"; }

mkdir -p "$SAMPLES_DIR"

for name in "${!SAMPLES[@]}"; do
  dest="$SAMPLES_DIR/$name"
  if [[ -f "$dest" ]]; then
    log "$name already downloaded, skipping"
    continue
  fi
  log "Downloading $name"
  # Download to a temporary name first so an interrupted download never looks complete.
  curl -fL --retry 3 --progress-bar -o "$dest.part" "${SAMPLES[$name]}"
  mv "$dest.part" "$dest"
done

log "Verifying checksums"
if command -v sha256sum >/dev/null; then
  (cd "$SAMPLES_DIR" && sha256sum -c "$CHECKSUMS")
else
  (cd "$SAMPLES_DIR" && shasum -a 256 -c "$CHECKSUMS")   # macOS
fi

log "Recordings are ready in data/samples/"
