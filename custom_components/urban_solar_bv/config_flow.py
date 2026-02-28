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
        curr_inj = self.hass.states.get(self._config[CONF_INJECTION_ENTITY])
        curr_hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        curr_hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])

        if not (curr_inj and curr_hp and curr_hc): return None

        try:
            # On calcule le delta depuis le point de départ
            delta_inj = float(curr_inj.state) - self._config[CONF_START_INJECTION]
            delta_hp = float(curr_hp.state) - self._config[CONF_START_HCHP]
            delta_hc = float(curr_hc.state) - self._config[CONF_START_HCHC]
            
            # Formule finale en kWh
            balance = (delta_inj - (delta_hp + delta_hc)) / 1000
            return round(balance + self._config[CONF_START_BATTERY_KWH], 2)
        except: return None

class UrbanSolarCurrentPrice(SensorEntity):
    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = "Prix kWh Actuel (Dynamique)"
        self._attr_unique_id = f"{config[CONF_INJECTION_ENTITY]}_current_price"
        self._attr_native_unit_of_measurement = "€/kWh"
        self._attr_device_class = SensorDeviceClass.MONETARY

    @property
    def native_value(self):
        # On récupère le niveau via l'entité qu'on vient de créer
        level = self.hass.states.get(f"sensor.niveau_batterie_virtuelle")
        if not level or level.state in ["unknown", "unavailable"]: return self._config[CONF_PRICE_HP]
        
        # Si stock > 0 on applique la taxe, sinon prix plein
        return self._config[CONF_TAX_HP] if float(level.state) > 0 else self._config[CONF_PRICE_HP]

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
        curr_hp = self.hass.states.get(self._config[CONF_HCHP_ENTITY])
        curr_hc = self.hass.states.get(self._config[CONF_HCHC_ENTITY])
        if not (curr_hp and curr_hc): return None
        
        delta_hp = (float(curr_hp.state) - self._config[CONF_START_HCHP]) / 1000
        delta_hc = (float(curr_hc.state) - self._config[CONF_START_HCHC]) / 1000
        
        # Gain estimé par rapport au tarif réseau classique
        savings = (delta_hp * (self._config[CONF_PRICE_HP] - self._config[CONF_TAX_HP])) + \
                  (delta_hc * (self._config[CONF_PRICE_HC] - self._config[CONF_TAX_HC]))
        return round(max(0, savings), 2)