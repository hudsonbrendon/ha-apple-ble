# Changelog

## 0.1.3 - Unreleased

- Target Home Assistant 2026.10 / Python 3.14 (HACS floor 2025.6.0).
- Store the coordinator in `entry.runtime_data` instead of `hass.data`.
- Platforms use `AddConfigEntryEntitiesCallback` and declare `PARALLEL_UPDATES`.
- Add diagnostics, `quality_scale.yaml`, `integration_type` and `loggers` in the manifest.
- Tooling: ruff config, tests on Python 3.14 with `pytest-homeassistant-custom-component==0.13.375`, release workflow.
