"""Support for interfacing with HDMI Matrix."""
import logging
from homeassistant.components.switch import SwitchEntity

from .nohassle_hdmi_matrix import NoHassleHDMOMatrixController
from .const import DATA_HDMIMATRIX, ATTR_SOURCE, SERVICE_SETZONE

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

    _LOGGER.info(f'Adding entity for Power of HDMI Matrix')
    entity = HDMIMatrixPower(host, controller)
    _LOGGER.info(f'entityId: #{entity.unique_id}')
    hass.data[DATA_HDMIMATRIX][entity.unique_id] = entity
    add_entities([entity], True)

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


class HDMIMatrixPower(SwitchEntity):
    """Representation of an HDMI matrix device (output)."""

    def __init__(self, hdmi_host, controller):
        self._controller = controller
        self._unique_id = f'{hdmi_host}-power-switch'
        self._device_name = f'{hdmi_host} Power Switch'
        self._is_on = self._controller.are_devices_powered_on()

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
            _LOGGER.debug(f"Exception occurred: {e}", exc_info=True)
            self.current_option = None

    def update(self):
        """Retrieve latest state."""
        try:
            self._is_on = self._controller.are_devices_powered_on()
        except Exception as e:
            _LOGGER.debug(f"Exception: {e}", exc_info=True)
            self._is_on = None

        try:
            source_number = self._controller.get_output_status().get("allsource")[self._device_number]
            self.current_option = self._controller.get_input_status().get("inname")[source_number]
        except Exception as e:
            _LOGGER.debug(f"Exception: {e}", exc_info=True)
            self.current_option = None

    @property
    def name(self):
        """Return the name of the zone."""
        return self._device_name

    @property
    def unique_id(self):
        """Return the current input source of the device."""
        return self._unique_id

    @property
    def is_on(self):
        """Return the current input source of the device."""
        return self._is_on

    def turn_on(self):
        self._controller.power_on_devices()

    def turn_off(self):
        self._controller.power_off_devices()