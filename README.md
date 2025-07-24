No Hassle AV HDMI Matrix
============
This is my rewrite of: https://github.com/IDmedia/hass-nohassle_hdmi_matrix  

## Installation using HACS (Recommended)
1. Navigate to HACS and add a custom repository  
    **URL:** https://github.com/UnintelligibleMaker/hass-nohassle_hdmi_matrix
    **Category:** Integration
2. Install module as usual
3. Restart Home Assistant

## Configuration
| Key | Default | Required | Description
| --- | --- | --- | ---
| host | 127.0.0.1 | no | The ip or hostname of your hdmi matrix.

## Example
Add the following to your `configuration.yaml`:
```
select:
  - platform: nohassle_hdmi_matrix
    host: 192.168.1.168

switch:
  - platform: nohassle_hdmi_matrix
    host: 192.168.1.168    
```

The Select is for the outputs to select input.
The Switch is for the main power on/off of the unit.

## Usage
You should have 9 new entities:
* 1x Switch - On/Off of unit
* 8x Selectors with the names from the device.  Example

```
192.168.1.168 Power - [ On, Off ]
Output1 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
Output2 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
Output3 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
Output4 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
Output5 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
Output6 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
Output7 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
Output8 - [Input1, Input2, Input3, Input4, Input5, Input6, Input7, Input8]
```