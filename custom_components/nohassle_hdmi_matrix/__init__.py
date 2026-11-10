"""The No Hassle AV HDMI Matrix integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .event_manager import DATA_HOSTS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up No Hassle AV HDMI Matrix from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and stop its telnet event manager."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        host = entry.data[CONF_HOST]
        bundle = hass.data.get(DATA_HOSTS, {}).pop(host, None)
        if bundle is not None:
            await bundle["manager"].async_stop()
    return unloaded
