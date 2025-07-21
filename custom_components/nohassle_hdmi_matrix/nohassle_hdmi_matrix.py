import json
import logging
import time
from urllib import request
from typing import Optional, List

# Set up logging
_LOGGER = logging.getLogger(__name__)


class NoHassleHDMOMatrixController:
    """
    A class to manage device operations, like sending commands, retrieving statuses,
    managing sources/devices, and performing power operations.
    """

    def __init__(self, host: str):
        """
        Initialize the NoHassleHDMOMatrixController with the host address.

        Args:
            host (str): The host address (URL) of the device.
        """
        self.host = host

    # ----------------- Core Helper Methods -----------------

    def _send_instr(self, instr: dict, attempts: int = 3) -> Optional[dict]:
        """
        Sends an instruction to the specified host's API endpoint.

        Args:
            instr (dict): The instruction to be sent as a dictionary.
            attempts (int): Number of retry attempts if the request fails.

        Returns:
            Optional[dict]: JSON response from the host if successful; otherwise None.
        """
        _LOGGER.debug(f"Sending instruction: {instr}")

        req_data = json.dumps(instr).encode('utf-8')
        req = request.Request(f"http://{self.host}/cgi-bin/instr")
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        req.add_header('Content-Length', str(len(req_data)))

        for attempt in range(1, attempts + 1):
            try:
                with request.urlopen(req, req_data) as response:
                    if response.status == 200:
                        _LOGGER.debug(f"Attempt {attempt}/{attempts}: Successful response.")
                        result = json.loads(response.read().decode())
                        if result.get("comhead") == instr.get("comhead"):
                            return result
            except Exception as e:
                _LOGGER.warning(f"Attempt {attempt}/{attempts} failed: {e}")
                time.sleep(1)  # Retry delay

        _LOGGER.error(f"Failed to send instruction after {attempts} attempts to {self.host}.")
        return None

    def _send_command(self, command: str) -> Optional[dict]:
        """
        Helper method to send a command to the host.

        Args:
            command (str): The command to be sent to the device.

        Returns:
            Optional[dict]: Response from the device if successful; otherwise None.
        """
        _LOGGER.debug(f"Sending '{command}' command to {self.host}.")
        instr = {
            "comhead": command,
            "language": 0,
        }
        return self._log_response(instr, command)

    def _log_response(self, instr: dict, action: str, delay: int = 0) -> Optional[dict]:
        """
        Helper method to log responses from instructions.

        Args:
            instr (dict): The instruction to be sent.
            action (str): A description of the action.
            delay (int): Time to wait after the command (default: 0).

        Returns:
            Optional[dict]: The server's response if successful; otherwise None.
        """
        response = self._send_instr(instr)
        if response:
            _LOGGER.debug(f"{action} executed successfully. Response: {response}")
            if delay:
                time.sleep(delay)
            return response
        _LOGGER.error(f"Failed to execute {action}.")
        return None

    # ----------------- Device and Sources Management -----------------

    def get_devices(self) -> Optional[List[str]]:
        """
        Retrieves the list of devices from the host.

        Returns:
            Optional[List[str]]: List of device names if successful; otherwise None.
        """
        output_status = self.get_output_status()
        devices = output_status.get("name") if output_status else None
        return self._deduplicate_names(devices) if devices else None

    def get_device_count(self) -> int:
        """
            Retrieves the total count of devices connected to the host.

            Returns:
                int: The count of devices if found, otherwise 0.
            """
        # Get the list of devices
        devices = self.get_devices()

        # Return the count of devices or 0 as fallback
        return len(devices) if devices else 0

    def get_sources(self) -> Optional[List[str]]:
        """
        Retrieves the list of sources from the host.

        Returns:
            Optional[List[str]]: List of source names if successful; otherwise None.
        """
        input_status = self.get_input_status()
        sources = input_status.get("name") if input_status else None
        return self._deduplicate_names(sources) if sources else None

    def set_device_source(self, device_num: int, source_num: int) -> Optional[dict]:
        """
        Sets the source for a specific device.

        Args:
            device_num (int): The device number to set the source for.
            source_num (int): The source number to assign to the device.

        Returns:
            Optional[dict]: Response if the command was successful; otherwise None.
        """
        _LOGGER.debug(f"Setting source ({source_num}) for device ({device_num}).")
        instr = {
            "comhead": "video switch",
            "language": 0,
            "source": [source_num, device_num],
        }
        return self._log_response(instr, "'video switch' command")

    # ----------------- Device Status Commands -----------------

    def get_status(self) -> Optional[dict]:
        """Retrieves the general status of the device."""
        return self._send_command("get status")

    def get_video_status(self) -> Optional[dict]:
        """Retrieves the video status of the device."""
        return self._send_command("get videostatus")

    def get_input_status(self) -> Optional[dict]:
        """Retrieves the input status of the device."""
        return self._send_command("get input status")

    def get_output_status(self) -> Optional[dict]:
        """Retrieves the output status of the device."""
        return self._send_command("get output status")

    # ----------------- Power Control -----------------

    def power_on_devices(self) -> None:
        """Sends a command to power on the devices."""
        self._perform_power_command(1, 'power-on')

    def power_off_devices(self) -> None:
        """Sends a command to power off the devices."""
        self._perform_power_command(0, 'power-off')

    def are_devices_powered_on(self) -> Optional[bool]:
        """
        Checks if the devices are powered on.

        Returns:
            Optional[bool]: True if devices are powered on, False if not; None if status cannot be determined.
        """
        status = self.get_status()
        if not status or "power" not in status:
            return None
        return int(status["power"]) == 1

    def _perform_power_command(self, power_state: int, action: str) -> None:
        """
        Sends a power-on/off command to the devices.

        Args:
            power_state (int): The power state (1 for on, 0 for off).
            action (str): A description of the action being performed.
        """
        _LOGGER.debug(f"Performing '{action}' command.")
        instr = {
            "comhead": "set poweronoff",
            "language": 0,
            "power": power_state,
        }
        self._log_response(instr, f"'{action}' command", delay=5)

    # ----------------- Utility Methods -----------------

    @staticmethod
    def _deduplicate_names(names: Optional[List[str]]) -> List[str]:
        """
        Deduplicates a list of names with unique suffixes.

        Args:
            names (Optional[List[str]]): List of names to deduplicate.

        Returns:
            List[str]: Deduplicated list.
        """
        if not names:
            return []

        seen = {}
        for i in range(len(names)):
            name = names[i]
            if name not in seen:
                seen[name] = 0
            else:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            names[i] = name
        return names