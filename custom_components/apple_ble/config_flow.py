"""Config flow for Apple BLE — stub (full implementation in B7)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from apple_ble import APPLE_MANUFACTURER_ID, MODEL_BY_CHAR, parse_proximity_pairing

from .const import CONF_MODEL, CONF_RSSI_FLOOR, DEFAULT_RSSI_FLOOR, DOMAIN

# "" = auto (strongest RSSI). Other values pin a specific model.
_MODEL_CHOICES = ["", *sorted(set(MODEL_BY_CHAR.values()))]


def _unique_id(model: str) -> str:
    return f"{DOMAIN}_{(model or 'auto').lower().replace(' ', '_').replace('(', '').replace(')', '')}"


def _title(model: str) -> str:
    return model or "AirPods (auto)"


class AppleBleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apple BLE."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_model: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Triggered automatically when an Apple AirPods advert is seen."""
        payload = (discovery_info.manufacturer_data or {}).get(APPLE_MANUFACTURER_ID)
        parsed = parse_proximity_pairing(bytes(payload)) if payload else None
        if parsed is None:
            return self.async_abort(reason="not_airpods")
        self._discovered_model = parsed.model
        await self.async_set_unique_id(_unique_id(parsed.model))
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": parsed.model}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding the discovered AirPods (pinned to its model)."""
        model = self._discovered_model or ""
        if user_input is not None:
            return self.async_create_entry(
                title=_title(model),
                data={CONF_MODEL: model, CONF_RSSI_FLOOR: DEFAULT_RSSI_FLOOR},
            )
        return self.async_show_form(
            step_id="confirm", description_placeholders={"model": model}
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual setup: choose auto (strongest RSSI) or pin a model."""
        if user_input is not None:
            model = user_input[CONF_MODEL]
            await self.async_set_unique_id(_unique_id(model))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=_title(model),
                data={CONF_MODEL: model, CONF_RSSI_FLOOR: DEFAULT_RSSI_FLOOR},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_MODEL, default=""): vol.In(_MODEL_CHOICES)}
            ),
        )
