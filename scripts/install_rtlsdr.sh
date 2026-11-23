#!/usr/bin/env bash

# RRR (root run refusal)
if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "Error: Do not run this script as root." >&2
  exit 1
fi

sudo -v

# stop pipeline at the first failure
set -euo pipefail

# repository directory variable
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# package manager updates
echo "Retrieving latest package versions..."
sudo apt-get update

# initial package installs
echo "Starting install..."
sudo apt-get -y install rtl-sdr # RTL-SDR components

[[ -x "$REPO_DIR/edge/.venv/bin/pip" ]] || { echo "Run setup_pi.sh first."; exit 1; } # pyrtlsdr install
"$REPO_DIR/edge/.venv/bin/pip" install -e "$REPO_DIR/edge[sdr]"

# dvb_usb_rtl28xxu blacklist to prevent blockage on I/O when using RTL-SDR dongle
echo "Blacklisting dvb_usb_rtl28xxu..."

echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtlsdr.conf > /dev/null

# verify dvb_usb_rtl28xxu is loaded and unloads driver from device
if lsmod | grep -q '^dvb_usb_rtl28xxu'; then
  sudo modprobe -r dvb_usb_rtl28xxu
fi

# plugdev permission mod for active user / allows for dongle use w/o sudo
sudo udevadm control --reload-rules && sudo udevadm trigger # reloads USB permissions to prevent need to unplug and replug dongle
sudo usermod -aG plugdev "$(id -un)" # requires logout/login for change to apply

if ! id -nG | grep -qw plugdev; then
  echo "The current user is not a member of \"plugdev\" group yet. Please log back in and re-run install_rtlsdr.sh."
  exit 1
fi

# RTL-SDR installation verification
echo "Testing RTL-SDR..."
rtl_test -t
echo "Note: a single 'lost at least 32 bytes' at the start is normal."
timeout 10 rtl_test -s 2048000 || [[ $? -eq 124 ]]

# closing statements
echo "Done. The RTL-SDR is installed and the TV driver is blocked."
echo "A reboot is recommended so the blacklist applies on every boot."