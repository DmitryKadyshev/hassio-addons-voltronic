import json

import pytest

from voltronic.config import Config, ConfigError


def valid_options():
    return {
        "device": "/dev/hidraw0", "run_interval": 5,
        "amperage_factor": 1.0, "watt_factor": 1.0,
        "qpiri": 97, "qpiws": 36, "qmod": 5, "qpigs": 110,
        "mqtt_server": "mosquitto", "mqtt_port": 1883,
        "mqtt_topic": "homeassistant", "devicename": "voltronic",
        "mqtt_username": "", "mqtt_password": "",
    }


def write_options(tmp_path, data):
    path = tmp_path / "options.json"
    path.write_text(json.dumps(data))
    return path


def test_load_valid_config(tmp_path):
    cfg = Config.load(write_options(tmp_path, valid_options()))
    assert cfg.device == "/dev/hidraw0"
    assert cfg.mqtt_port == 1883


@pytest.mark.parametrize("key", ["mqtt_server", "mqtt_topic", "devicename"])
def test_rejects_empty_required_strings(tmp_path, key):
    data = valid_options()
    data[key] = ""
    with pytest.raises(ConfigError):
        Config.load(write_options(tmp_path, data))


@pytest.mark.parametrize("key", ["run_interval", "qpiri", "qpiws", "qmod", "qpigs"])
def test_rejects_non_positive_intervals(tmp_path, key):
    data = valid_options()
    data[key] = 0
    with pytest.raises(ConfigError):
        Config.load(write_options(tmp_path, data))


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_rejects_invalid_mqtt_port(tmp_path, port):
    data = valid_options()
    data["mqtt_port"] = port
    with pytest.raises(ConfigError):
        Config.load(write_options(tmp_path, data))


def test_rejects_partial_mqtt_credentials(tmp_path):
    data = valid_options()
    data["mqtt_username"] = "user"
    with pytest.raises(ConfigError):
        Config.load(write_options(tmp_path, data))


def test_rejects_unsafe_device_path(tmp_path):
    data = valid_options()
    data["device"] = "/dev/sda"
    with pytest.raises(ConfigError):
        Config.load(write_options(tmp_path, data))
