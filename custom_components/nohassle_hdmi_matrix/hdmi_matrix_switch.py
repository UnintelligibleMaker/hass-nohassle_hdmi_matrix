"""Support for interfacing with HDMI Matrix."""

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_logger = logging.getLogger(__name__)

class HDMIMatrixSwitch(SwitchEntity):
    """Representation of an HDMI matrix device (power)."""

    def __init__(self, hdmi_host, controller):
        self._controller = controller
        self._host = hdmi_host
        self._unique_id = f'{hdmi_host}-power-switch'
        self._device_name = f'{hdmi_host} Power Switch'
        self._is_on = self._controller.are_devices_powered_on()

    def update(self):
        """Retrieve latest state."""
        try:
            self._is_on = self._controller.are_devices_powered_on()
        except Exception as e:
            _logger.debug(f"Exception: {e}", exc_info=True)
            self._is_on = None

    @property
    def name(self):
        """Return the name of the zone."""
        return self._device_name

    @property
    def unique_id(self):
        """Return the unique id of the device."""
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

    @property
    def is_on(self):
        """Return whether the matrix is powered on."""
        return self._is_on

    def turn_on(self, **kwargs):
        self._controller.power_on_devices()

    def turn_off(self, **kwargs):
        self._controller.power_off_devices()

    async def async_added_to_hass(self):
        manager = getattr(self, "_manager", None)
        if manager is not None:
            manager.register_entity(self)

    async def async_will_remove_from_hass(self):
        manager = getattr(self, "_manager", None)
        if manager is not None:
            manager.unregister_entity(self)
