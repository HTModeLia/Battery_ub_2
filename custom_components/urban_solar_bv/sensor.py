from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from .const import *

async def async_setup_entry(hass, config_entry, async_add_entities):
    config = config_entry.data
    async_add_entities([
        UrbanSolarBatteryLevel(hass, config),
        UrbanSolarTaxCost(hass, config),
        UrbanSolarSavings(hass, config)
    ], True)

class UrbanSolarBatteryLevel(SensorEntity):
    """Capteur du niveau de stock en kWh"""
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
        
        balance = (float(inj.state) - (float(hp.state) + float(hc.state))) / 1000
        return round(balance + self._config[CONF_INITIAL_BATTERY_LEVEL], 2)

class UrbanSolarTaxCost(SensorEntity):
    """Calcule le coût des taxes (TURPE) payées sur le déstockage"""
    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = "Coût Taxes Déstockage"
        self._attr_native_unit_of_measurement = "€"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])
        if not (hp and hc): return None
        
        total_tax = (float(hp.state) / 1000 * self._config[CONF_TAX_HP]) + \
                    (float(hc.state) / 1000 * self._config[CONF_TAX_HC])
        return round(total_tax, 2)

class UrbanSolarSavings(SensorEntity):
    """Calcule l'économie réelle (Prix grille - Taxes payées)"""
    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = "Économies Réalisées"
        self._attr_native_unit_of_measurement = "€"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])
        if not (hp and hc): return None
        
        # Ce qu'on aurait payé sans batterie - Ce qu'on paye en taxes
        brut_cost = (float(hp.state) / 1000 * self._config[CONF_PRICE_HP]) + \
                    (float(hc.state) / 1000 * self._config[CONF_PRICE_HC])
        taxes = (float(hp.state) / 1000 * self._config[CONF_TAX_HP]) + \
                (float(hc.state) / 1000 * self._config[CONF_TAX_HC])
        
        return round(brut_cost - taxes, 2)