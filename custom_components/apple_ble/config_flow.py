"""Config flow for Apple BLE."""

from __future__ import annotations

from typing import Any

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
import voluptuous as vol

from apple_ble import (
    APPLE_MANUFACTURER_ID,
    MODEL_BY_CHAR,
    parse_key,
    parse_proximity_pairing,
)

from .const import (
    CONF_ENC_KEY,
    CONF_IRK,
    CONF_MODEL,
    CONF_RSSI_FLOOR,
    DEFAULT_RSSI_FLOOR,
    DISCOVERY_RSSI_FLOOR,
    DOMAIN,
)

# "" = auto (strongest RSSI). Other values pin a specific model.
_MODEL_CHOICES = ["", *sorted(set(MODEL_BY_CHAR.values()))]


def _unique_id(model: str) -> str:
    return f"{DOMAIN}_{(model or 'auto').lower().replace(' ', '_').replace('(', '').replace(')', '')}"


def _title(model: str) -> str:
    return model or "AirPods (auto)"


class AppleBleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apple BLE."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Keys are optional and live in the options flow."""
        return AppleBleOptionsFlow()

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovered_model: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Triggered automatically when an Apple AirPods advert is seen."""
        payload = (discovery_info.manufacturer_data or {}).get(APPLE_MANUFACTURER_ID)
        parsed = parse_proximity_pairing(bytes(payload)) if payload else None
        if parsed is None:
            return self.async_abort(reason="not_airpods")
        # Only auto-discover AirPods that are close by; a neighbour's distant
        # AirPods would otherwise get auto-pinned in a dense RF environment.
        if discovery_info.rssi < DISCOVERY_RSSI_FLOOR:
            return self.async_abort(reason="too_far")
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


class AppleBleOptionsFlow(OptionsFlow):
    """Optional AirPods keys (IRK + EncKey) from the Mac keychain."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the keys; empty fields disable the feature."""
        errors: dict[str, str] = {}
        if user_input is not None:
            for field in (CONF_IRK, CONF_ENC_KEY):
                value = user_input.get(field, "").strip()
                user_input[field] = value
                if value:
                    try:
                        parse_key(value)
                    except ValueError:
                        errors[field] = "invalid_key"
            if not errors:
                return self.async_create_entry(data=user_input)
        current = user_input or self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_IRK, default=current.get(CONF_IRK, "")): str,
                    vol.Optional(
                        CONF_ENC_KEY, default=current.get(CONF_ENC_KEY, "")
                    ): str,
                }
            ),
            errors=errors,
        )
