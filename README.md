No Hassle AV HDMI Matrix
============
This is my rewrite of: https://github.com/IDmedia/hass-nohassle_hdmi_matrix

A Home Assistant integration for No Hassle AV HDMI matrix switches (e.g. the
HDP-MXB88DA 8x8). Source and output names are pulled from the device itself,
not from the config. It exposes the matrix as a **single device** with a power
switch and one select per output, and listens to the matrix's telnet event
stream for near-instant state updates (HTTP polling is kept as a backstop).

## Installation using HACS (Recommended)
1. Navigate to HACS and add a custom repository
    **URL:** https://github.com/UnintelligibleMaker/hass-nohassle_hdmi_matrix
    **Category:** Integration
2. Install the integration
3. Restart Home Assistant

## Configuration
Configured from the UI — no YAML.

1. **Settings → Devices & Services → Add Integration**
2. Search for **No Hassle AV HDMI Matrix**
3. Enter the **host** (IP or hostname) of the matrix

| Key | Required | Description |
| --- | --- | --- |
| host | yes | The IP or hostname of your HDMI matrix |

That creates one device with all its entities grouped under it. You can reload
or remove it from Settings → Devices & Services without restarting Home Assistant.

### Migrating from the old YAML config
Older versions were set up with `switch:` / `select:` platform blocks in
`configuration.yaml`. If you still have those, they are **imported automatically**
into a config entry on the next restart — entity IDs and history are preserved.
Once the device shows up, delete the old blocks:
```yaml
# remove these once the integration appears under Devices & Services:
switch:
  - platform: nohassle_hdmi_matrix
    host: 192.168.1.168
select:
  - platform: nohassle_hdmi_matrix
    host: 192.168.1.168
```

## Entities
You get **one device** with 9 entities:
* **1x switch** — power on/off of the unit
* **8x select** — one per output; the options are the input names read from the device

Example:
```
Power            [ On, Off ]
Output1          [ Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8 ]
Output2          [ Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8 ]
 ...
Output8          [ Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8 ]
```
The switch and output names come from the device, so they match whatever you've
named things on the matrix.

## CEC control
The matrix can also inject HDMI-CEC to each **output** (display/AVR) and **input**
(source). This is exposed as one `remote` entity per port — 16 total, named
`<Port Name> CEC`:

* **Outputs** (`remote.<output>_cec`): `remote.turn_on` / `turn_off` = CEC power;
  `remote.send_command` supports `mute`, `volume_up`, `volume_down`.
* **Inputs** (`remote.<input>_cec`): `remote.turn_on` / `turn_off` = CEC power;
  `remote.send_command` supports `up`, `down`, `left`, `right`, `ok`, `menu`,
  `back`, `play`, `pause`, `stop`, `previous`, `next`, `rewind`, `fast_forward`,
  `mute`, `volume_up`, `volume_down`.

Each remote's valid command list is also published in its `cec_commands`
attribute. Example:

```yaml
service: remote.send_command
target:
  entity_id: remote.fire_tv_cec
data:
  command: play
```

**Availability is live-gated** (CEC only works while the matrix is powered on):
a CEC remote is `unavailable` when the matrix is off, when its **output** has no
connected display, or when its **input** has no live signal. Power state is
reported best-effort (`assumed_state`) — the matrix's CEC power field is not
fully reliable, so these remotes don't try to lie about it.

> CEC does nothing while the matrix is in standby. This integration deliberately
> does **not** auto-power the matrix — if you want "turn the matrix on, wait,
> then CEC-power a TV," build that as a Home Assistant automation.
