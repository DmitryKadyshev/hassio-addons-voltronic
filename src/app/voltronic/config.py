"""Add-on configuration loaded from /data/options.json (HA Supervisor convention)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


OPTIONS_PATH = Path(os.environ.get("VOLTRONIC_OPTIONS", "/data/options.json"))


class ConfigError(ValueError):
    """Raised when add-on configuration is invalid."""


@dataclass(frozen=True)
class Config:
    device: str
    run_interval: int
    amperage_factor: float
    watt_factor: float
    qpiri: int
    qpiws: int
    qmod: int
    qpigs: int
    mqtt_server: str
    mqtt_port: int
    mqtt_topic: str
    devicename: str
    mqtt_username: str
    mqtt_password: str

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        config_path = path or OPTIONS_PATH
        try:
            raw = json.loads(config_path.read_text())
        except FileNotFoundError as exc:
            raise ConfigError(f"configuration file not found: {config_path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"invalid JSON in configuration: {config_path}") from exc

        if not isinstance(raw, dict):
            raise ConfigError("configuration root must be a JSON object")

        required = (
            "device", "run_interval", "amperage_factor", "watt_factor",
            "qpiri", "qpiws", "qmod", "qpigs", "mqtt_server", "mqtt_port",
            "mqtt_topic", "devicename", "mqtt_username", "mqtt_password",
        )
        missing = [key for key in required if key not in raw]
        if missing:
            raise ConfigError(f"missing configuration keys: {', '.join(missing)}")

        try:
            cfg = cls(
                device=raw["device"], run_interval=int(raw["run_interval"]),
                amperage_factor=float(raw["amperage_factor"]), watt_factor=float(raw["watt_factor"]),
                qpiri=int(raw["qpiri"]), qpiws=int(raw["qpiws"]),
                qmod=int(raw["qmod"]), qpigs=int(raw["qpigs"]),
                mqtt_server=raw["mqtt_server"], mqtt_port=int(raw["mqtt_port"]),
                mqtt_topic=raw["mqtt_topic"], devicename=raw["devicename"],
                mqtt_username=raw["mqtt_username"], mqtt_password=raw["mqtt_password"],
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise ConfigError("configuration contains invalid value types") from exc

        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not isinstance(self.device, str) or not self.device.startswith(("/dev/hidraw", "/dev/ttyUSB")):
            raise ConfigError("device must be a /dev/hidraw* or /dev/ttyUSB* path")
        if self.run_interval < 1:
            raise ConfigError("run_interval must be at least 1 second")
        if self.amperage_factor <= 0 or self.watt_factor <= 0:
            raise ConfigError("amperage_factor and watt_factor must be greater than zero")
        for name, value in (("qpiri", self.qpiri), ("qpiws", self.qpiws), ("qmod", self.qmod), ("qpigs", self.qpigs)):
            if value < 1:
                raise ConfigError(f"{name} must be greater than zero")
        if not 1 <= self.mqtt_port <= 65535:
            raise ConfigError("mqtt_port must be between 1 and 65535")
        for name, value in (("mqtt_server", self.mqtt_server), ("mqtt_topic", self.mqtt_topic), ("devicename", self.devicename)):
            if not isinstance(value, str) or not value.strip():
                raise ConfigError(f"{name} must not be empty")
        if bool(self.mqtt_username) != bool(self.mqtt_password):
            raise ConfigError("mqtt_username and mqtt_password must be provided together")
