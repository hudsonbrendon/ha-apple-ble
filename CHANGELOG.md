# Changelog

## 0.2.0 - Unreleased

- Read AirPods adverts directly from ESPHome Bluetooth proxies: HA's
  habluetooth drops Apple `0x07` adverts before integrations see them.
- Optional IRK + EncKey (options flow, `scripts/airpods_keys.sh` for macOS):
  exact 1 % battery, connected-device suffix, pin your own AirPods.
- New entities: left/right in ear, case lid, pods in case, connected to.
- Battery/charging/lid keep the last known value when a bud goes silent
  (closed case). Entity names translated (en, pt-BR).
- Requires `apple-ble==0.2.0`.

## 0.1.3 - Unreleased

- Target Home Assistant 2026.10 / Python 3.14 (HACS floor 2025.6.0).
- Store the coordinator in `entry.runtime_data` instead of `hass.data`.
- Platforms use `AddConfigEntryEntitiesCallback` and declare `PARALLEL_UPDATES`.
- Add diagnostics, `quality_scale.yaml`, `integration_type` and `loggers` in the manifest.
- Tooling: ruff config, tests on Python 3.14 with `pytest-homeassistant-custom-component==0.13.375`, release workflow.
