#!/usr/bin/env bash
# setup_pi.sh: provision a fresh Raspberry Pi for pi-rf-monitor
# run from a clone of the repo without sudo:
#   ./scripts/setup_pi.sh
# re-runs are safe, each step is designed to skip checks already done.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_DIR/edge/.venv"
MIN_PYTHON="3.13"
PACKAGES=(git python3-venv python3-pip ufw build-essential cmake)

log() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }
apt_get() {
  sudo env DEBIAN_FRONTEND=noninteractive apt-get -y \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold "$@"
}

# safety checks
[[ $EUID -ne 0 ]] || die "Run as your normal user, not root. The script uses sudo where needed."
[[ -f "$REPO_DIR/edge/pyproject.toml" ]] || die "Can't find edge/pyproject.toml. Run this from a clone of pi-rf-monitor."
sudo -v  # ask for the sudo password once, up front

# system updates
log "Updating system packages"
apt_get update
apt_get full-upgrade

# base packages
log "Installing base packages: ${PACKAGES[*]}"
apt_get install "${PACKAGES[@]}"

# ufw: deny everything incoming except rate-limited SSH
log "Configuring ufw firewall"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw limit 22/tcp comment 'SSH (rate-limited)'   # allow SSH BEFORE enabling
sudo ufw --force enable

# verify SSH hardening
log "Checking SSH hardening"
sshd_config="$(sudo sshd -T)"
grep -qx 'passwordauthentication no' <<<"$sshd_config" \
  || die "SSH password login is still enabled. Re-flash with public-key-only SSH, or set 'PasswordAuthentication no'."
if grep -qx 'permitrootlogin yes' <<<"$sshd_config"; then
  die "SSH allows root login. Set 'PermitRootLogin no' in /etc/ssh/sshd_config."
fi
echo "Password login is disabled."

# project python environment
log "Setting up the Python environment"
python3 -c "import sys; sys.exit(sys.version_info < tuple(map(int, '$MIN_PYTHON'.split('.'))))" \
  || die "Python $MIN_PYTHON+ is required; found $(python3 --version)."
[[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -e "$REPO_DIR/edge[dev]"
"$VENV_DIR/bin/python" -c "import rfmon" || die "The rfmon package didn't import after install."

# summary
log "Done"
sudo ufw status verbose
echo "Python:      $("$VENV_DIR/bin/python" --version)"
echo "Virtualenv:  $VENV_DIR"
echo "CPU temp:    $(vcgencmd measure_temp 2>/dev/null || echo 'n/a')"
echo
echo "Activate the environment with:  source edge/.venv/bin/activate"
