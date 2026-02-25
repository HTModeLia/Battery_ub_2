from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from .const import *

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = config_entry.data
    async_add_entities([
        UrbanSolarBatteryLevel(hass, config),
        UrbanSolarCurrentPrice(hass, config),
        UrbanSolarSavings(hass, config)
    ], True)

class UrbanSolarBatteryLevel(SensorEntity):
    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = "Niveau Batterie Virtuelle"
        self._attr_unique_id = f"{config[CONF_INJECTION_ENTITY]}_level"
        self._attr_native_unit_of_measurement = "kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        inj = self.hass.states.get(self._config[CONF_INJECTION_ENTITY])
        hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])
        if not (inj and hp and hc): return None
        try:
            # Conversion Wh vers kWh si nécessaire (ZLinky est souvent en Wh)
            balance = (float(inj.state) - (float(hp.state) + float(hc.state))) / 1000
            return round(balance + self._config[CONF_INITIAL_BATTERY_LEVEL], 2)
        except: return None

class UrbanSolarCurrentPrice(SensorEntity):
    """Capteur de prix dynamique pour le Dashboard Énergie"""
    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = "Prix kWh Actuel (Dynamique)"
        self._attr_unique_id = f"{config[CONF_INJECTION_ENTITY]}_current_price"
        self._attr_native_unit_of_measurement = "€/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self):
        level = self.hass.states.get(f"sensor.niveau_batterie_virtuelle")
        if not level or level.state == "unknown": return self._config[CONF_PRICE_HP]
        
        # LOGIQUE : Si batterie > 0, on paye la taxe, sinon prix plein
        if float(level.state) > 0:
            return self._config[CONF_TAX_HP]
        return self._config[CONF_PRICE_HP]

class UrbanSolarSavings(SensorEntity):
    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = "Économies Totales Urban Solar"
        self._attr_unique_id = f"{config[CONF_INJECTION_ENTITY]}_savings"
        self._attr_native_unit_of_measurement = "€"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])
        if not (hp and hc): return None
        # Gain = (Prix plein - Taxes) * kWh consommés sur batterie
        # Pour simplifier, on calcule l'économie par rapport au prix réseau
        savings = (float(hp.state)/1000 * (self._config[CONF_PRICE_HP] - self._config[CONF_TAX_HP])) + \
                  (float(hc.state)/1000 * (self._config[CONF_PRICE_HC] - self._config[CONF_TAX_HC]))
        return round(savings, 2)