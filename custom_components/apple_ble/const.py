"""Constants for the apple_ble integration."""

DOMAIN = "apple_ble"

# Config entry data keys.
CONF_MODEL = "model"          # pinned AirPods model name, or "" for auto (strongest RSSI)
CONF_RSSI_FLOOR = "rssi_floor"

DEFAULT_RSSI_FLOOR = -75      # ignore adverts weaker than this (dBm)

# Drop the cached AirPods state if no advert seen within this many seconds.
# Used by the coordinator's auto-mode staleness reset (and will also serve Part C presence expiry).
STALE_AFTER_SECONDS = 60
