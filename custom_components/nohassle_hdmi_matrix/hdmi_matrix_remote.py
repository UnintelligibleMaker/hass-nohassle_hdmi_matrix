"""CEC remote entities for the HDMI Matrix.

One `remote` entity per port, both directions (object 1 = output/display, 0 =
input/source). The remote's built-in on/off is the CEC power command; the key
codes are sent via `remote.send_command`. Command/index maps were decompiled
from the matrix's own web UI (chunk-2e33ab38); `object` disambiguates — the same
integer means different things for inputs vs outputs.
"""
import logging

from homeassistant.components.remote import RemoteEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_logger = logging.getLogger(__name__)

# CEC key codes, keyed by `object` (1 = output, 0 = input).
# Power is (on, off); send_command maps canonical names -> code.
_OUTPUT_POWER = (0, 1)
_OUTPUT_COMMANDS = {
    "mute": 2,
    "volume_down": 3,
    "volume_up": 4,
}

_INPUT_POWER = (1, 2)
_INPUT_COMMANDS = {
    "up": 3,
    "left": 4,
    "ok": 5,
    "right": 6,
    "menu": 7,
    "down": 8,
    "back": 9,
    "previous": 10,
    "play": 11,
    "next": 12,
    "rewind": 13,
    "pause": 14,
    "fast_forward": 15,
    "stop": 16,
    "mute": 17,
    "volume_down": 18,
    "volume_up": 19,
}


class HDMIMatrixCecRemote(RemoteEntity):
    """A CEC remote for one matrix port (output display or input source)."""

    _attr_assumed_state = True  # CEC power state is best-effort (the field lies)
    _attr_should_poll = True

    def __init__(self, hdmi_host, controller, port, is_output):
        self._host = hdmi_host
        self._controller = controller
        self._port = port
        self._is_output = is_output
        self._object = 1 if is_output else 0
        self._power = _OUTPUT_POWER if is_output else _INPUT_POWER
        self._commands = _OUTPUT_COMMANDS if is_output else _INPUT_COMMANDS
        tag = "output" if is_output else "input"
        self._unique_id = f"{hdmi_host}-{tag}-{port}-cec"
        self._attr_name = f"{self._port_name()} CEC"
        self._is_on = False
        self._available = False

    # ---- naming (output names from get_devices, input names from get_sources) ----
    def _port_name(self):
        try:
            names = (
                self._controller.get_devices()
                if self._is_output
                else self._controller.get_sources()
            )
            name = (names or [])[self._port]
            if name:
                return name
        except Exception:  # noqa: BLE001
            pass
        return f"{'Output' if self._is_output else 'Input'} {self._port + 1}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def available(self):
        return self._available

    @property
    def is_on(self):
        return self._is_on

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name="Living Room HDMI Matrix",
            manufacturer="No Hassle AV",
            model="HDP-MXB88DA",
            configuration_url=f"http://{self._host}/",
        )

    @property
    def extra_state_attributes(self):
        return {"cec_commands": sorted(self._commands)}

    # ---- helpers ----
    def _port_mask(self):
        mask = [0] * 8
        mask[self._port] = 1
        return mask

    def _send(self, index):
        self._controller.send_cec(self._object, self._port_mask(), index)

    # ---- control ----
    def turn_on(self, **kwargs):
        self._send(self._power[0])
        self._is_on = True

    def turn_off(self, **kwargs):
        self._send(self._power[1])
        self._is_on = False

    def send_command(self, command, **kwargs):
        repeats = kwargs.get("num_repeats", 1)
        for _ in range(repeats):
            for cmd in command:
                code = self._commands.get(cmd)
                if code is None:
                    _logger.warning(
                        "Unknown CEC command '%s' for %s (valid: %s)",
                        cmd, self._attr_name, ", ".join(sorted(self._commands)),
                    )
                    continue
                self._send(code)

    # ---- state ----
    def update(self):
        try:
            cec = self._controller.get_cec_status() or {}
            powered = bool(cec.get("power"))
            if not powered:
                self._available = False
                return
            if self._is_output:
                out = self._controller.get_output_status() or {}
                connected = bool((out.get("allconnect") or [0] * 8)[self._port])
                self._available = connected
                cur = cec.get("currentOutput") or [0] * 8
            else:
                inp = self._controller.get_input_status() or {}
                live = (inp.get("inactive") or [1] * 8)[self._port] == 0
                self._available = live
                cur = cec.get("currentInput") or [0] * 8
            self._is_on = bool(cur[self._port])
        except Exception as e:  # noqa: BLE001
            _logger.debug("CEC remote update failed (%s): %s", self._attr_name, e, exc_info=True)
            self._available = False

    # ---- telnet push registration ----
    async def async_added_to_hass(self):
        manager = getattr(self, "_manager", None)
        if manager is not None:
            manager.register_entity(self)

    async def async_will_remove_from_hass(self):
        manager = getattr(self, "_manager", None)
        if manager is not None:
            manager.unregister_entity(self)
