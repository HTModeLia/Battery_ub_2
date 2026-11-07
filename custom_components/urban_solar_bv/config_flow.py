import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from . import parse_local
from .const import *

ENTITY_SELECTOR = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="energy"))
NUMBER_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step=0.001, min=0)
)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_INJECTION_ENTITY): ENTITY_SELECTOR,
    vol.Required(CONF_HCHP_ENTITY): ENTITY_SELECTOR,
    vol.Required(CONF_HCHC_ENTITY): ENTITY_SELECTOR,
    vol.Required(CONF_RELEVE_KWH, default=0): NUMBER_SELECTOR,
    vol.Required(CONF_RELEVE_DATE): selector.DateTimeSelector(),
    vol.Required(CONF_PRICE_HP, default=0.22): NUMBER_SELECTOR,
    vol.Required(CONF_PRICE_HC, default=0.16): NUMBER_SELECTOR,
    vol.Required(CONF_TAX_HP, default=0.05): NUMBER_SELECTOR,
    vol.Required(CONF_TAX_HC, default=0.05): NUMBER_SELECTOR,
})


class UrbanSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            if parse_local(user_input[CONF_RELEVE_DATE]) > dt_util.utcnow():
                errors[CONF_RELEVE_DATE] = "date_future"
            else:
                # Une entrée par capteur d'injection : évite de doubler les entités
                await self.async_set_unique_id(user_input[CONF_INJECTION_ENTITY])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Urban Solar Virtual Battery", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(DATA_SCHEMA, user_input),
            errors=errors,
        )
