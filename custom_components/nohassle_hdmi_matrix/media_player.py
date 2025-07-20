"""Support for interfacing with HDMI Matrix."""
import json
import logging
import datetime
import time
from urllib import request, parse
import voluptuous as vol
from typing import Optional, Tuple

from homeassistant.components.media_player import (
    MediaPlayerEntity, MediaPlayerEntityFeature, PLATFORM_SCHEMA)

from homeassistant.components.media_player.const import (
    DOMAIN)

from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_HOST, CONF_NAME, CONF_TYPE, STATE_OFF,
    STATE_ON)

import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SUPPORT_HDMIMATRIX = MediaPlayerEntityFeature.SELECT_SOURCE

MEDIA_PLAYER_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.comp_entity_ids,
})

# ZONE_SCHEMA = vol.Schema({
#     vol.Required(CONF_NAME): cv.string,
# })

# SOURCE_SCHEMA = vol.Schema({
#     vol.Required(CONF_NAME): cv.string,
# })

CONF_ZONES = 'zones'
CONF_SOURCES = 'sources'

DATA_HDMIMATRIX = 'hdmi_matrix'

SERVICE_SETZONE = 'hdmi_matrix_set_zone'
ATTR_SOURCE = 'source'

SERVICE_SETZONE_SCHEMA = MEDIA_PLAYER_SCHEMA.extend({
    vol.Required(ATTR_SOURCE): cv.string
})

# Valid zone ids: 1-8
# ZONE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=8))

