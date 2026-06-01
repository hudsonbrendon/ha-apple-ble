"""Battery and diagnostic sensors for Apple BLE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

if TYPE_CHECKING:
    from apple_ble import AirPodsData

from .const import DOMAIN
from .coordinator import AppleBleCoordinator
from .entity import AppleBleEntity


@dataclass(frozen=True, kw_only=True)
class AppleBleSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    value_fn: Callable[[AppleBleCoordinator], int | str | None]


def _battery(field: str) -> Callable[[AppleBleCoordinator], int | None]:
    def _get(coord: AppleBleCoordinator) -> int | None:
        data: AirPodsData | None = coord.data
        return getattr(data, field) if data is not None else None

    return _get


SENSORS: tuple[AppleBleSensorDescription, ...] = (
    AppleBleSensorDescription(
        key="left_battery",
        translation_key="left_battery",
        name="Left battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_battery("left_battery"),
    ),
    AppleBleSensorDescription(
        key="right_battery",
        translation_key="right_battery",
        name="Right battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_battery("right_battery"),
    ),
    AppleBleSensorDescription(
        key="case_battery",
        translation_key="case_battery",
        name="Case battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_battery("case_battery"),
    ),
    AppleBleSensorDescription(
        key="rssi",
        translation_key="rssi",
        name="Signal strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda coord: coord.best_rssi,
    ),
    AppleBleSensorDescription(
        key="apple_devices_nearby",
        translation_key="apple_devices_nearby",
        name="Apple devices nearby",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coord: coord.apple_devices_nearby,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Apple BLE sensors."""
    coordinator: AppleBleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AppleBleSensor(coordinator, entry.entry_id, entry.title, desc)
        for desc in SENSORS
    )


class AppleBleSensor(AppleBleEntity, SensorEntity):
    """A single Apple BLE sensor."""

    entity_description: AppleBleSensorDescription

    def __init__(
        self,
        coordinator: AppleBleCoordinator,
        entry_id: str,
        title: str,
        description: AppleBleSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, title)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> int | str | None:
        return self.entity_description.value_fn(self.coordinator)
