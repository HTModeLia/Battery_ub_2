import logging
from datetime import timedelta
from functools import partial

from homeassistant.components.recorder import get_instance, history
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import engine
from .const import *

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


async def async_setup_entry(hass, entry):
    battery = VirtualBattery(hass, entry)
    await battery.async_start()
    entry.runtime_data = battery
    # Les tarifs modifiés via « Configurer » s'appliquent au rechargement
    entry.async_on_unload(entry.add_update_listener(lambda h, e: h.config_entries.async_reload(e.entry_id)))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.async_stop()
    return ok


async def async_remove_entry(hass, entry):
    await _store(hass, entry).async_remove()


def _store(hass, entry):
    return Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")


def parse_local(value):
    """Date saisie (texte ou datetime ; sans fuseau = heure locale de HA) -> UTC."""
    when = dt_util.parse_datetime(value) if isinstance(value, str) else value
    if when is None:
        raise HomeAssistantError(f"Date invalide : {value}")
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_utc(when)


class VirtualBattery:
    """Suit les compteurs Linky et tient la batterie virtuelle à jour (état persistant)."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entities = {
            "inj": entry.data[CONF_INJECTION_ENTITY],
            "hp": entry.data[CONF_HCHP_ENTITY],
            "hc": entry.data[CONF_HCHC_ENTITY],
        }
        self._keys = {eid: key for key, eid in self.entities.items()}
        self._entry = entry
        self._store = _store(hass, entry)
        self._listeners = []
        self._unsub = None
        self.data = None

    async def async_start(self):
        saved = await self._store.async_load()
        conf = {**self._entry.data, **self._entry.options}
        tarifs = {
            "hp": (conf[CONF_PRICE_HP], conf[CONF_TAX_HP]),
            "hc": (conf[CONF_PRICE_HC], conf[CONF_TAX_HC]),
        }
        if saved:
            self.data = saved
            # Données de la 2.0.0 : coût et économies n'étaient pas cumulés
            if "cout" not in saved:
                saved["cout"] = sum(saved[f"decharge_{k}"] * tax for k, (_, tax) in tarifs.items())
                saved["economies"] = sum(saved[f"decharge_{k}"] * (p - tax) for k, (p, tax) in tarifs.items())
            saved["tarifs"] = tarifs
            # Rattrape ce qui s'est passé pendant l'arrêt de HA
            await self._replay(saved["stock"], dt_util.parse_datetime(saved["updated"]), saved["last"], count=True)
        else:
            releve = self._entry.data[CONF_RELEVE_KWH]
            self.data = engine.new_data(releve)
            self.data["tarifs"] = tarifs
            try:
                await self.async_calibrate(releve, parse_local(self._entry.data[CONF_RELEVE_DATE]))
            except HomeAssistantError as err:
                _LOGGER.warning("%s. Le stock part du relevé à l'instant présent.", err)
                engine.replay(self.data, releve, {}, self._current_events(), count=False)
        self._unsub = async_track_state_change_event(self.hass, list(self.entities.values()), self._on_change)
        self._save()

    async def async_stop(self):
        if self._unsub:
            self._unsub()
        await self._store.async_save(self.data)

    async def async_calibrate(self, kwh, when):
        """Stock = niveau relevé chez Urban Solar à `when`, puis rejoue l'historique jusqu'à maintenant."""
        if when > dt_util.utcnow():
            raise HomeAssistantError("La date du relevé est dans le futur")
        await self._replay(kwh, when, None, count=False)
        self._save()
        self._notify()

    async def _replay(self, stock, since, base, count):
        hist = await get_instance(self.hass).async_add_executor_job(
            partial(
                history.get_significant_states,
                self.hass,
                since,
                None,
                list(self.entities.values()),
                include_start_time_state=True,
                significant_changes_only=False,
            )
        )
        calibrating = base is None
        base = dict(base or {})
        events = []
        for key, eid in self.entities.items():
            for state in hist.get(eid, []):
                value = self._kwh(state)
                if value is None:
                    continue
                # Au redémarrage, un index jamais lu prend sa 1re valeur comme référence (voir engine.apply)
                if key in base or not calibrating:
                    events.append((state.last_updated, key, value))
                elif state.last_updated <= since + timedelta(seconds=1):  # état au début de la période
                    base[key] = value
        missing = [eid for key, eid in self.entities.items() if key not in base]
        if calibrating and missing:
            raise HomeAssistantError(
                f"Pas d'historique de {', '.join(missing)} au {dt_util.as_local(since):%d/%m/%Y %H:%M} "
                "(date antérieure à la conservation du recorder ?)"
            )
        engine.replay(self.data, stock, base, events + self._current_events(), count)

    def _current_events(self):
        now = dt_util.utcnow()
        events = []
        for key, eid in self.entities.items():
            state = self.hass.states.get(eid)
            value = self._kwh(state)
            if value is not None:
                events.append((now, key, value))
        return events

    @staticmethod
    def _kwh(state):
        try:
            value = float(state.state)
        except (AttributeError, TypeError, ValueError):  # absent, unknown, unavailable
            return None
        # shortcut: seules les unités Wh et kWh sont gérées
        return value / 1000 if state.attributes.get("unit_of_measurement") == "Wh" else value

    @callback
    def _on_change(self, event):
        value = self._kwh(event.data["new_state"])
        if value is None:
            return
        engine.apply(self.data, self._keys[event.data["entity_id"]], value)
        self._save()
        self._notify()

    def _save(self):
        self.data["updated"] = dt_util.utcnow().isoformat()
        self._store.async_delay_save(lambda: self.data, 10)

    @callback
    def add_listener(self, cb):
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb)

    def _notify(self):
        for cb in self._listeners:
            cb()
