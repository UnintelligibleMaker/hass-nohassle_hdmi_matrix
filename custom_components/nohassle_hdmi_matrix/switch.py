"""Support for interfacing with an HDMI Matrix (switch platform)."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .hdmi_matrix_switch import HDMIMatrixSwitch
from .event_manager import get_host_bundle

_logger = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Migrate legacy YAML (`switch: - platform: nohassle_hdmi_matrix`) into a config entry.

    Adds no entities itself — it just hands the host to the import flow; the
    config entry creates the entities (with the same unique_ids, so history is kept).
    """
    host = config.get(CONF_HOST)
    if host:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data={CONF_HOST: host}
            )
        )


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the matrix power switch from a config entry."""
    host = entry.data[CONF_HOST]

    def _build():
        bundle = get_host_bundle(hass, host)
        controller = bundle["controller"]
        manager = bundle["manager"]
        if controller.get_status() is None:
            return None
        entity = HDMIMatrixSwitch(host, controller)
        entity._manager = manager
        return entity

    entity = await hass.async_add_executor_job(_build)
    if entity is None:
        raise ConfigEntryNotReady(f"HDMI matrix at {host} is not reachable")

    async_add_entities([entity], True)
