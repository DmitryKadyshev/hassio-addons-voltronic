# Voltronic Home Assistant Add-on

Monitor and control Voltronic-based inverters from Home Assistant.

## Features

- Reads inverter status through `/dev/hidraw*`.
- Publishes inverter data to MQTT.
- Integrates with Home Assistant through MQTT discovery.
- Automatically reconnects to the inverter and MQTT broker after communication failures.
- Supports the Home Assistant architectures configured by the add-on.

## Requirements

- Home Assistant with add-on support.
- A compatible Voltronic-based inverter.
- Access to the inverter USB/HID device, exposed as `/dev/hidraw0` (or another configured `hidraw` device).
- An MQTT broker reachable from Home Assistant.

## Installation

1. Open **Settings → Add-ons → Add-on Store** in Home Assistant.
2. Open the repository menu and add this GitHub repository as an add-on repository.
3. Install **Voltronic**.
4. Configure the inverter device and MQTT connection settings.
5. Start the add-on and check the add-on log for connection status.

## Configuration

The add-on configuration is validated when it starts. The main settings are:

| Option | Description | Example |
| --- | --- | --- |
| `device` | HID device used by the inverter | `/dev/hidraw0` |
| `run_interval` | Polling interval in seconds | `5` |
| `amperage_factor` | Current scaling factor | `1.0` |
| `watt_factor` | Power scaling factor | `1.0` |
| `qpiri` | QPIRI polling interval in seconds | `97` |
| `qpiws` | QPIWS polling interval in seconds | `36` |
| `qmod` | QMOD polling interval in seconds | `5` |
| `qpigs` | QPIGS polling interval in seconds | `110` |
| `mqtt_server` | MQTT broker hostname | `mosquitto` |
| `mqtt_port` | MQTT broker port | `1883` |
| `mqtt_topic` | MQTT base topic | `homeassistant` |
| `devicename` | Device name shown in Home Assistant | `voltronic` |
| `mqtt_username` | MQTT username, if required | — |
| `mqtt_password` | MQTT password, if required | — |

For security, MQTT credentials are empty by default. Configure them only when your broker requires authentication.

## Development

The project contains the Python application under `src/app/voltronic` and the Home Assistant add-on runtime files under `src/rootfs`.

Run the test suite locally with:

```bash
python3 -m pytest -q
```

The GitHub Actions test workflow runs the same pytest suite on pull requests and pushes.

## Troubleshooting

### The inverter is not detected

Check that the correct HID device is configured and that Home Assistant has access to it. On the host, inspect available devices with:

```bash
ls -l /dev/hidraw*
```

### MQTT entities are missing

Verify the MQTT broker address, port, and credentials. After a reconnect, the add-on republishes Home Assistant MQTT discovery information.

### The add-on exits during startup

Check the add-on log for a configuration validation error. Invalid or missing values are rejected before the inverter and MQTT connections are started.

## License

No separate license file is currently included in this repository.
