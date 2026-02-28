from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import DeviceInfo # <--- Ajouté
from .const import *

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = config_entry.data
    # On passe config_entry pour récupérer l'ID de l'appareil
    async_add_entities([
        UrbanSolarBatteryLevel(hass, config, config_entry),
        UrbanSolarCurrentPrice(hass, config, config_entry),
        UrbanSolarSavings(hass, config, config_entry)
    ], True)

class UrbanSolarBaseSensor(SensorEntity):
    """Classe de base pour partager les infos de l'appareil"""
    def __init__(self, hass, config, entry):
        self.hass = hass
        self._config = config
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Définit l'appareil auquel l'entité appartient"""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Gestionnaire Batterie Virtuelle",
            manufacturer="Urban Solar",
            model="Simulateur BV 1.2",
            configuration_url="https://github.com/votre_pseudo/Battery_ub_2",
        )

class UrbanSolarBatteryLevel(UrbanSolarBaseSensor):
    def __init__(self, hass, config, entry):
        super().__init__(hass, config, entry)
        self._attr_name = "Niveau Batterie Virtuelle"
        self._attr_unique_id = f"{entry.entry_id}_level"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        curr_inj = self.hass.states.get(self._config[CONF_INJECTION_ENTITY])
        curr_hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        curr_hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])
        if not (curr_inj and curr_hp and curr_hc): return None
        try:
            delta_inj = float(curr_inj.state) - self._config[CONF_START_INJECTION]
            delta_hp = float(curr_hp.state) - self._config[CONF_START_HCHP]
            delta_hc = float(curr_hc.state) - self._config[CONF_START_HCHC]
            balance = (delta_inj - (delta_hp + delta_hc)) / 1000
            return round(balance + self._config[CONF_START_BATTERY_KWH], 2)
        except: return None

class UrbanSolarCurrentPrice(UrbanSolarBaseSensor):
    def __init__(self, hass, config, entry):
        super().__init__(hass, config, entry)
        self._attr_name = "Prix kWh Actuel"
        self._attr_unique_id = f"{entry.entry_id}_price"
        self._attr_native_unit_of_measurement = "€/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self):
        # On cherche l'entité niveau de batterie de cet appareil
        level = self.hass.states.get(f"sensor.niveau_batterie_virtuelle")
        if not level or level.state in ["unknown", "unavailable"]: return self._config[CONF_PRICE_HP]
        return self._config[CONF_TAX_HP] if float(level.state) > 0 else self._config[CONF_PRICE_HP]

class UrbanSolarSavings(UrbanSolarBaseSensor):
    def __init__(self, hass, config, entry):
        super().__init__(hass, config, entry)
        self._attr_name = "Économies Totales"
        self._attr_unique_id = f"{entry.entry_id}_savings"
        self._attr_native_unit_of_measurement = "€"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        curr_hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        curr_hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])
        if not (curr_hp and curr_hc): return None
        delta_hp = (float(curr_hp.state) - self._config[CONF_START_HCHP]) / 1000
        delta_hc = (float(curr_hc.state) - self._config[CONF_START_HCHC]) / 1000
        savings = (delta_hp * (self._config[CONF_PRICE_HP] - self._config[CONF_TAX_HP])) + \
                  (delta_hc * (self._config[CONF_PRICE_HC] - self._config[CONF_TAX_HC]))
        return round(max(0, savings), 2)