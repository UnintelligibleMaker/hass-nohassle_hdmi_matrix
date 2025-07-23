"""Support for interfacing with HDMI Matrix."""
import json
import logging
import datetime
import time
from urllib import request, parse
import voluptuous as vol
from typing import Optional, Tuple

from homeassistant.components.select import SelectEntity

from .nohassle_hdmi_matrix import NoHassleHDMOMatrixController
from .const import  DATA_HDMIMATRIX, ATTR_SOURCE, SERVICE_SETZONE

_LOGGER = logging.getLogger(__name__)
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
        _LOGGER.error(f"Error: host name is not defined in the config")
        return

    controller = NoHassleHDMOMatrixController(host=host)
    if controller.get_status() is None:
        _LOGGER.error(f"Error: host {host} is not reachable")
        return

    entities = []
    for device_num in range(0, controller.get_device_count()):
        _LOGGER.info(f'Adding entity for device: #{device_num}')
        entity = HDMIMatrixZone(host, device_num, controller)
        _LOGGER.info(f'entityId: #{entity.unique_id}')
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




class HDMIMatrixZone(SelectEntity):
    """Representation of an HDMI matrix device (output)."""

    def __init__(self, hdmi_host, device_num, controller):
        """Initialize new zone."""
        self._device_number = device_num
        self._controller = controller
        self._unique_id = f'{hdmi_host}-output-{device_num}'
        self._options = self._controller.get_sources()
        self._device_name = self._controller.get_devices()[device_num]


        try:
            output_status = self._controller.get_output_status()
            if not output_status:
                self.current_option = None
                return
            source_number = output_status.get("allsource")[self._device_number]

            input_status = self._controller.get_input_status()
            if not input_status:
                self.current_option = None
                return
            self.current_option = input_status.get("inname")[source_number]
        except Exception as e:
            _LOGGER.info(f"Exception occurred: {e}", exc_info=True)
            self.current_option = None

    def update(self):
        """Retrieve latest state."""
        try:
            self._options = self._controller.get_sources()
        except Exception as e:
            _LOGGER.info(f"Exception: {e}", exc_info=True)
            self._options = None

        try:
            self._device_name = self._controller.get_devices()[device_num]
        except Exception as e:
            _LOGGER.info(f"Exception: {e}", exc_info=True)
            self._device_name = None


        try:
            source_number = self._controller.get_output_status().get("allsource")[self._device_number]
            self.current_option = self._controller.get_input_status().get("inname")[source_number]
        except Exception as e:
            _LOGGER.info(f"Exception: {e}", exc_info=True)
            self.current_option = None

    @property
    def name(self):
        """Return the name of the zone."""
        return  self._device_name

    @property
    def options(self):
        """Return the name of the zone."""
        return  self._options

    @property
    def unique_id(self):
        """Return the current input source of the device."""
        return self._unique_id

    def select_option(self, option: str) -> None:
        """Set input option."""
        options = self._controller.get_sources()
        option_num = options.index(option) if option in option else None
        if not option_num:
            _LOGGER.error(f"Unknown Option: {option}")
            return

        _LOGGER.info(f'Setting device {self._device_number} source to {option_num}')
        self._controller.set_device_source(device_num=self._device_number, source_num=option_num)
        self.current_option = option
