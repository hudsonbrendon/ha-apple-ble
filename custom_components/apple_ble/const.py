"""Constants for the apple_ble integration."""

DOMAIN = "apple_ble"

# Config entry data keys.
CONF_MODEL = "model"  # pinned AirPods model name, or "" for auto (strongest RSSI)
CONF_RSSI_FLOOR = "rssi_floor"
# Options: per-AirPods keys (Mac keychain "MobileBluetooth" item).
CONF_IRK = "irk"  # MagicAccIRK -> identify *your* AirPods despite MAC rotation
CONF_ENC_KEY = "enc_key"  # MagicAccEncKey -> exact battery %, connected host

DEFAULT_RSSI_FLOOR = -75  # ignore adverts weaker than this (dBm)

# Auto-discovery only fires for AirPods this close, so a neighbour's distant
# AirPods don't get auto-pinned. Manual setup is not subject to this floor.
DISCOVERY_RSSI_FLOOR = -55

# Drop the cached AirPods state if no advert seen within this many seconds.
# Used by the coordinator's auto-mode staleness reset (and will also serve Part C presence expiry).
STALE_AFTER_SECONDS = 60

# How often to (re)attach to ESPHome proxy connections.
TAP_REFRESH_SECONDS = 30
