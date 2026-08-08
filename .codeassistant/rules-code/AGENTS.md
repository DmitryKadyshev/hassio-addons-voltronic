# Project Coding Rules (Non-Obvious Only)

- Do NOT touch the CRC implementation in [`crc.py`](../../../src/app/REDACTED/crc.py) — it is a verbatim port of the old C++ `cal_crc_half` with reserved-byte substitution. Standardizing it to normal CRC-16 breaks framing with the inverter.
- Never rename or reorder keys in `SENSORS` ([`parser.py`](../../../src/app/REDACTED/parser.py:28)) or the dict from `build_state()`. They map 1:1 to existing HA entity IDs (`devicename_<sensor>`) and are a frozen compatibility contract.
- Add any new config option to BOTH `config.yaml` `schema`/`options` and the `Config` dataclass in [`config.py`](../../../src/app/REDACTED/config.py). `Config.load()` does a hard `json.loads` + direct key access — a missing/wrong-typed key crashes at startup.
- Publish payloads from `build_state()` are always strings (str), matching what MQTT/HA expect; do not switch to numeric types.
- Runtime is a single blocking loop in `__main__.py`. Do not introduce threads/async for inverter I/O — the fd is opened once and shared sequentially.
- Dependencies are installed via Alpine `apk add` in the `Dockerfile`, not pip. There is no requirements.txt or package manifest.