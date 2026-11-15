#!/usr/bin/env bash
# RPI4b_SETUP.sh: one-time Raspberry Pi 4 Model B setup for SlightlyCutGem.
#
#   1. turns on SPI (ADF4351 synth) and I2C (ADS1115 ADC) with raspi-config
#   2. installs every package the scripts need, from apt
#   3. adds your user to the spi, i2c and gpio groups
#
# Run from the repo folder:   sudo ./RPI4b_SETUP.sh
# Then reboot so SPI, I2C and the group changes take effect.
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "You need to run as root for raspi-config" >&2
    exit 1
fi

if ! command -v raspi-config >/dev/null 2>&1; then
    echo "raspi-config not found: this script is for Raspberry Pi OS." >&2
    exit 1
fi

PACKAGES=(
    python3-spidev      # ADF4351 synth over SPI0
    python3-smbus2      # ADS1115 ADC over I2C1
    python3-gpiozero    # synth CE and lock-detect pins
    python3-lgpio       # gpiozero's backend on Bookworm
    python3-matplotlib  # sweep.py --plot
    python3-rich        # coloured tables in check_hw.py and selftest.py
    i2c-tools           # i2cdetect -y 1
    git
)

echo "==> [1/3] Enabling SPI and I2C"
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0

echo "==> [2/3] Installing packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y "${PACKAGES[@]}"

echo "==> [3/3] Adding your user to the spi, i2c and gpio groups"
TARGET_USER="${SUDO_USER:-}"
if [ -n "$TARGET_USER" ] && [ "$TARGET_USER" != "root" ]; then
    usermod -aG spi,i2c,gpio "$TARGET_USER"
    echo "    added $TARGET_USER"
else
    echo "    skipped: run with sudo from your normal account to have this done for you"
fi

cat <<'DONE'

Setup finished. Reboot so SPI, I2C and the group changes take effect:

    sudo reboot

Then, from the repo folder, as your normal user (no sudo):

    python3 selftest.py          # software check, no hardware needed
    python3 check_hw.py          # hardware check
DONE
