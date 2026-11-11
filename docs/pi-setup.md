# Raspberry Pi Provisioning Steps

- **Hardware**: Pi 5, the official 27W supply, the USB drive, Ethernet
- **Generate an SSH key** on the client (ssh-keygen -t ed25519)
- **Flash the OS with Raspberry Pi Imager**: hostname, username, SSH with public key only, Wi-Fi if used
- **First boot and connect**: ssh user@raspberry-pi.local, plus the ~/.ssh/config entry
- **Verify password login is disabled**: ssh -o PubkeyAuthentication=no rfmon should be refused
- **Run setup_pi.sh** (SCRUM-14)
- **Run install_rtlsdr.sh** (SCRUM-15)
- **Troubleshooting**: the errors you’ve already hit, including the config filename problem
