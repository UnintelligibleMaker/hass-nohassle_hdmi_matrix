import json
import logging
import time
from urllib import request
from typing import Optional, List

# Set up logging
_LOGGER = logging.getLogger(__name__)


class NoHassleHDMOMatrixController:
    """
    A class to manage device operations such as sending commands, retrieving statuses,
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
        _LOGGER.debug(f"Preparing to send instruction: {instr}")

        req_data = json.dumps(instr).encode("utf-8")
        req = request.Request(f"http://{self.host}/cgi-bin/instr")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Content-Length", str(len(req_data)))

        for attempt in range(1, attempts + 1):
            try:
                with request.urlopen(req, req_data) as response:
                    if response.status == 200:
                        result = json.loads(response.read().decode())
                        if result.get("comhead") == instr.get("comhead"):
                            _LOGGER.debug(f"Instruction succeeded on attempt {attempt}.")
                            return result
            except Exception as e:
                _LOGGER.warning(f"Attempt {attempt}/{attempts} failed: {e}")
                time.sleep(1)  # Retry delay

        _LOGGER.error(f"Failed to send instruction after {attempts} attempts to {self.host}.")
        return None

    def _send_command(self, command: str) -> Optional[dict]:
        """
        Sends a predefined command to the host.

        Args:
            command (str): The command to be sent.

        Returns:
            Optional[dict]: Response from the host if successful; otherwise None.
        """
        _LOGGER.debug(f"Sending command: '{command}'")
        instr = {
            "comhead": command,
            "language": 0,
        }
        return self._log_response(instr, command)

    def _log_response(self, instr: dict, action: str, delay: int = 0) -> Optional[dict]:
        """
        Sends an instruction and logs the result.

        Args:
            instr (dict): The instruction to be sent.
            action (str): The corresponding action for the instruction.
            delay (int): Optional delay after sending the instruction.

        Returns:
            Optional[dict]: The host response if successful; otherwise None.
        """
        response = self._send_instr(instr)
        if response:
            _LOGGER.info(f"{action} executed successfully. Response: {response}")
            if delay:
                time.sleep(delay)
            return response
        _LOGGER.error(f"Failed to execute action '{action}'.")
        return None

    # ----------------- Device and Sources Management -----------------

    def get_devices(self, attempts: int = 3) -> Optional[List[str]]:
        """
        Retrieves the list of devices from the host.

        Args:
            attempts (int): Number of retry attempts.

        Returns:
            Optional[List[str]]: List of device names if successful; otherwise None.
        """
        for attempt in range(1, attempts + 1):
            try:
                output_status = self.get_output_status()
                if not output_status or "name" not in output_status:
                    _LOGGER.warning(
                        f"Attempt {attempt}/{attempts}: Output status is invalid: {output_status}"
                    )
                    continue

                devices = output_status.get("name")
                if devices:
                    return self._deduplicate_names(devices)

                _LOGGER.warning(f"Attempt {attempt}/{attempts}: 'name' field is empty.")
            except Exception as e:
                _LOGGER.error(f"Attempt {attempt}/{attempts} failed with error: {e}")
            time.sleep(1)

        _LOGGER.error("Failed to retrieve devices after all attempts.")
        return None

    def get_device_count(self) -> int:
        """
        Returns the total count of connected devices.

        Returns:
            int: Device count if successful; 0 otherwise.
        """
        devices = self.get_devices()
        return len(devices) if devices else 0

    def get_sources(self, attempts: int = 3) -> Optional[List[str]]:
        """
        Retrieves the list of sources from the host.

        Args:
            attempts (int): Number of retry attempts.

        Returns:
            Optional[List[str]]: List of source names if successful; otherwise None.
        """
        for attempt in range(1, attempts + 1):
            try:
                input_status = self.get_input_status()
                if not input_status or "inname" not in input_status:
                    _LOGGER.warning(
                        f"Attempt {attempt}/{attempts}: Input status is invalid: {input_status}"
                    )
                    continue

                sources = input_status.get("inname")
                if sources:
                    return self._deduplicate_names(sources)

                _LOGGER.warning(f"Attempt {attempt}/{attempts}: 'inname' field is empty.")
            except Exception as e:
                _LOGGER.error(f"Attempt {attempt}/{attempts} failed with error: {e}")
            time.sleep(1)

        _LOGGER.error("Failed to retrieve sources after all attempts.")
        return None

    def set_device_source(self, device_num: int, source_num: int) -> Optional[dict]:
        """
        Sets the source for a specific device.

        Args:
            device_num (int): Target device.
            source_num (int): Source to assign.

        Returns:
            Optional[dict]: Response if successful; otherwise None.
        """
        _LOGGER.debug(f"Setting source '{source_num}' for device '{device_num}'.")
        instr = {
            "comhead": "video switch",
            "language": 0,
            "source": [source_num, device_num],
        }
        return self._log_response(instr, "video switch command")

    # ----------------- Power Control -----------------

    def power_on_devices(self) -> None:
        """Powers on all devices."""
        self._perform_power_command(1, "power-on")

    def power_off_devices(self) -> None:
        """Powers off all devices."""
        self._perform_power_command(0, "power-off")

    def are_devices_powered_on(self) -> Optional[bool]:
        """
        Checks device power status.

        Returns:
            Optional[bool]: True if devices are on, False otherwise; or None if unknown.
        """
        status = self.get_status()
        if not status or "power" not in status:
            return None
        return status["power"] == 1

    def _perform_power_command(self, power_state: int, action: str) -> None:
        """
        Sends a power state command to devices.

        Args:
            power_state (int): 1 for on, 0 for off.
            action (str): The action description.
        """
        instr = {
            "comhead": "set poweronoff",
            "language": 0,
            "power": power_state,
        }
        self._log_response(instr, action, delay=2)

    # ----------------- Utility Methods -----------------

    @staticmethod
    def _deduplicate_names(names: Optional[List[str]]) -> List[str]:
        """
        Deduplicates a list of names, appending a unique suffix for duplicates.

        Args:
            names (Optional[List[str]]): List of names to deduplicate.

        Returns:
            List[str]: Deduplicated list.
        """
        if not names:
            return []

        seen = {}
        for i, name in enumerate(names):
            if name not in seen:
                seen[name] = 0
            else:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            names[i] = name
        return names