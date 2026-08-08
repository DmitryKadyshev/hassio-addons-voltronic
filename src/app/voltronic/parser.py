"""QMOD / QPIRI / QPIGS / QPIWS parsing and field metadata.

Field names, order, and value semantics mirror the original C++ output shape
(main.cpp:243-279) so existing HA entity IDs keep resolving. `SENSORS` is the
single source of truth for both discovery config publish and state publish.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


# QMOD single-char → int code, matching cInverter::GetMode in inverter.cpp.
# Extends the NUT operational modes to cover the letters the inverter can answer.
MODE_MAP = {"P": 1, "S": 2, "L": 3, "B": 4, "F": 5, "H": 6}

# Human-readable (RU) names for the operational mode returned by QMOD.
MODE_NAMES = {
    1: "Включение",
    2: "Ожидание",
    3: "Сеть",
    4: "АКБ",
    5: "Ошибка",
    6: "Отключение",
}

# QPIRI output source priority (Program 01) → RU label.
OUT_SOURCE_PRIORITY_NAMES = {
    0: "От сети (первый)",
    1: "Солнечная (первая)",
    2: "СБУ (Solar-Battery-Utility)",
}

# QPIRI charger source priority (Program 16) → RU label.
CHARGER_SOURCE_PRIORITY_NAMES = {
    0: "От сети (первый)",
    1: "Солнечная (первая)",
    2: "Солнечная и сеть",
    3: "Только солнечная",
}

# QPIWS 64-bit warning mask → RU label. Index (1-based) is the warning number.
# Source: https://networkupstools.org/protocols/REDACTED.html  "Warnings".
WARNING_NAMES: dict[int, str] = {
    1: "АКБ отключена",
    2: "Нейтраль не подключена",
    3: "Ошибка заземления",
    4: "Неверный порядок фаз",
    5: "Неверный порядок фаз в байпасе",
    6: "Нестабильная частота сети в байпасе",
    7: "Перезаряд АКБ",
    8: "Низкий заряд АКБ",
    9: "Перегрузка",
    10: "Неисправность вентилятора",
    11: "Включён EPO",
    12: "Невозможно включить инвертор",
    13: "Перегрев",
    14: "Неисправность зарядного устройства",
    15: "Дистанционное автоматическое отключение",
    16: "Не работает предохранитель L1",
    17: "Не работает предохранитель L2",
    18: "Не работает предохранитель L3",
    19: "Аномалия положительного PFC в L1",
    20: "Аномалия отрицательного PFC в L1",
    21: "Аномалия положительного PFC в L2",
    22: "Аномалия отрицательного PFC в L2",
    23: "Аномалия положительного PFC в L3",
    24: "Аномалия отрицательного PFC в L3",
    25: "Неисправность шины CAN",
    26: "Неисправность цепи синхросигнала",
    27: "Неисправность цепи синхроимпульса",
    28: "Неисправность цепи ведущего сигнала",
    29: "Плохой контакт разъёма (папа) параллельного кабеля",
    30: "Плохой контакт разъёма (мама) параллельного кабеля",
    31: "Параллельный кабель подключён плохо",
    32: "Несогласованность АКБ в параллельной системе",
    33: "Несогласованность сети в параллельной системе",
    34: "Несогласованность байпаса в параллельной системе",
    35: "Разные модели в параллельной системе",
    36: "Разная мощность в параллельной системе",
    37: "Разные настройки автозапуска в параллельной системе",
    38: "Перезаряд банки АКБ",
    39: "Разные настройки защиты АКБ в параллельной системе",
    40: "Разные настройки контроля АКБ в параллельной системе",
    41: "Разные настройки запрета байпаса в параллельной системе",
    42: "Разные настройки конвертера в параллельной системе",
    43: "Разные верхние пороги частоты байпаса в параллельной системе",
    44: "Разные нижние пороги частоты байпаса в параллельной системе",
    45: "Разные верхние пороги напряжения байпаса в параллельной системе",
    46: "Разные нижние пороги напряжения байпаса в параллельной системе",
    47: "Разные верхние пороги частоты сети в параллельной системе",
    48: "Разные нижние пороги частоты сети в параллельной системе",
    49: "Разные верхние пороги напряжения сети в параллельной системе",
    50: "Разные нижние пороги напряжения сети в параллельной системе",
    51: "Блокировка байпаса после 3 перегрузок за 30 мин",
    52: "Дисбаланс входного тока (3 фазы)",
    53: "Дисбаланс входного тока от АКБ (3 фазы)",
    54: "Дисбаланс тока инвертора",
    55: "Предупреждение отключения программируемых розеток",
    56: "Требуется замена АКБ",
    57: "Аномалия входного угла фазы",
    58: "Открыта крышка обслуживания",
    62: "Ошибка записи EEPROM",
}


@dataclass(frozen=True)
class SensorSpec:
    name: str                          # HA-side sensor slug (appended after devicename_)
    unit: str                          # unit_of_measurement (empty string = omit)
    icon: str                          # mdi:<icon>
    device_class: Optional[str] = None # HA device_class if the reading has one
    state_class: Optional[str] = None  # measurement / total / total_increasing
    friendly_name: str = ""            # localized display name; empty = fall back to slug


# 33 sensors — 32 originally registered + `Warnings` (previously orphaned).
# The `friendly_name` maps to HA's `name` (display) while `name` stays the stable
# slug that keeps existing entity_ids (`devicename_<sensor>`) intact.
SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("Inverter_mode",              "",  "solar-power", friendly_name="Режим работы инвертора"),
    SensorSpec("AC_grid_voltage",            "V", "power-plug",        "voltage",     "measurement", "Напряжение сети"),
    SensorSpec("AC_grid_frequency",          "Hz","current-ac",        "frequency",   "measurement", "Частота сети"),
    SensorSpec("AC_out_voltage",             "V", "power-plug",        "voltage",     "measurement", "Выходное напряжение"),
    SensorSpec("AC_out_frequency",           "Hz","current-ac",        "frequency",   "measurement", "Выходная частота"),
    SensorSpec("PV_in_voltage",              "V", "solar-panel-large", "voltage",     "measurement", "Напряжение солнечных панелей"),
    SensorSpec("PV_in_current",              "A", "solar-panel-large", "current",     "measurement", "Ток солнечных панелей"),
    SensorSpec("PV_in_watts",                "W", "solar-panel-large", "power",       "measurement", "Мощность солнечных панелей"),
    SensorSpec("PV_in_watthour",             "Wh","solar-panel-large", "energy",      "total_increasing", "Выработка солнечных панелей (кВт·ч)"),
    SensorSpec("SCC_voltage",                "V", "current-dc",        "voltage",     "measurement", "Напряжение контроллера заряда"),
    SensorSpec("Load_pct",                   "%", "brightness-percent",None,          "measurement", "Загрузка инвертора (%)"),
    SensorSpec("Load_watt",                  "W", "chart-bell-curve",  "power",       "measurement", "Активная мощность нагрузки"),
    SensorSpec("Load_watthour",              "Wh","chart-bell-curve",  "energy",      "total_increasing", "Энергия нагрузки (кВт·ч)"),
    SensorSpec("Load_va",                    "VA","chart-bell-curve",  "apparent_power","measurement", "Полная мощность нагрузки"),
    SensorSpec("Bus_voltage",                "V", "details",           "voltage",     "measurement", "Напряжение внутренней шины"),
    SensorSpec("Heatsink_temperature",       "",  "details",           "temperature", "measurement", "Температура радиатора"),
    SensorSpec("Battery_capacity",           "%", "battery-outline",   "battery",     "measurement", "Заряд АКБ"),
    SensorSpec("Battery_voltage",            "V", "battery-outline",   "voltage",     "measurement", "Напряжение АКБ"),
    SensorSpec("Battery_charge_current",     "A", "current-dc",        "current",     "measurement", "Ток заряда АКБ"),
    SensorSpec("Battery_discharge_current",  "A", "current-dc",        "current",     "measurement", "Ток разряда АКБ"),
    SensorSpec("Load_status_on",             "",  "power", friendly_name="Статус нагрузки"),
    SensorSpec("SCC_charge_on",              "",  "power", friendly_name="Заряд от MPPT"),
    SensorSpec("AC_charge_on",               "",  "power", friendly_name="Заряд от сети"),
    SensorSpec("Battery_recharge_voltage",   "V", "current-dc",        "voltage", friendly_name="Порог возврата к сети (Программа 12)"),
    SensorSpec("Battery_under_voltage",      "V", "current-dc",        "voltage", friendly_name="Порог отключения АКБ (Программа 29)"),
    SensorSpec("Battery_bulk_voltage",       "V", "current-dc",        "voltage", friendly_name="Напряжение осн. заряда (Программа 26)"),
    SensorSpec("Battery_float_voltage",      "V", "current-dc",        "voltage", friendly_name="Напряжение подзарядки (Программа 27)"),
    SensorSpec("Max_grid_charge_current",    "A", "current-ac",        "current", friendly_name="Макс. ток заряда от сети (Программа 11)"),
    SensorSpec("Max_charge_current",         "A", "current-ac",        "current", friendly_name="Макс. общий ток заряда (Программа 02)"),
    SensorSpec("Out_source_priority",        "",  "grid", friendly_name="Приоритет источника питания (Программа 01)"),
    SensorSpec("Charger_source_priority",    "",  "solar-power", friendly_name="Приоритет источника заряда (Программа 16)"),
    SensorSpec("Battery_redischarge_voltage","V", "battery-negative",  "voltage", friendly_name="Порог возврата к АКБ (Программа 13)"),
    SensorSpec("Warnings",                   "",  "alert", friendly_name="Статус ошибок и предупреждений"),
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
    """Return the raw QPIWS payload (a 64-char 0/1 warning mask string)."""
    return payload.decode("ascii", errors="replace").strip()


def decode_warnings(raw: str) -> str:
    """Turn the QPIWS bit-mask string into a comma-separated RU warning list.

    The first character of the mask is warning #1, the 64th is #64. Only bits
    set to '1' are reported. Returns "Нет" when no warnings are active.
    """
    labels = [
        WARNING_NAMES[idx]
        for idx, bit in enumerate(raw, start=1)
        if bit == "1" and idx in WARNING_NAMES
    ]
    if not labels:
        return "Нет"
    return ", ".join(labels)


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

    def on_off(bit: str) -> str:
        return "Да" if bit == "1" else "Нет"

    return {
        "Inverter_mode":                MODE_NAMES.get(mode, str(mode)),
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
        "Load_status_on":               on_off(pick(status, 3)),
        "SCC_charge_on":                on_off(pick(status, 6)),
        "AC_charge_on":                 on_off(pick(status, 7)),
        "Battery_recharge_voltage":     f"{qpiri['batt_recharge_voltage']:.1f}",
        "Battery_under_voltage":        f"{qpiri['batt_under_voltage']:.1f}",
        "Battery_bulk_voltage":         f"{qpiri['batt_bulk_voltage']:.1f}",
        "Battery_float_voltage":        f"{qpiri['batt_float_voltage']:.1f}",
        "Max_grid_charge_current":      str(qpiri["max_grid_charge_current"]),
        "Max_charge_current":           str(qpiri["max_charge_current"]),
        "Out_source_priority":          OUT_SOURCE_PRIORITY_NAMES.get(
            qpiri["out_source_priority"], str(qpiri["out_source_priority"])
        ),
        "Charger_source_priority":      CHARGER_SOURCE_PRIORITY_NAMES.get(
            qpiri["charger_source_priority"], str(qpiri["charger_source_priority"])
        ),
        "Battery_redischarge_voltage":  f"{qpiri['batt_redischarge_voltage']:.1f}",
        "Warnings":                     decode_warnings(warnings),
    }
