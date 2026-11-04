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

## How it gets the data (important on HA 2026.x)

Home Assistant's Bluetooth stack (`habluetooth`) silently **drops** Apple
adverts whose first byte isn't `0x02/0x06/0x10/0x11/0x12` — AirPods
proximity-pairing adverts (`0x07`) never reach any integration. Apple BLE
therefore also reads the raw advert stream that every **ESPHome Bluetooth
proxy** already sends to HA (a passive second handler on the same API
connection — no extra subscription). **You need an ESPHome Bluetooth proxy in
range**; the HA host's own adapter can't see AirPods while that filter exists.

## Exact battery % and "your" AirPods only (optional keys)

The advert has a clear half (battery in 10 % steps, charging, in-ear, case) and a
16-byte half encrypted with a per-AirPods key that every paired Apple device
holds. On a Mac that paired with the AirPods, run:

```sh
scripts/airpods_keys.sh          # reads keychain item "MobileBluetooth"
```

and paste both values in **Settings → Devices & Services → Apple BLE →
Configure**:

- **IRK** (`MagicAccIRK`) — resolves the rotating BLE address, so only *your*
  AirPods are tracked (no RSSI guessing, neighbours ignored).
- **EncKey** (`MagicAccEncKey`) — decrypts exact 1 % battery for left / right /
  case and the device they're connected to.

Keys stay in your HA config entry; nothing leaves your network.

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
| `sensor.<name>_pods_in_case` | How many earbuds are in the case (0–2). |
| `sensor.<name>_connected_to` | Last 3 bytes of the BT address of the device the AirPods are connected to (needs EncKey). Diagnostic. |
| `sensor.<name>_signal_strength` | Bluetooth RSSI (dBm). Diagnostic, disabled by default. |
| `sensor.<name>_apple_devices_nearby` | Count of distinct Apple devices seen recently. Diagnostic. |

### Binary sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.<name>_case_charging` | On while the case is charging. |
| `binary_sensor.<name>_left_charging` | On while the left earbud is charging. |
| `binary_sensor.<name>_right_charging` | On while the right earbud is charging. |
| `binary_sensor.<name>_left_in_ear` / `_right_in_ear` | Earbud is in an ear. |
| `binary_sensor.<name>_case_lid` | Case lid open/closed while a bud is in the case; unknown with both buds in your ears. |
| `binary_sensor.<name>_apple_device_nearby` | On while any Apple device is nearby. |

## Scope & limitations

- **When AirPods advertise.** Out of the case (in your ears) they advertise about
  once a second; in a closed case they go quiet, so entities hold the last value.
  Opening the lid refreshes them.
- **Only AirPods expose battery.** Apple Watch / iPhone / Mac do **not** broadcast
  battery over BLE — they only contribute to the coarse "Apple device nearby"
  presence signal.
- **MAC randomization.** Apple rotates the BLE MAC (~15 min). Without the IRK
  "your" AirPods are matched by model + strongest RSSI; with the IRK they are
  identified exactly.
- **Auto-discovery** relies on HA's Bluetooth matcher, which the filter above
  blocks; add the integration manually.

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
