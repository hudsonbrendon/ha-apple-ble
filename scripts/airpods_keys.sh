#!/bin/sh
# Print the IRK and EncKey of AirPods paired with this Mac, for the Apple BLE
# options flow. Reads the login-keychain item "MobileBluetooth" (account =
# AirPods classic Bluetooth address); macOS may ask you to allow access.
#
# usage: scripts/airpods_keys.sh [AA:BB:CC:DD:EE:FF]
set -eu
addr=${1:-$(system_profiler SPBluetoothDataType 2>/dev/null |
  awk '/AirPods/{f=1} f&&/Address:/{print $2; exit}')}
[ -n "$addr" ] || { echo "No AirPods found; pass the address." >&2; exit 1; }
echo "AirPods $addr"
security find-generic-password -s MobileBluetooth -a "$addr" -w |
  xxd -r -p |
  plutil -convert json -o - - |
  python3 -c 'import json,sys; d=json.load(sys.stdin)
print("IRK     ", d["MagicAccIRK"]); print("EncKey  ", d["MagicAccEncKey"])'