# Valid source ids: 1-8
# SOURCE_IDS = vol.All(vol.Coerce(int), vol.Range(min=1, max=8))

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
    if HDMIMatrixZone.get_status(host) is None:
        _LOGGER.error(f"Error: host {host} is not reachable")
        return

    ## Get Devices
    devices = HDMIMatrixZone.get_devices(host=host)

    entities = []
    for device_num in range(0,len(devices)):
        _LOGGER.info(f'Adding entity for device: #{device_num}')
        entity = HDMIMatrixZone(host, device_num)
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

    def __init__(self, hdmi_host, device_num):
        """Initialize new zone."""
        self._hdmi_host = hdmi_host
        self._device_number = device_num
        self._device_name = self.get_devices(host=hdmi_host)[device_num]
        self._unique_id = f'{hdmi_host}-output-{device_num}'
        self._sources = self.get_sources(host=hdmi_host)
        self._state = STATE_ON if self.are_devices_powered_on(hdmi_host) else STATE_OFF
        try:
            source_number = self.get_output_status(self._hdmi_host).get("allsource")[self._device_id]
            self._source = self.get_input_status(self._hdmi_host).get("inname")[source_number]
        except Exception as e:
            _LOGGER.exception(f"Exception occurred: {e}", exc_info=True)
            self._source = "UNKNOWN"

    def update(self):
        """Retrieve latest state."""
        try:
            self._state = STATE_ON if self.are_devices_powered_on(self._hdmi_host)  else STATE_OFF
        except Exception as e:
            _LOGGER.exception(f"Exception occurred: {e}", exc_info=True)
            self._state = STATE_OFF
        try:
            source_number = self.get_output_status(self._hdmi_host).get("allsource")[self._device_id]
            self._source = self.get_input_status(self._hdmi_host).get("inname")[source_number]
        except Exception as e:
            _LOGGER.exception(f"Exception: {e}", exc_info=True)
            self._source = "Unknown"

    @property
    def name(self):
        """Return the name of the zone."""
        return  self.get_devices(host=self._hdmi_host)[self._device_id]

    @property
    def state(self):
        """Return the state of the zone."""
        return self._state

    @property
    def supported_features(self):
        """Return flag of media commands that are supported."""
        return SUPPORT_HDMIMATRIX

    @property
    def media_title(self):
        """Return the current source as media title."""
        if self.state is STATE_OFF:
            return "Powered Off"
        return f"{self.source()} on {self.name()}"

    @property
    def source(self):
        """Return the current input source of the device."""
        return self._source

    @property
    def unique_id(self):
        """Return the current input source of the device."""
        return self._unique_id

    @property
    def source_list(self):
        """List of available input sources."""
        return self._sources

    def select_source(self, source):
        """Set input source."""
        sources = self.get_sources(self._hdmi_host)
        source_num = sources.index(source) if source in sources else None
        if not source_num:
            _LOGGER.error(f"Unknown Source: {source}")
            return

        _LOGGER.debug(f'Setting device {self._device_number} source to {source_num}')
        self.set_device_source(host=self._hdmi_host,
                               device_num=self._device_number,
                               source_num=source_num)
        self._source = source

    @staticmethod
    def send_instr(host: str, instr: dict, attempts: int = 3) -> Optional[dict]:
        """
        Sends an instruction to the specified host's API endpoint.

        Args:
            host (str): The host string (URL) of the device.
            instr (dict): The instruction to be sent as a dictionary.
            attempts (int): Number of retry attempts if the request fails.

        Returns:
            Optional[dict]: The parsed JSON response from the server if successful, or None if all attempts fail.
        """
        _LOGGER.debug(f"Sending instruction: {instr}")

        # Prepare the request data
        req_data = json.dumps(instr).encode('utf-8')
        req = request.Request(f"http://{host}/cgi-bin/instr")
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        req.add_header('Content-Length', str(len(req_data)))

        # Attempt to send the request
        for attempt in range(1, attempts + 1):
            try:
                # Execute the request
                with request.urlopen(req, req_data) as response:
                    if response.status == 200:
                        result = json.loads(response.read().decode())
                        _LOGGER.debug(f"Attempt {attempt}/{attempts}: Successful response: {result}")
                        return result

            except Exception as e:
                _LOGGER.warning(f"Attempt {attempt}/{attempts} failed: {e}")
                time.sleep(1)  # Wait before retrying

        # Log failure after exhausting all attempts
        _LOGGER.error(f"Failed to send instruction after {attempts} attempts to {host}.")
        return None

    @staticmethod
    def get_status(host: str) -> Optional[dict]:
        """
        Retrieves the status of the device by sending a command.

        Args:
            host (str): The host string (URL) of the device.

        Returns:
            Optional[dict]: The response from the device if successful, otherwise None.
        """
        _LOGGER.debug("Getting Device Status.")

        instr = {
            "comhead": "get status",
            "language": 0,
        }
        response = HDMIMatrixZone.send_instr(host, instr)

        if response:
            _LOGGER.debug(f"'get status' command sent successfully. Response: {response}")
            return response
        else:
            _LOGGER.error("Failed to send the 'get_status' command.")
            return None

    @staticmethod
    def get_video_status(host: str) -> Optional[dict]:
        """
        Retrieves the video status of the device by sending a command.

        Args:
            host (str): The host string (URL) of the device.

        Returns:
            Optional[dict]: The response from the device if successful, otherwise None.
        """
        _LOGGER.debug("Getting Device Video Status.")

        instr = {
            "comhead": "get videostatus",
            "language": 0,
        }
        response = HDMIMatrixZone.send_instr(host, instr)

        if response:
            _LOGGER.debug(f"'get videostatus' command sent successfully. Response: {response}")
            return response
        else:
            _LOGGER.error("Failed to send the 'get videostatus' command.")
            return None

    @staticmethod
    def get_input_status(host: str) -> Optional[dict]:
        """
        Retrieves the input status of the device by sending a command.

        Args:
            host (str): The host string (URL) of the device.

        Returns:
            Optional[dict]: The response from the device if successful, otherwise None.
        """
        _LOGGER.debug("Getting Device Input Status.")

        instr = {
            "comhead": "get input status",
            "language": 0,
        }
        response = HDMIMatrixZone.send_instr(host, instr)

        if response and response.get("comhead") == "get input status":
            _LOGGER.debug(f"'get input status' command sent successfully. Response: {response}")
            return response
        else:
            _LOGGER.error("Failed to send the 'get input status' command.")
            return None

    @staticmethod
    def get_output_status(host: str) -> Optional[dict]:
        """
        Retrieves the output status of the device by sending a command.

        Args:
            host (str): The host string (URL) of the device.

        Returns:
            Optional[dict]: The response from the device if successful, otherwise None.
        """
        _LOGGER.debug("Getting Device Output Status.")

        instr = {
            "comhead": "get output status",
            "language": 0,
        }
        response = HDMIMatrixZone.send_instr(host, instr)

        if response and response.get("comhead") == "get output status":
            _LOGGER.debug(f"'get output status' command sent successfully. Response: {response}")
            return response
        else:
            _LOGGER.error("Failed to send the 'get output status' command.")
            return None

    @staticmethod
    def get_devices(host: str) -> Optional[list]:
        """
        Retrieves the list of devices from the specified host.

        Args:
            host (str): The host address to query for devices.

        Returns:
            Optional[list]: A list of device names if found, otherwise None.
        """
        _LOGGER.debug("Retrieving devices from the host.")

        # Retrieve the devices from the output status
        output_status = HDMIMatrixZone.get_output_status(host)
        devices = output_status.get("name") if output_status else None

        if devices:
            _LOGGER.debug(f"Devices retrieved: {devices}")
            return HDMIMatrixZone.deduplicate_names(devices)
        _LOGGER.warning("No devices found or failed to retrieve devices.")
        return None

    @staticmethod
    def get_sources(host: str) -> Optional[list]:
        """
        Retrieves the list of sources from the specified host.

        Args:
            host (str): The host address to query for sources.

        Returns:
            Optional[list]: A list of source names if found, otherwise None.
        """
        _LOGGER.debug("Retrieving sources from the host.")

        # Retrieve the sources from the input status
        input_status = HDMIMatrixZone.get_input_status(host)
        sources = input_status.get("name") if input_status else None

        if sources:
            _LOGGER.debug(f"Sources retrieved: {sources}")
            return HDMIMatrixZone.deduplicate_names(sources)
        _LOGGER.warning("No sources found or failed to retrieve sources.")
        return None

    @staticmethod
    def power_on_devices(host: str) -> None:
        """
        Sends a command to power on the devices.

        Args:
            host (str): The host string (URL) of the device.

        Returns:
            None
        """
        _LOGGER.debug("Powering on devices...")

        instr = {
            "comhead": "set poweronoff",
            "language": 0,
            "power": 1
        }

        # Send the power-on instruction
        response = HDMIMatrixZone.send_instr(host, instr)

        if response:
            _LOGGER.debug(f"Power-on command sent successfully. Response: {response}")
        else:
            _LOGGER.error("Failed to send the power-on command.")

        # Allow time for devices to power on
        time.sleep(5)

    @staticmethod
    def power_off_devices(host: str) -> None:
        """
        Sends a command to power off the devices.

        Args:
            host (str): The host string (URL) of the device.

        Returns:
            None
        """
        _LOGGER.debug("Powering off devices...")

        instr = {
            "comhead": "set poweronoff",
            "language": 0,
            "power": 0
        }

        # Send the power-off instruction
        response = HDMIMatrixZone.send_instr(host, instr)

        if response:
            _LOGGER.debug(f"Power-off command sent successfully. Response: {response}")
        else:
            _LOGGER.error("Failed to send the power-off command.")

    @staticmethod
    def are_devices_powered_on(host: str) -> Optional[bool]:
        """
        Checks if the devices are powered on based on the host's status.

        Args:
            host (str): The host string (URL) of the device.

        Returns:
            Optional[bool]: True if devices are powered on, False if they are off,
                            or None if the status couldn't be retrieved or is invalid.
        """
        _LOGGER.debug("Checking if devices are powered on...")

        # Retrieve device status
        status = HDMIMatrixZone.get_status(host)

        if not status:
            _LOGGER.error("Failed to retrieve status")
            return None

        if "power" not in status:
            _LOGGER.error(f"Status does not contain 'power': {status}")
            return None

        if int(status.get("power")) == 1:
            _LOGGER.debug("Devices are powered on.")
            return True

        _LOGGER.debug("Devices are not powered on.")
        return False

    @staticmethod
    def deduplicate_names(names: list) -> list:
        """
        Deduplicates the names in the given list by appending a suffix
        (e.g., '_1', '_2') to duplicates and modifies the original list.

        Args:
            names (list): The list of names to deduplicate.

        Returns:
            list: The modified original list with deduplicated names.
        """
        seen = {}

        for i in range(len(names)):
            name = names[i]
            if name not in seen:
                seen[name] = 0
            else:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            names[i] = name  # Update the original list with the unique name
        return names

    @staticmethod
    def set_device_source(host: str, device_num: int, source_num: int) -> Optional[dict]:
        """
        Sets the source for a specific device on the given host.

        Args:
            host (str): The host address to send the command.
            device_num (int): The device number to set the source for.
            source_num (int): The source number to assign to the device.

        Returns:
            Optional[dict]: The response from the host if the command was successful, otherwise None.
        """
        # Log the operation being performed
        _LOGGER.debug(f"Setting source ({source_num}) for device ({device_num}) on host ({host}).")

        # Prepare the instruction payload for the 'video switch' command
        instr = {
            "comhead": "video switch",
            "language": 0,
            "source": [source_num, device_num]
        }

        # Send the instruction to the host
        response = HDMIMatrixZone.send_instr(host, instr)

        # Handle the response and provide logs
        if response:
            _LOGGER.debug(f"'video switch' command sent successfully. Response: {response}")
            return response

        # Log an error if the command failed
        _LOGGER.error("Failed to send the 'video switch' command.")
        return None
