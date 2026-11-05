"""Event-driven (push) layer for the No Hassle HDMI matrix.

The matrix exposes a telnet stream on port 23 that narrates state changes in
real time, e.g.:

    input 5 -> output 8          # routing changed
    power off                    # powered off
    hdmi input 6: sync           # an input synced (implies powered on)
    hdmi output 2: connect       # an output connected

This module holds ONE persistent telnet connection per host and, whenever it
sees a state-changing line, invalidates the shared controller's read cache and
forces an immediate refresh of the registered entities. It is purely additive:
writes still go over the cgi HTTP API, and the entities keep their normal
polling as a backstop, so if telnet is unreachable everything degrades to plain
(cached) polling with no loss of function.
"""

import asyncio
import logging
import re

from homeassistant.const import EVENT_HOMEASSISTANT_STOP

from .nohassle_hdmi_matrix import NoHassleHDMOMatrixController

_LOGGER = logging.getLogger(__name__)

DATA_HOSTS = "nohassle_hdmi_matrix_hosts"
TELNET_PORT = 23

_ROUTE_RE = re.compile(rb"input\s+\d+\s*->\s*output\s+\d+", re.IGNORECASE)
_POWER_RE = re.compile(rb"power\s+(on|off)", re.IGNORECASE)
_ALIVE_HINTS = (b"sync", b"connect", b"initialization finished")

_REFRESH_DEBOUNCE = 0.4  # s — collapse a burst of events (e.g. the power-on cascade) into one refresh


def _strip_iac(data: bytes) -> bytes:
    """Drop telnet IAC negotiation sequences (0xFF + command [+ option])."""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b == 0xFF:
            # WILL/WONT/DO/DONT (251-254) carry one option byte; others carry none.
            if i + 1 < n and 251 <= data[i + 1] <= 254:
                i += 3
            else:
                i += 2
            continue
        out.append(b)
        i += 1
    return bytes(out)


class MatrixEventManager:
    """Owns the persistent telnet connection and pushes refreshes to entities."""

    def __init__(self, hass, host, controller):
        self._hass = hass
        self._host = host
        self._controller = controller
        self._entities = set()
        self._task = None
        self._debounce = None
        self._closing = False

    # -- entity registration (called from entities' async_added/removed) --
    def register_entity(self, entity) -> None:
        self._entities.add(entity)

    def unregister_entity(self, entity) -> None:
        self._entities.discard(entity)

    # -- lifecycle (scheduled on the loop) --
    def start(self) -> None:
        if self._task is None:
            self._task = self._hass.loop.create_task(self._runner())

    async def async_stop(self) -> None:
        self._closing = True
        if self._debounce is not None:
            self._debounce.cancel()
            self._debounce = None
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    # -- telnet read loop with reconnect/backoff --
    async def _runner(self) -> None:
        backoff = 2
        while not self._closing:
            writer = None
            try:
                reader, writer = await asyncio.open_connection(self._host, TELNET_PORT)
                _LOGGER.info("HDMI matrix telnet connected (%s:%s)", self._host, TELNET_PORT)
                backoff = 2
                # A fresh connection means we may have missed events while down — resync once.
                self._schedule_refresh()
                buf = b""
                while not self._closing:
                    data = await reader.read(256)
                    if not data:
                        break  # remote closed
                    buf += _strip_iac(data)
                    while b"\n" in buf:
                        raw, buf = buf.split(b"\n", 1)
                        self._handle_line(raw)
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the loop alive on any socket error
                _LOGGER.warning("HDMI matrix telnet connection error: %s", err)
            finally:
                if writer is not None:
                    try:
                        writer.close()
                    except Exception:  # noqa: BLE001
                        pass
            if not self._closing:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    def _handle_line(self, raw: bytes) -> None:
        line = raw.strip()
        if not line:
            return
        lower = line.lower()
        if (
            _ROUTE_RE.search(line)
            or _POWER_RE.search(line)
            or any(hint in lower for hint in _ALIVE_HINTS)
        ):
            _LOGGER.debug("HDMI matrix event: %s", line)
            self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        if self._debounce is not None:
            self._debounce.cancel()
        self._debounce = self._hass.loop.call_later(_REFRESH_DEBOUNCE, self._do_refresh)

    def _do_refresh(self) -> None:
        self._debounce = None
        try:
            self._controller._invalidate_cache()
        except Exception:  # noqa: BLE001
            pass
        for entity in list(self._entities):
            try:
                entity.async_schedule_update_ha_state(True)
            except Exception:  # noqa: BLE001
                pass


def get_host_bundle(hass, host):
    """Return the shared {'controller', 'manager'} for a host, creating once.

    Called from the (executor-thread) setup_platform of both the switch and
    select platforms, so it must be safe to call more than once per host.
    """
    hosts = hass.data.setdefault(DATA_HOSTS, {})
    bundle = hosts.get(host)
    if bundle is not None:
        return bundle

    controller = NoHassleHDMOMatrixController(host=host)
    manager = MatrixEventManager(hass, host, controller)
    bundle = {"controller": controller, "manager": manager}
    hosts[host] = bundle

    # Telnet is best-effort: never let it block/break entity setup.
    try:
        hass.add_job(manager.start)
        hass.bus.listen_once(
            EVENT_HOMEASSISTANT_STOP, lambda _evt: hass.add_job(manager.async_stop)
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("HDMI matrix telnet event manager unavailable: %s", err)

    return bundle
