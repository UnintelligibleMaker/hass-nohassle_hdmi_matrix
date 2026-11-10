"""Config flow for the No Hassle AV HDMI Matrix integration."""
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .nohassle_hdmi_matrix import NoHassleHDMOMatrixController

_LOGGER = logging.getLogger(__name__)


def _test_connection(host: str) -> bool:
    """Blocking reachability check (run in an executor)."""
    try:
        return NoHassleHDMOMatrixController(host=host).get_status() is not None
    except Exception:  # noqa: BLE001 - any failure means "not reachable"
        return False


class NoHassleHDMIMatrixConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the No Hassle AV HDMI Matrix."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a user-initiated setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            if await self.hass.async_add_executor_job(_test_connection, host):
                return self.async_create_entry(title=host, data={CONF_HOST: host})
            errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_import(self, import_data) -> FlowResult:
        """Import the legacy YAML (switch:/select: platforms) into a config entry.

        Both platforms fire this; async_set_unique_id (raise_on_progress) makes the
        second abort, so only one entry is ever created per host.
        """
        host = import_data[CONF_HOST]
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=host, data={CONF_HOST: host})
