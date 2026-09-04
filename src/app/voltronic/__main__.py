"""Entry point: one process, one MQTT connection, one poll loop."""

from __future__ import annotations

import logging
import signal
import sys
import threading

from . import parser
from .config import Config
from .inverter import Inverter
from .mqtt import MqttClient

SW_VERSION = "0.4.4"

log = logging.getLogger("REDACTED")


def _poll_once(inv: Inverter, cfg: Config) -> tuple[int, dict, dict, str] | None:
    """Run QMOD + QPIGS + QPIRI + QPIWS, return parsed values or None on any failure."""
    qmod = inv.query("QMOD", cfg.qmod)
    if qmod is None:
        return None
    mode = parser.parse_qmod(qmod)

    qpigs_raw = inv.query("QPIGS", cfg.qpigs)
    if qpigs_raw is None:
        return None
    qpigs = parser.parse_qpigs(qpigs_raw)
    if qpigs is None:
        log.warning("QPIGS parse failed: %r", qpigs_raw)
        return None

    qpiri_raw = inv.query("QPIRI", cfg.qpiri)
    if qpiri_raw is None:
        return None
    qpiri = parser.parse_qpiri(qpiri_raw)
    if qpiri is None:
        log.warning("QPIRI parse failed: %r", qpiri_raw)
        return None

    qpiws_raw = inv.query("QPIWS", cfg.qpiws)
    warnings = parser.parse_qpiws(qpiws_raw) if qpiws_raw is not None else ""
    return mode, qpigs, qpiri, warnings


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = Config.load()
    log.info("REDACTED %s starting; poll every %ds via %s", SW_VERSION, cfg.run_interval, cfg.device)

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    inv = Inverter(cfg.device)
    mqttc = MqttClient(
        host=cfg.mqtt_server,
        port=cfg.mqtt_port,
        username=cfg.mqtt_username,
        password=cfg.mqtt_password,
        base_topic=cfg.mqtt_topic,
        devicename=cfg.devicename,
    )

    discovery_generation = 0
    try:
        mqttc.connect()
        while not stop.is_set():
            if mqttc.is_connected and mqttc.connection_generation != discovery_generation:
                mqttc.publish_discovery(parser.SENSORS, SW_VERSION)
                discovery_generation = mqttc.connection_generation

            snapshot = _poll_once(inv, cfg)
            if snapshot is not None:
                mode, qpigs, qpiri, warnings = snapshot
                state = parser.build_state(
                    mode, qpigs, qpiri, warnings,
                    amperage_factor=cfg.amperage_factor,
                    watt_factor=cfg.watt_factor,
                    run_interval=cfg.run_interval,
                )
                if mqttc.is_connected:
                    mqttc.publish_state(state)
                else:
                    log.warning("skipping publish: MQTT not connected yet")

            stop.wait(cfg.run_interval)
    finally:
        inv.close()
        mqttc.shutdown()
    log.info("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
