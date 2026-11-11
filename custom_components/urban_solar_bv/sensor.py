import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass as DC, SensorEntity, SensorStateClass as SC
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util

from . import parse_local
from .const import *


def _independance(d):
    total = d["decharge_hp"] + d["decharge_hc"] + d["reseau_hp"] + d["reseau_hc"]
    return 100 * (d["decharge_hp"] + d["decharge_hc"]) / total if total else None


SENSORS = (
    # (clé, nom, unité, device_class, state_class, valeur(data))
    ("stock", "Stock batterie virtuelle", "kWh", DC.ENERGY_STORAGE, SC.MEASUREMENT, lambda d: d["stock"]),
    ("charge", "Charge batterie virtuelle", "kWh", DC.ENERGY, SC.TOTAL_INCREASING, lambda d: d["charge"]),
    ("decharge", "Décharge batterie virtuelle", "kWh", DC.ENERGY, SC.TOTAL_INCREASING,
     lambda d: d["decharge_hp"] + d["decharge_hc"]),
    ("reseau_hp", "Import réseau HP", "kWh", DC.ENERGY, SC.TOTAL_INCREASING, lambda d: d["reseau_hp"]),
    ("reseau_hc", "Import réseau HC", "kWh", DC.ENERGY, SC.TOTAL_INCREASING, lambda d: d["reseau_hc"]),
    ("cout_destockage", "Coût déstockage", "EUR", DC.MONETARY, SC.TOTAL,
     lambda d: d["cout"]),
    ("economies", "Économies batterie virtuelle", "EUR", DC.MONETARY, SC.TOTAL,
     lambda d: d["economies"]),
    ("independance", "Indépendance réseau", "%", None, SC.MEASUREMENT, _independance),
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(UrbanSolarSensor(entry, *s) for s in SENSORS)
    entity_platform.async_get_current_platform().async_register_entity_service(
        "calibrer",
        {vol.Required("niveau"): vol.Coerce(float), vol.Optional("date_releve"): cv.datetime},
        "async_calibrer",
    )


class UrbanSolarSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, entry, key, name, unit, device_class, state_class, value):
        self._battery = entry.runtime_data
        self._value = value
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Batterie virtuelle Urban Solar",
            manufacturer="Urban Solar",
            model="Batterie virtuelle",
            configuration_url="https://github.com/HTModeLia/Battery_ub_2",
        )

    async def async_added_to_hass(self):
        self.async_on_remove(self._battery.add_listener(self.async_write_ha_state))

    @property
    def native_value(self):
        value = self._value(self._battery.data)
        return None if value is None else round(value, 3)

    async def async_calibrer(self, niveau, date_releve=None):
        when = parse_local(date_releve) if date_releve else dt_util.utcnow()
        await self._battery.async_calibrate(niveau, when)
