"""Support for interfacing with HDMI Matrix."""
import json
import logging
import datetime
import time
from urllib import request, parse
import voluptuous as vol
from typing import Optional, Tuple

from homeassistant.components.media_player import (
    MediaPlayerEntity, MediaPlayerState, MediaPlayerEntityFeature, PLATFORM_SCHEMA, MediaPlayerState)

from homeassistant.components.media_player.const import (
    DOMAIN)

from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_HOST, CONF_NAME, CONF_TYPE)

import homeassistant.helpers.config_validation as cv
from nohassle_hdmi_matrix import NoHassleHDMOMatrixController

_LOGGER = logging.getLogger(__name__)

SUPPORT_HDMIMATRIX = (MediaPlayerEntityFeature.SELECT_SOURCE
                      | MediaPlayerEntityFeature.TURN_ON
                      | MediaPlayerEntityFeature.TURN_OFF)

MEDIA_PLAYER_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.comp_entity_ids,
})


DATA_HDMIMATRIX = 'hdmi_matrix'

SERVICE_SETZONE = 'hdmi_matrix_set_zone'
ATTR_SOURCE = 'source'

SERVICE_SETZONE_SCHEMA = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_SOURCE): cv.string
})

PLATFORM_SCHEMA = vol.All(
    cv.has_at_least_one_key(CONF_HOST),
    PLATFORM_SCHEMA.extend({
        vol.Exclusive(CONF_HOST, CONF_TYPE): cv.string,
    }))


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

    ## Get Devices
    devices = controller.get_devices()

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

    hass.services.register(DOMAIN, SERVICE_SETZONE, service_handle,
                           schema=SERVICE_SETZONE_SCHEMA)




class HDMIMatrixZone(MediaPlayerEntity):
    """Representation of a HDMI matrix zone."""

    def __init__(self, hdmi_host, device_num, controller):
        """Initialize new zone."""
        self._hdmi_host = hdmi_host
        self._device_number = device_num
        self._device_name = self.get_devices(host=hdmi_host)[device_num]
        self._unique_id = f'{hdmi_host}-output-{device_num}'
        self._sources = self.get_sources(host=hdmi_host)
        self._controller = controller
        self._state = MediaPlayerState.ON if self.are_devices_powered_on(hdmi_host) else MediaPlayerState.OFF

        try:
            output_status = self._controller.get_output_status()
            if not output_status:
                self._source = None
                return
            source_number = output_status.get("allsource")[self._device_number]

            input_status = self._controller.get_input_status()
            if not input_status:
                self._source = None
                return
            self._source = input_status.get("inname")[source_number]
        except Exception as e:
            _LOGGER.debug(f"Exception occurred: {e}", exc_info=True)
            self._source = None

    def update(self):
        """Retrieve latest state."""
        try:
            self._state = MediaPlayerState.ON if self._controller.are_devices_powered_on()  else MediaPlayerState.OFF
        except Exception as e:
            _LOGGER.debug(f"Exception occurred: {e}", exc_info=True)
            self._state = MediaPlayerState.OFF
        try:
            source_number = self._controller.get_output_status().get("allsource")[self._device_number]
            self._source = self._controller.get_input_status().get("inname")[source_number]
        except Exception as e:
            _LOGGER.debug(f"Exception: {e}", exc_info=True)
            self._source = None

    @property
    def name(self):
        """Return the name of the zone."""
        return  self._device_name

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the zone."""
        return self._state

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_HDMIMATRIX

    @property
    def media_title(self):
        """Return the current source as media title."""
        if self.state is MediaPlayerState.OFF:
            return "Powered Off"
        return f"{self.source} on {self.name}"

    @property
    def source(self)-> str | None:
        """Return the current input source of the device."""
        return self._source

    @property
    def unique_id(self):
        """Return the current input source of the device."""
        return self._unique_id

    @property
    def source_list(self)-> list[str]:
        """List of available input sources."""
        return self._sources

    def select_source(self, source: str) -> None:
        """Set input source."""
        sources = self._controller.get_sources()
        source_num = sources.index(source) if source in sources else None
        if not source_num:
            _LOGGER.error(f"Unknown Source: {source}")
            return

        _LOGGER.debug(f'Setting device {self._device_number} source to {source_num}')
        self._controller.set_device_source(device_num=self._device_number, source_num=source_num)
        self._source = source
