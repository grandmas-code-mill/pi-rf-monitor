# Raspberry Pi Setup

How to take a blank USB drive to a provisioned pi-rf-monitor edge device, using only this guide and the scripts in the repo.

## 1. Hardware

- Raspberry Pi 5 with the Active Cooler
- Official 27W USB-C power supply (weaker supplies can't power a USB boot drive)
- USB 3.0 flash drive, 32GB or larger
- Ethernet cable (recommended for the first boot)

The Pi 5 boots from USB when no microSD card is inserted, so no SD card or card reader is needed.

## 2. Generate an SSH key on your computer

The Pi will accept key-based logins only. Create a key on the computer you'll connect from:

```bash
ssh-keygen -t ed25519 -C "you@pi-rf-monitor"
```

Accept the default location and set a passphrase. This creates `~/.ssh/id_ed25519` (private, never share it) and `~/.ssh/id_ed25519.pub` (public, goes on the Pi).

## 3. Flash the OS with Raspberry Pi Imager

Choose Raspberry Pi 5, a Raspberry Pi OS image, and the USB drive. In the customization settings:

- **Hostname:** for example `raspberry-pi`
- **Username:** your choice
- **Timezone and keyboard:** your locale
- **Wi-Fi:** only if you won't use Ethernet
- **SSH:** enabled, **public-key authentication only**, with the contents of `id_ed25519.pub` pasted in

Public-key only means password logins are disabled from the first boot.

## 4. First boot and connect

Plug in the drive, Ethernet, and power. The first boot takes a minute or two while the Pi applies your settings.

```bash
ssh <user>@raspberry-pi.local
```

Answer `yes` to the fingerprint prompt the first time. If `.local` names don't resolve on your network, find the Pi's IP address in your router's connected-devices list and use that instead.

**Optional shortcut.** Add this to `~/.ssh/config` on your computer (create the file if it doesn't exist) so that `ssh rfmon` works:

```
Host rfmon
    HostName raspberry-pi.local
    User <user>
    IdentityFile ~/.ssh/id_ed25519
```

The rest of this guide uses `rfmon` as that alias.

## 5. Verify password login is disabled

From your computer:

```bash
ssh -o PubkeyAuthentication=no rfmon
```

This should be refused with `Permission denied (publickey)`. If it asks for a password instead, re-flash with public-key-only SSH.

## 6. Clone the repo on the Pi

```bash
ssh rfmon
git --version || sudo apt install -y git
cd ~
git clone https://github.com/grandmas-code-mill/pi-rf-monitor.git
cd pi-rf-monitor
```

Use the HTTPS URL. The repo is public, so cloning needs no GitHub login. The Pi only pulls; changes are made through pull requests.

## 7. Run the setup script

From the repo root, as your normal user (not with `sudo`):

```bash
./scripts/setup_pi.sh
```

It updates the system, installs base packages, enables a ufw firewall that allows only rate-limited SSH, checks that SSH password login is disabled, and creates the project's Python environment in `edge/.venv`. The first run takes a while because of the system update. The script is safe to re-run; a second run should finish cleanly with nothing new to do.

## 8. Download the recordings and run the tests

```bash
./scripts/fetch_samples.sh
edge/.venv/bin/pytest edge
edge/.venv/bin/rfmon --version
```

Each recording should report `OK` against its checksum, and all tests should pass, including the real-recording tests that skip in CI.

## 9. RTL-SDR drivers (coming with the receiver)

`scripts/install_rtlsdr.sh` will install the RTL-SDR drivers and block the default TV-tuner driver that claims the dongle. It will be added once the receiver arrives.

## Updating the Pi

```bash
cd ~/pi-rf-monitor
git pull
./scripts/setup_pi.sh
```

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `ssh rfmon` doesn't connect, but `ssh <user>@raspberry-pi.local` does | The config file was saved as `config.txt` (common with Notepad), so SSH ignores it | Rename it to exactly `config` with no extension; check with `ssh -G rfmon` |
| `Permission denied (publickey)` when cloning | The `git@github.com:...` SSH URL needs a key registered with GitHub | Clone with the `https://github.com/...` URL instead |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Re-flashing gave the Pi a new host key | `ssh-keygen -R raspberry-pi.local`, then connect again |
| `Permission denied` running a script | The executable bit isn't set in your clone | `git pull` the latest version, or run it with `bash scripts/<name>.sh` |
| `git pull` refuses: local changes would be overwritten | A file was edited or `chmod`ed on the Pi | `git restore .`, then `git pull` |
| The fan spins at boot, then stops | Normal: the Active Cooler only runs once the CPU warms up (around 50°C) | Nothing to fix; check with `vcgencmd measure_temp` |
