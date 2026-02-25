import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import *

class UrbanSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Batterie Virtuelle Urban Solar", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_INJECTION_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="energy")),
                vol.Required(CONF_HCHP_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="energy")),
                vol.Required(CONF_HCHC_ENTITY): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="energy")),
                vol.Required(CONF_INITIAL_BATTERY_LEVEL, default=0): vol.Coerce(float),
                vol.Required(CONF_PRICE_HP, default=0.22): vol.Coerce(float),
                vol.Required(CONF_PRICE_HC, default=0.16): vol.Coerce(float),
                vol.Required(CONF_TAX_HP, default=0.05): vol.Coerce(float),
                vol.Required(CONF_TAX_HC, default=0.05): vol.Coerce(float),
            })
        )