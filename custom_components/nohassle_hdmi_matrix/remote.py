"""CEC remote platform for the HDMI Matrix.

Config-entry only (no legacy YAML). Creates one `remote` entity per port in both
directions — 8 outputs (displays/AVRs) + 8 inputs (sources) — all 16 regardless
of what's connected; per-port availability hides the dark/unconnected ones.
"""
import logging

from homeassistant.const import CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DATA_HDMIMATRIX
from .hdmi_matrix_remote import HDMIMatrixCecRemote
from .event_manager import get_host_bundle

_logger = logging.getLogger(__name__)

PORT_COUNT = 8


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the CEC remotes from a config entry."""
    host = entry.data[CONF_HOST]
    hass.data.setdefault(DATA_HDMIMATRIX, {})

    def _build():
        bundle = get_host_bundle(hass, host)
        controller = bundle["controller"]
        manager = bundle["manager"]
        if controller.get_status() is None:
            return None
        entities = []
        for is_output in (True, False):
            for port in range(PORT_COUNT):
                entity = HDMIMatrixCecRemote(host, controller, port, is_output)
                entity._manager = manager
                entities.append(entity)
        return entities

    entities = await hass.async_add_executor_job(_build)
    if entities is None:
        raise ConfigEntryNotReady(f"HDMI matrix at {host} is not reachable")

    for entity in entities:
        hass.data[DATA_HDMIMATRIX][entity.unique_id] = entity
    async_add_entities(entities, True)
