"""Support for interfacing with an HDMI Matrix (select platform)."""
import logging

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .hdm_matrix_select import HDMIMatrixSelect
from .event_manager import get_host_bundle

_logger = logging.getLogger(__name__)


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Migrate legacy YAML (`select: - platform: nohassle_hdmi_matrix`) into a config entry.

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
    """Set up the matrix output selects from a config entry."""
    host = entry.data[CONF_HOST]

    def _build():
        bundle = get_host_bundle(hass, host)
        controller = bundle["controller"]
        manager = bundle["manager"]
        if controller.get_status() is None:
            return None
        entities = []
        for device_num in range(0, controller.get_device_count()):
            entity = HDMIMatrixSelect(host, device_num, controller)
            entity._manager = manager
            entities.append(entity)
        return entities

    entities = await hass.async_add_executor_job(_build)
    if entities is None:
        raise ConfigEntryNotReady(f"HDMI matrix at {host} is not reachable")

    async_add_entities(entities, True)
