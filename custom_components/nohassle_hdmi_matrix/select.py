"""Support for interfacing with an HDMI Matrix (select platform)."""
import logging

from homeassistant.components.select.const import DOMAIN as SELECT_DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, DATA_HDMIMATRIX, ATTR_SOURCE, SERVICE_SETZONE
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
    hass.data.setdefault(DATA_HDMIMATRIX, {})

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

    for entity in entities:
        hass.data[DATA_HDMIMATRIX][entity.unique_id] = entity
    async_add_entities(entities, True)

    def service_handle(service):
        """Handle the legacy hdmi_matrix_set_zone service."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        source = service.data.get(ATTR_SOURCE)
        if entity_ids:
            targets = [e for e in hass.data[DATA_HDMIMATRIX].values()
                       if e.entity_id in entity_ids]
        else:
            targets = hass.data[DATA_HDMIMATRIX].values()
        for e in targets:
            if service.service == SERVICE_SETZONE:
                e.select_source(source)

    hass.services.async_register(SELECT_DOMAIN, SERVICE_SETZONE, service_handle)
