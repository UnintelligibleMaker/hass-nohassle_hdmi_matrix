"""Support for interfacing with an HDMI Matrix (switch platform)."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.components.select.const import DOMAIN as SELECT_DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, DATA_HDMIMATRIX, ATTR_SOURCE, SERVICE_SETZONE
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
    hass.data.setdefault(DATA_HDMIMATRIX, {})

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

    hass.data[DATA_HDMIMATRIX][entity.unique_id] = entity
    async_add_entities([entity], True)

    def service_handle(service):
        """Handle the legacy hdmi_matrix_set_zone service."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        source = service.data.get(ATTR_SOURCE)
        if entity_ids:
            entities = [e for e in hass.data[DATA_HDMIMATRIX].values()
                        if e.entity_id in entity_ids]
        else:
            entities = hass.data[DATA_HDMIMATRIX].values()
        for e in entities:
            if service.service == SERVICE_SETZONE:
                e.select_source(source)

    hass.services.async_register(SELECT_DOMAIN, SERVICE_SETZONE, service_handle)
