"""Long-lived MQTT client wrapping paho-mqtt with LWT + HA discovery.

One TCP connection for the process lifetime. Discovery configs and every state
update publish through the same socket — no more spawning `mosquitto_pub` per
field like the old `mqtt-push.sh` did.
"""

from __future__ import annotations

import json
import logging
from typing import Iterable

import paho.mqtt.client as mqtt

from .parser import SensorSpec

log = logging.getLogger(__name__)


class MqttClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        base_topic: str,
        devicename: str,
    ) -> None:
        self._host = host
        self._port = port
        self._base = base_topic
        self._devicename = devicename
        self._availability_topic = f"{base_topic}/{devicename}/availability"
        self._connected = False

        # paho-mqtt v2 requires an explicit callback_api_version. Prefer VERSION2;
        # fall back to unspecified for older builds that pre-date that enum.
        client_kwargs = {"client_id": devicename, "clean_session": True}
        api_v2 = getattr(mqtt, "CallbackAPIVersion", None)
        if api_v2 is not None:
            client_kwargs["callback_api_version"] = api_v2.VERSION2
        self._client = mqtt.Client(**client_kwargs)

        if username:
            self._client.username_pw_set(username, password)
        self._client.will_set(self._availability_topic, "offline", qos=0, retain=True)
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def connect(self) -> None:
        log.info("connecting to %s:%d", self._host, self._port)
        self._client.connect_async(self._host, self._port, keepalive=60)
        self._client.loop_start()

    def shutdown(self) -> None:
        try:
            self._client.publish(self._availability_topic, "offline", qos=0, retain=True).wait_for_publish(timeout=2)
        except Exception:
            pass
        self._client.loop_stop()
        try:
            self._client.disconnect()
        except Exception:
            pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    def publish(self, topic: str, payload: str, retain: bool = True) -> None:
        self._client.publish(topic, payload, qos=0, retain=retain)

    def publish_state(self, values: dict[str, str]) -> None:
        for name, value in values.items():
            self._client.publish(
                f"{self._base}/sensor/{self._devicename}_{name}",
                value, qos=0, retain=True,
            )

    def publish_discovery(self, sensors: Iterable[SensorSpec], sw_version: str) -> None:
        device_block = {
            "identifiers": [self._devicename],
            "name": self._devicename,
            "manufacturer": "Voltronic",
            "model": "Inverter",
            "sw_version": sw_version,
        }
        for spec in sensors:
            topic = f"{self._base}/sensor/{self._devicename}_{spec.name}/config"
            payload = {
                "name": spec.friendly_name or f"{self._devicename}_{spec.name}",
                "object_id": f"{self._devicename}_{spec.name}",
                "unique_id": f"{self._devicename}_{spec.name}",
                "state_topic": f"{self._base}/sensor/{self._devicename}_{spec.name}",
                "availability_topic": self._availability_topic,
                "payload_available": "online",
                "payload_not_available": "offline",
                "icon": f"mdi:{spec.icon}",
                "device": device_block,
            }
            if spec.unit:
                payload["unit_of_measurement"] = spec.unit
            if spec.device_class:
                payload["device_class"] = spec.device_class
            if spec.state_class:
                payload["state_class"] = spec.state_class
            self._client.publish(topic, json.dumps(payload), qos=0, retain=True)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if getattr(reason_code, "is_failure", False):
            log.error("connect failed: %s", reason_code)
            return
        log.info("connected (rc=%s)", reason_code)
        self._connected = True
        client.publish(self._availability_topic, "online", qos=0, retain=True)

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        self._connected = False
        log.warning("disconnected — paho will auto-reconnect")
