#!/usr/bin/env bash
# install_capture_service.sh: run rfmon capture at boot with systemd.
# run from a clone of the repo without sudo, after setup_pi.sh and install_rtlsdr.sh:
#   ./scripts/install_capture_service.sh
# re-runs are safe: the unit is rewritten, but existing settings are kept.

set -euo pipefail

if [ "${EUID:-$(id -u)}" -eq 0 ]; then
    echo "Error: do not run this script as root; it will ask for sudo." >&2
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="$(id -un)"
UNIT_SRC="$REPO_DIR/scripts/systemd/rfmon-capture.service"
ENV_SRC="$REPO_DIR/scripts/systemd/rfmon-capture.env"
UNIT_DST=/etc/systemd/system/rfmon-capture.service
ENV_DST=/etc/default/rfmon-capture

log() { printf '\n==> %s\n' "$*"; }

# the service runs rfmon from the venv and needs rtl_sdr, so check both first
[[ -x "$REPO_DIR/edge/.venv/bin/rfmon" ]] || { echo "Run setup_pi.sh first." >&2; exit 1; }
command -v rtl_sdr > /dev/null || { echo "Run install_rtlsdr.sh first." >&2; exit 1; }

sudo -v  # ask for the password once, up front

log "Installing $UNIT_DST (user $RUN_USER, repo $REPO_DIR)"
sed -e "s|@USER@|$RUN_USER|g" -e "s|@REPO@|$REPO_DIR|g" "$UNIT_SRC" \
    | sudo tee "$UNIT_DST" > /dev/null

if [[ -f "$ENV_DST" ]]; then
    log "Keeping existing settings in $ENV_DST"
else
    log "Installing default settings to $ENV_DST"
    sudo cp "$ENV_SRC" "$ENV_DST"
fi

log "Enabling the service for every boot"
sudo systemctl daemon-reload
sudo systemctl enable rfmon-capture.service

log "Recording one capture now to test it"
if sudo systemctl start rfmon-capture.service; then
    systemctl status rfmon-capture.service --no-pager --lines=5 || true
    echo
    echo "Done. Captures go to $REPO_DIR/data/captures/."
    echo "Change the station in $ENV_DST, then: sudo systemctl start rfmon-capture"
else
    echo "The test capture failed. See: journalctl -u rfmon-capture -n 30" >&2
    exit 1
fi