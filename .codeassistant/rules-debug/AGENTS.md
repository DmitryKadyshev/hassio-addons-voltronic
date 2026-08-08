# Project Debug Rules (Non-Obvious Only)

- There is **no** local repro environment: no unit tests, no fake inverter, no mock device. The only way to verify behavior is to build the add-on and run against real hardware (`/dev/hidraw*`).
- To point `Config.load()` at a non-default options file, set the `VOLTRONIC_OPTIONS` env var. If any key from `config.yaml` `schema` is missing or wrong-typed, the add-on crashes with a Python exception at startup (no graceful error).
- `query()` returns `None` on timeout, CRC mismatch, or bad framing — it logs a warning and continues. A `None` return from `_poll_once` skips the whole publish cycle silently; the loop relies on this to keep going, so don't turn it into a hard failure.
- Read timeouts appear as warnings ("%s read timeout after N/N bytes") with no error/exception — this is expected noise on flaky USB/hidraw links, not necessarily a bug.
- The single long-lived MQTT connection uses paho's `loop_start()` with auto-reconnect. If the broker drops, `is_connected` goes False and state publishes are skipped with "skipping publish: MQTT not connected yet".
- Logs go to the s6 service stdout (visible via `ha addons logs`), not a file. Log level is hardcoded to INFO in `__main__.py`.