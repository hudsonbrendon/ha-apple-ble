# Apple BLE for Home Assistant

Passively read **AirPods battery** (case / left / right + charging) and detect
nearby Apple devices over Bluetooth — using your ESP32 ESPHome bluetooth_proxy
and/or the HA host's built-in adapter. No pairing, no cloud, `local_push`.

## Install (HACS)
1. HACS → Integrations → custom repository → `hudsonbrendon/ha-apple-ble`.
2. Restart Home Assistant.
3. Settings → Devices & Services → **Add Integration** → *Apple BLE*.
   Open your AirPods lid nearby; it will be auto-discovered, or add it manually
   (leave model empty for auto, or pin a model).

## Entities
- `sensor.*_left_battery`, `*_right_battery`, `*_case_battery` (%)
- `binary_sensor.*_left_charging`, `*_right_charging`, `*_case_charging`
- `sensor.*_signal_strength` (RSSI, diagnostic, disabled by default)

## Limitations
- Only AirPods expose battery over BLE; Apple Watch / iPhone do not (BLE can
  only confirm an Apple device is *nearby*).
- Apple rotates the BLE MAC (~15 min); "your" AirPods are matched by model +
  strongest RSSI. Two identical models close together can be ambiguous.
- Battery is reported in 10% steps.

Built on [`apple-ble`](https://github.com/hudsonbrendon/apple-ble).
