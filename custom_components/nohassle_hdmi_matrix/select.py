"""Support for interfacing with HDMI Matrix."""

import logging

from .nohassle_hdmi_matrix import NoHassleHDMOMatrixController
from .const import  DATA_HDMIMATRIX, ATTR_SOURCE, SERVICE_SETZONE
from .hdm_matrix_select import HDMIMatrixSelect

_logger = logging.getLogger(__name__)
from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_HOST, CONF_NAME, CONF_TYPE)

from homeassistant.components.select.const import (
    DOMAIN)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the HDMI Matrix platform."""
    if DATA_HDMIMATRIX not in hass.data:
        hass.data[DATA_HDMIMATRIX] = {}

    ## Get host
    host = config.get(CONF_HOST)
    if host is None:
        _logger.error(f"Error: host name is not defined in the config")
        return

    controller = NoHassleHDMOMatrixController(host=host)
    if controller.get_status() is None:
        _logger.error(f"Error: host {host} is not reachable")
        return

    entities = []
    for device_num in range(0, controller.get_device_count()):
        _logger.info(f'Adding entity for device: #{device_num}')
        entity = HDMIMatrixSelect(host, device_num, controller)
        _logger.info(f'entityId: #{entity.unique_id}')
        hass.data[DATA_HDMIMATRIX][entity.unique_id] = entity
        entities.append(entity)
    add_entities(entities, True)

    def service_handle(service):
        """Handle for services."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        source = service.data.get(ATTR_SOURCE)
        if entity_ids:
            entities = [entity for entity in hass.data[DATA_HDMIMATRIX].values()
                       if entity.entity_id in entity_ids]
        else:
            entities = hass.data[DATA_HDMIMATRIX].values()

        for entity in entities:
            if service.service == SERVICE_SETZONE:
                entity.select_source(source)

    hass.services.register(DOMAIN, SERVICE_SETZONE, service_handle)


