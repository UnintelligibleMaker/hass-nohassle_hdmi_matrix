"""Support for interfacing with HDMI Matrix."""

import logging
from homeassistant.components.switch import SwitchEntity

_logger = logging.getLogger(__name__)

class HDMIMatrixSwitch(SwitchEntity):
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
            _logger.debug(f"Exception occurred: {e}", exc_info=True)
            self.current_option = None

    def update(self):
        """Retrieve latest state."""
        try:
            self._is_on = self._controller.are_devices_powered_on()
        except Exception as e:
            _logger.debug(f"Exception: {e}", exc_info=True)
            self._is_on = None

        try:
            source_number = self._controller.get_output_status().get("allsource")[self._device_number]
            self.current_option = self._controller.get_input_status().get("inname")[source_number]
        except Exception as e:
            _logger.debug(f"Exception: {e}", exc_info=True)
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
