<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/apple_ble/brand/dark_logo.png">
    <img src="custom_components/apple_ble/brand/logo.png" alt="Apple BLE" width="360">
  </picture>
</p>

# Apple BLE for Home Assistant

[![Tests](https://github.com/hudsonbrendon/ha-apple-ble/actions/workflows/tests.yml/badge.svg)](https://github.com/hudsonbrendon/ha-apple-ble/actions/workflows/tests.yml)
[![Hassfest](https://github.com/hudsonbrendon/ha-apple-ble/actions/workflows/hassfest.yml/badge.svg)](https://github.com/hudsonbrendon/ha-apple-ble/actions/workflows/hassfest.yml)
[![HACS](https://github.com/hudsonbrendon/ha-apple-ble/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/ha-apple-ble/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/ha-apple-ble)](https://github.com/hudsonbrendon/ha-apple-ble/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Passively read **AirPods battery** (case / left / right + charging) and detect
nearby **Apple devices** over Bluetooth LE — through your ESPHome Bluetooth proxy
and/or the Home Assistant host's built-in adapter. No pairing, no cloud,
`local_push`.

The Bluetooth protocol and parsing live in a separate Python library,
[**`apple-ble`**](https://github.com/hudsonbrendon/apple-ble)
([PyPI](https://pypi.org/project/apple-ble/)), which this integration pulls in
automatically via `manifest.json` `requirements`.

## Features

- 🔋 **AirPods battery** — `sensor`s for case, left, and right battery levels.
- ⚡ **Charging** — `binary_sensor`s for case, left, and right charging state.
- 🎧 **Model detection** — AirPods 1/2/3, Pro, Pro 2, Max.
- 🔍 **Automatic discovery** — open your AirPods case lid near Home Assistant and
  they show up as a discovered device (only nearby AirPods are auto-offered, so a
  neighbour's don't get picked up).
- 🏠 **Apple presence** — a coarse "Apple device nearby" `binary_sensor` and a count
  `sensor` (any nearby Apple device — diagnostic, approximate).
- 📶 **Signal strength** — an RSSI `sensor` (diagnostic).
- 🛰️ **Works through ESPHome Bluetooth proxies** — uses Home Assistant's shared
  Bluetooth stack, so your AirPods only need to be near a proxy, not the HA host.
- 🌐 **Localized** — UI translated to English and Português (Brasil).

## Requirements

- Home Assistant **2024.8** or newer.
- A Bluetooth adapter on the Home Assistant host **or** an
  [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html)
  within range.
- AirPods (1st/2nd/3rd gen, Pro, Pro 2, or Max).

## Installation

### HACS (recommended)

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add the repository URL `https://github.com/hudsonbrendon/ha-apple-ble`
   and choose the **Integration** category.
3. Search for **Apple BLE** in HACS, install it, and **restart Home Assistant**.

### Manual

1. Copy `custom_components/apple_ble/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Setup

1. **Open your AirPods case lid** right next to a Bluetooth adapter or proxy —
   that is when AirPods broadcast their battery.
2. Home Assistant discovers them automatically — go to
   **Settings → Devices & Services** and you'll see an **Apple BLE** *Discovered*
   card. Click **Configure → Submit**.
3. If they aren't auto-discovered, add them manually: **Settings → Devices &
   Services → Add Integration → Apple BLE**, and either leave the model empty
   (auto-track the strongest nearby AirPods) or pin a specific model.

## Entities

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.<name>_case_battery` | Case battery level (%). |
| `sensor.<name>_left_battery` | Left earbud battery level (%). |
| `sensor.<name>_right_battery` | Right earbud battery level (%). |
| `sensor.<name>_signal_strength` | Bluetooth RSSI (dBm). Diagnostic, disabled by default. |
| `sensor.<name>_apple_devices_nearby` | Count of distinct Apple devices seen recently. Diagnostic. |

### Binary sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.<name>_case_charging` | On while the case is charging. |
| `binary_sensor.<name>_left_charging` | On while the left earbud is charging. |
| `binary_sensor.<name>_right_charging` | On while the right earbud is charging. |
| `binary_sensor.<name>_apple_device_nearby` | On while any Apple device is nearby. |

## Scope & limitations

- **Battery updates when the lid is open.** AirPods broadcast their battery advert
  reliably only when the case lid is opened (the same moment iOS shows the pairing
  card). In normal use the entities hold the last known value; open the lid near an
  adapter to refresh.
- **Only AirPods expose battery.** Apple Watch / iPhone / Mac do **not** broadcast
  battery over BLE — they only contribute to the coarse "Apple device nearby"
  presence signal.
- **MAC randomization.** Apple rotates the BLE MAC (~15 min) and the advert carries
  no stable id, so "your" AirPods are matched by model + strongest RSSI. Auto-discovery
  is RSSI-gated so a neighbour's distant AirPods aren't picked up.

## Credits

Bluetooth library: [apple-ble](https://github.com/hudsonbrendon/apple-ble).
Continuity reverse-engineering:
[furiousMAC/continuity](https://github.com/furiousMAC/continuity),
[kavishdevar/librepods](https://github.com/kavishdevar/librepods),
[delphiki/AirStatus](https://github.com/delphiki/AirStatus),
[d4rken-org/capod](https://github.com/d4rken-org/capod).
Author [@hudsonbrendon](https://github.com/hudsonbrendon).

## License

MIT — see [LICENSE](LICENSE).
