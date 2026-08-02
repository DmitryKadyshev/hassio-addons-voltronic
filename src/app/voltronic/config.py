"""Add-on configuration loaded from /data/options.json (HA supervisor convention)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


OPTIONS_PATH = Path(os.environ.get("VOLTRONIC_OPTIONS", "/data/options.json"))


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
        raw = json.loads((path or OPTIONS_PATH).read_text())
        return cls(
            device=raw["device"],
            run_interval=int(raw["run_interval"]),
            amperage_factor=float(raw["amperage_factor"]),
            watt_factor=float(raw["watt_factor"]),
            qpiri=int(raw["qpiri"]),
            qpiws=int(raw["qpiws"]),
            qmod=int(raw["qmod"]),
            qpigs=int(raw["qpigs"]),
            mqtt_server=raw["mqtt_server"],
            mqtt_port=int(raw["mqtt_port"]),
            mqtt_topic=raw["mqtt_topic"],
            devicename=raw["devicename"],
            mqtt_username=raw["mqtt_username"],
            mqtt_password=raw["mqtt_password"],
        )
