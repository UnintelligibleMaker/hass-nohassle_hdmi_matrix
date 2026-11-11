"""Support for interfacing with HDMI Matrix."""

import logging
import voluptuous as vol

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_logger = logging.getLogger(__name__)

class HDMIMatrixSelect(SelectEntity):
    """Representation of an HDMI matrix device (output)."""

    def __init__(self, hdmi_host, device_num, controller):
        self._device_number = device_num
        self._controller = controller
        self._host = hdmi_host
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

    @property
    def device_info(self) -> DeviceInfo:
        """Group this entity under the single matrix device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name="Living Room HDMI Matrix",
            manufacturer="No Hassle AV",
            model="HDP-MXB88DA",
            configuration_url=f"http://{self._host}/",
        )

    def select_option(self, option: str) -> None:
        """Set input option."""
        try:
            option_num = self.options.index(option)
        except ValueError:
            _logger.error(f"Unknown option: {option}")
            return

        _logger.debug(f'Setting device {self._device_number} source to {option_num}')
        # The matrix accepts `video switch` while powered off and the change persists
        # through its next power-on (verified on fw V1.03.33), so routing is done
        # directly with no power-on/off dance — the driver never powers the matrix.
        self._controller.set_device_source(device_num=self._device_number + 1, source_num=option_num + 1)
        self.current_option = option

    async def async_added_to_hass(self):
        manager = getattr(self, "_manager", None)
        if manager is not None:
            manager.register_entity(self)

    async def async_will_remove_from_hass(self):
        manager = getattr(self, "_manager", None)
        if manager is not None:
            manager.unregister_entity(self)
