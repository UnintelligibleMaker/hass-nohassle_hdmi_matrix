"""CEC media_player entities for the HDMI Matrix.

A clickable `media_player` per port, alongside the companion `remote` keypad:
- outputs (displays/AVRs): power + volume step + mute
- inputs (sources): power + transport (play/pause/stop/next/previous)
The nav/menu CEC keys that media_player has no slot for live on the `remote`
entity. CEC index codes are disambiguated by `object` (see hdmi_matrix_remote.py).
"""
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_logger = logging.getLogger(__name__)

_OUTPUT_FEATURES = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
)
_INPUT_FEATURES = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
)

# CEC key codes (object 1 = output, 0 = input).
_OUTPUT_POWER = (0, 1)
_OUTPUT_MUTE = 2
_OUTPUT_VOL_DOWN = 3
_OUTPUT_VOL_UP = 4
_INPUT_POWER = (1, 2)
_INPUT_PREV = 10
_INPUT_PLAY = 11
_INPUT_NEXT = 12
_INPUT_PAUSE = 14
_INPUT_STOP = 16


class HDMIMatrixMediaPlayer(MediaPlayerEntity):
    """Clickable CEC control for one matrix port (output display or input source)."""

    _attr_assumed_state = True  # CEC power state is best-effort (the field lies)
    _attr_should_poll = True

    def __init__(self, hdmi_host, controller, port, is_output):
        self._host = hdmi_host
        self._controller = controller
        self._port = port
        self._is_output = is_output
        self._object = 1 if is_output else 0
        self._power = _OUTPUT_POWER if is_output else _INPUT_POWER
        tag = "output" if is_output else "input"
        suffix = "Display" if is_output else "Source"
        self._unique_id = f"{hdmi_host}-{tag}-{port}-mediaplayer"
        self._attr_supported_features = _OUTPUT_FEATURES if is_output else _INPUT_FEATURES
        self._attr_name = f"{self._port_name()} {suffix}"
        self._is_on = False
        self._available = False

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
    def state(self):
        return MediaPlayerState.ON if self._is_on else MediaPlayerState.OFF

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._host)},
            name="Living Room HDMI Matrix",
            manufacturer="No Hassle AV",
            model="HDP-MXB88DA",
            configuration_url=f"http://{self._host}/",
        )

    # ---- helpers ----
    def _port_mask(self):
        mask = [0] * 8
        mask[self._port] = 1
        return mask

    def _send(self, index):
        self._controller.send_cec(self._object, self._port_mask(), index)

    # ---- control (outputs) ----
    def turn_on(self):
        self._send(self._power[0])
        self._is_on = True

    def turn_off(self):
        self._send(self._power[1])
        self._is_on = False

    def volume_up(self):
        self._send(_OUTPUT_VOL_UP)

    def volume_down(self):
        self._send(_OUTPUT_VOL_DOWN)

    def mute_volume(self, mute):
        # CEC mute is a toggle; the requested boolean can't be honored exactly.
        self._send(_OUTPUT_MUTE)

    # ---- control (inputs) ----
    def media_play(self):
        self._send(_INPUT_PLAY)

    def media_pause(self):
        self._send(_INPUT_PAUSE)

    def media_stop(self):
        self._send(_INPUT_STOP)

    def media_next_track(self):
        self._send(_INPUT_NEXT)

    def media_previous_track(self):
        self._send(_INPUT_PREV)

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
                self._available = bool((out.get("allconnect") or [0] * 8)[self._port])
                cur = cec.get("currentOutput") or [0] * 8
            else:
                inp = self._controller.get_input_status() or {}
                self._available = (inp.get("inactive") or [1] * 8)[self._port] == 0
                cur = cec.get("currentInput") or [0] * 8
            self._is_on = bool(cur[self._port])
        except Exception as e:  # noqa: BLE001
            _logger.debug("CEC media_player update failed (%s): %s", self._attr_name, e, exc_info=True)
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
