#!/usr/bin/env bash
# Read-only: no gpio export, I2C transactions, pinmux writes or resets.
set -eu
printf 'MODEL\n'
tr -d '\0' </proc/device-tree/model
printf '\nKERNEL\n'
uname -r
printf 'OVERLAY CONFIG\n'
cat /boot/dtb/amlogic/kvim3l.dtb.overlay.env
printf 'AVAILABLE OVERLAYS\n'
find /boot/overlays/kvim3l.dtb.overlays -maxdepth 1 -type f -printf '%f\n' | sort
printf 'HEADER PINMUX\n'
grep -E 'GPIO(H_[4567]|Z_15|A_(1|2|3|4|14|15))\)' \
  /sys/kernel/debug/pinctrl/pinctrl@ff634480-pinctrl-meson/pinmux-pins
printf 'I2S OVERLAY\n'
dtc -I dtb -O dts /boot/overlays/kvim3l.dtb.overlays/i2s.dtbo 2>/dev/null
printf 'UART OVERLAY\n'
dtc -I dtb -O dts /boot/overlays/kvim3l.dtb.overlays/uart3.dtbo 2>/dev/null
printf 'CURRENT DEVICE NODES\n'
ls /dev/ttyS* /dev/i2c-*
printf 'SOUND CARDS\n'
cat /proc/asound/cards
