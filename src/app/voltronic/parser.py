"""QMOD / QPIRI / QPIGS / QPIWS parsing and field metadata.

Field names, order, and value semantics mirror the original C++ output shape
(main.cpp:243-279) so existing HA entity IDs keep resolving. `SENSORS` is the
single source of truth for both discovery config publish and state publish.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


# QMOD single-char → int code, matching cInverter::GetMode in inverter.cpp.
MODE_MAP = {"P": 1, "S": 2, "L": 3, "B": 4, "F": 5, "H": 6}


@dataclass(frozen=True)
class SensorSpec:
    name: str                          # HA-side sensor slug (appended after devicename_)
    unit: str                          # unit_of_measurement (empty string = omit)
    icon: str                          # mdi:<icon>
    device_class: Optional[str] = None # HA device_class if the reading has one
    state_class: Optional[str] = None  # measurement / total / total_increasing


# 33 sensors — 32 originally registered + `Warnings` (previously orphaned).
SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("Inverter_mode",              "",  "solar-power"),
    SensorSpec("AC_grid_voltage",            "V", "power-plug",        "voltage",     "measurement"),
    SensorSpec("AC_grid_frequency",          "Hz","current-ac",        "frequency",   "measurement"),
    SensorSpec("AC_out_voltage",             "V", "power-plug",        "voltage",     "measurement"),
    SensorSpec("AC_out_frequency",           "Hz","current-ac",        "frequency",   "measurement"),
    SensorSpec("PV_in_voltage",              "V", "solar-panel-large", "voltage",     "measurement"),
    SensorSpec("PV_in_current",              "A", "solar-panel-large", "current",     "measurement"),
    SensorSpec("PV_in_watts",                "W", "solar-panel-large", "power",       "measurement"),
    SensorSpec("PV_in_watthour",             "Wh","solar-panel-large", "energy",      "total_increasing"),
    SensorSpec("SCC_voltage",                "V", "current-dc",        "voltage",     "measurement"),
    SensorSpec("Load_pct",                   "%", "brightness-percent",None,          "measurement"),
    SensorSpec("Load_watt",                  "W", "chart-bell-curve",  "power",       "measurement"),
    SensorSpec("Load_watthour",              "Wh","chart-bell-curve",  "energy",      "total_increasing"),
    SensorSpec("Load_va",                    "VA","chart-bell-curve",  "apparent_power","measurement"),
    SensorSpec("Bus_voltage",                "V", "details",           "voltage",     "measurement"),
    SensorSpec("Heatsink_temperature",       "",  "details",           "temperature", "measurement"),
    SensorSpec("Battery_capacity",           "%", "battery-outline",   "battery",     "measurement"),
    SensorSpec("Battery_voltage",            "V", "battery-outline",   "voltage",     "measurement"),
    SensorSpec("Battery_charge_current",     "A", "current-dc",        "current",     "measurement"),
    SensorSpec("Battery_discharge_current",  "A", "current-dc",        "current",     "measurement"),
    SensorSpec("Load_status_on",             "",  "power"),
    SensorSpec("SCC_charge_on",              "",  "power"),
    SensorSpec("AC_charge_on",               "",  "power"),
    SensorSpec("Battery_recharge_voltage",   "V", "current-dc",        "voltage"),
    SensorSpec("Battery_under_voltage",      "V", "current-dc",        "voltage"),
    SensorSpec("Battery_bulk_voltage",       "V", "current-dc",        "voltage"),
    SensorSpec("Battery_float_voltage",      "V", "current-dc",        "voltage"),
    SensorSpec("Max_grid_charge_current",    "A", "current-ac",        "current"),
    SensorSpec("Max_charge_current",         "A", "current-ac",        "current"),
    SensorSpec("Out_source_priority",        "",  "grid"),
    SensorSpec("Charger_source_priority",    "",  "solar-power"),
    SensorSpec("Battery_redischarge_voltage","V", "battery-negative",  "voltage"),
    SensorSpec("Warnings",                   "",  "alert"),
)


def parse_qmod(payload: bytes) -> int:
    """QMOD payload is a single ASCII mode character."""
    if not payload:
        return 0
    return MODE_MAP.get(payload[:1].decode("ascii", errors="replace"), 0)


def parse_qpigs(payload: bytes) -> Optional[dict]:
    """Return a dict of the 17 QPIGS raw fields, or None if the frame is malformed."""
    tokens = payload.decode("ascii", errors="replace").split()
    if len(tokens) < 17:
        return None
    try:
        return {
            "voltage_grid":          float(tokens[0]),
            "freq_grid":             float(tokens[1]),
            "voltage_out":           float(tokens[2]),
            "freq_out":              float(tokens[3]),
            "load_va":               int(tokens[4]),
            "load_watt":             int(tokens[5]),
            "load_percent":          int(tokens[6]),
            "voltage_bus":           int(tokens[7]),
            "voltage_batt":          float(tokens[8]),
            "batt_charge_current":   int(tokens[9]),
            "batt_capacity":         int(tokens[10]),
            "temp_heatsink":         int(tokens[11]),
            "pv_input_current":      float(tokens[12]),
            "pv_input_voltage":      float(tokens[13]),
            "scc_voltage":           float(tokens[14]),
            "batt_discharge_current":int(tokens[15]),
            "device_status":         tokens[16],
        }
    except (ValueError, IndexError):
        return None


def parse_qpiri(payload: bytes) -> Optional[dict]:
    """Return a dict of QPIRI rating fields. Token 18 is a literal '-' placeholder."""
    tokens = payload.decode("ascii", errors="replace").split()
    if len(tokens) < 23:
        return None
    try:
        return {
            "batt_recharge_voltage":     float(tokens[8]),
            "batt_under_voltage":        float(tokens[9]),
            "batt_bulk_voltage":         float(tokens[10]),
            "batt_float_voltage":        float(tokens[11]),
            "max_grid_charge_current":   int(tokens[13]),
            "max_charge_current":        int(tokens[14]),
            "out_source_priority":       int(tokens[16]),
            "charger_source_priority":   int(tokens[17]),
            "batt_redischarge_voltage":  float(tokens[22]),
        }
    except (ValueError, IndexError):
        return None


def parse_qpiws(payload: bytes) -> str:
    return payload.decode("ascii", errors="replace").strip()


def build_state(
    mode: int,
    qpigs: dict,
    qpiri: dict,
    warnings: str,
    *,
    amperage_factor: float,
    watt_factor: float,
    run_interval: int,
) -> dict[str, str]:
    """Assemble the 33 field values keyed by sensor name (str payloads for MQTT)."""
    pv_current = qpigs["pv_input_current"] * amperage_factor
    pv_watts = qpigs["scc_voltage"] * pv_current * watt_factor
    divisor = 3600.0 / run_interval if run_interval else 3600.0
    pv_wh = pv_watts / divisor
    load_wh = qpigs["load_watt"] / divisor
    status = qpigs["device_status"]

    def pick(s: str, i: int) -> str:
        return s[i] if len(s) > i else ""

    return {
        "Inverter_mode":                str(mode),
        "AC_grid_voltage":              f"{qpigs['voltage_grid']:.1f}",
        "AC_grid_frequency":            f"{qpigs['freq_grid']:.1f}",
        "AC_out_voltage":               f"{qpigs['voltage_out']:.1f}",
        "AC_out_frequency":             f"{qpigs['freq_out']:.1f}",
        "PV_in_voltage":                f"{qpigs['pv_input_voltage']:.1f}",
        "PV_in_current":                f"{pv_current:.1f}",
        "PV_in_watts":                  f"{pv_watts:.1f}",
        "PV_in_watthour":               f"{pv_wh:.4f}",
        "SCC_voltage":                  f"{qpigs['scc_voltage']:.4f}",
        "Load_pct":                     str(qpigs["load_percent"]),
        "Load_watt":                    str(qpigs["load_watt"]),
        "Load_watthour":                f"{load_wh:.4f}",
        "Load_va":                      str(qpigs["load_va"]),
        "Bus_voltage":                  str(qpigs["voltage_bus"]),
        "Heatsink_temperature":         str(qpigs["temp_heatsink"]),
        "Battery_capacity":             str(qpigs["batt_capacity"]),
        "Battery_voltage":              f"{qpigs['voltage_batt']:.2f}",
        "Battery_charge_current":       str(qpigs["batt_charge_current"]),
        "Battery_discharge_current":    str(qpigs["batt_discharge_current"]),
        "Load_status_on":               pick(status, 3),
        "SCC_charge_on":                pick(status, 6),
        "AC_charge_on":                 pick(status, 7),
        "Battery_recharge_voltage":     f"{qpiri['batt_recharge_voltage']:.1f}",
        "Battery_under_voltage":        f"{qpiri['batt_under_voltage']:.1f}",
        "Battery_bulk_voltage":         f"{qpiri['batt_bulk_voltage']:.1f}",
        "Battery_float_voltage":        f"{qpiri['batt_float_voltage']:.1f}",
        "Max_grid_charge_current":      str(qpiri["max_grid_charge_current"]),
        "Max_charge_current":           str(qpiri["max_charge_current"]),
        "Out_source_priority":          str(qpiri["out_source_priority"]),
        "Charger_source_priority":      str(qpiri["charger_source_priority"]),
        "Battery_redischarge_voltage":  f"{qpiri['batt_redischarge_voltage']:.1f}",
        "Warnings":                     warnings,
    }
