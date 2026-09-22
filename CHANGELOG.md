# Changelog

## 0.4.8 - 2026-09-22

- Added optional startup auto-detection of the Voltronic inverter across all `/dev/hidraw*` devices.
- Auto-detection probes each device with `QMOD` and accepts only a valid Voltronic protocol response.
- Added the `auto_detect_device` boolean configuration option; disabled by default.


All notable changes to this Home Assistant add-on are documented here.

## 0.4.7 - 2026-09-04

- Fixed GHCR package publishing permissions.
- Restored project/module paths after the security history cleanup.
- Added startup configuration validation.
- Removed default MQTT credentials from the add-on configuration.
- Disabled unused Home Assistant API access.
- Improved reconnect and MQTT discovery reliability.
- Added automated tests and multi-architecture container builds.
- Added project documentation.
