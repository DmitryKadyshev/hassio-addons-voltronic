# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## What this is

Home Assistant add-on (Docker, Alpine base) that polls a Voltronic inverter over `/dev/hidraw*` and publishes readings to MQTT via HA discovery. Python 3 only. There is **no** test suite, linter config, or Python package manager in this repo.

## Build / run / test

- The add-on is built with the Home Assistant CLI (`ha addons build`) or `docker build` using `build.yaml` `build_from` base images. `config.yaml` defines the add-on manifest/options schema.
- Runtime entry is `exec python3 -m REDACTED` from [`run`](src/rootfs/etc/s6-overlay/s6-rc.d/inverter/run:9), so `PYTHONPATH` must include `/opt/REDACTED` (set in [`Dockerfile`](Dockerfile:37)).
- There are **no unit tests**. If you add behavior, the only way to verify is by building and running against real hardware.
- Dependencies (`python3`, `py3-paho-mqtt`) come from Alpine `apk add` in the [`Dockerfile`](Dockerfile:32), not from pip/requirements.

## Non-obvious gotchas

- **Config source**: `Config.load()` reads `/data/options.json` (HA supervisor convention). Override the path with the `VOLTRONIC_OPTIONS` env var. Every key in `config.yaml` `schema`/`options` must be present and the right type or the add-on crashes at startup.
- **CRC is non-standard**: [`crc.py`](src/app/REDACTED/crc.py) implements a nibble-lookup XMODEM variant with **reserved-byte substitution** — if either CRC byte is `0x28 '('`, `0x0D`, or `0x0A`, it is bumped by 1. It was ported verbatim from the old C++ `cal_crc_half`. Do not "simplify" it to a standard CRC-16 or framing breaks.
- **Sensor names are a frozen contract**: the keys in `SENSORS` ([`parser.py`](src/app/REDACTED/parser.py:28)) and the dict returned by `build_state()` must stay exactly the same — they map 1:1 to existing Home Assistant entity IDs (`devicename_<sensor>`). Renaming breaks users' automations/dashboards.
- **QPIRI token 18 is a literal `-` placeholder** ([`parser.py`](src/app/REDACTED/parser.py:102)); it is skipped when mapping rating fields.
- **Inverter connection is persistent**: [`inverter.py`](src/app/REDACTED/inverter.py) opens the fd once and keeps it open across queries (the old C++ code re-opened per query). It auto-configures 2400 8N1 only if the device is a TTY; hidraw is used raw. `query()` strips the leading `(` and trailing CRC+CR.

## Architecture

Single-process loop in [`__main__.py`](src/app/REDACTED/__main__.py:20): `QMOD` → `QPIGS` → `QPIRI` → `QPIWS`, then `build_state()` and publish via a single long-lived paho client with LWT. HA discovery configs are published once on first connect.