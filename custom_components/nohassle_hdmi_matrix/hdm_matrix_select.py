"""Support for interfacing with HDMI Matrix."""

import logging
import voluptuous as vol

from homeassistant.components.select import SelectEntity

_logger = logging.getLogger(__name__)

class HDMIMatrixSelect(SelectEntity):
    """Representation of an HDMI matrix device (output)."""

    def __init__(self, hdmi_host, device_num, controller):
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
            source_number = output_status.get("allsource")[self._device_number] - 1

            input_status = self._controller.get_input_status()
            if not input_status:
                self.current_option = None
                return
            self.current_option = input_status.get("inname")[source_number]
        except Exception as e:
            _logger.error(f"Exception occurred: {e}", exc_info=True)
            self.current_option = None

    def update(self):
        """Retrieve latest state."""
        try:
            self._options = self._controller.get_sources()
        except Exception as e:
            _logger.error(f"Exception: {e}", exc_info=True)
            self._options = None

        try:
            self._device_name = self._controller.get_devices()[self._device_number]
        except Exception as e:
            _logger.error(f"Exception: {e}", exc_info=True)
            self._device_name = None


        try:
            source_number = self._controller.get_output_status().get("allsource")[self._device_number] - 1
            self.current_option = self._controller.get_input_status().get("inname")[source_number]
        except Exception as e:
            _logger.error(f"Exception: {e}", exc_info=True)
            self.current_option = None

    @property
    def name(self):
        """Return the name of the zone."""
        return  self._device_name

    @property
    def options(self):
        """Return the name of the zone."""
        return  self._options or []

    @property
    def unique_id(self):
        """Return the current input source of the device."""
        return self._unique_id

    def select_option(self, option: str) -> None:
        """Set input option."""
        option_num = self.options.index(option)
        if not option_num:
            _logger.error(f"Unknown Option: {option}, N: {option_num}")
            return

        _logger.debug(f'Setting device {self._device_number} source to {option_num}')
        power_off = False
        if not self._controller.are_devices_powered_on():
            self._controller.power_on_devices()
            power_off = True
        self._controller.set_device_source(device_num=self._device_number + 1, source_num=option_num + 1)
        self.current_option = option
        if power_off:
            self._controller.power_off_devices()
