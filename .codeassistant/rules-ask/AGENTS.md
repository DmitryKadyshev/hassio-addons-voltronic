# Project Documentation Rules (Non-Obvious Only)

- This repo is a Home Assistant add-on repository: `repository.yaml` + `build.yaml` + `config.yaml` at the root, not a standard Python project. There is no `pyproject.toml`, `setup.py`, or `requirements.txt`.
- The actual Python package lives under `src/app/voltronic/`, which is a non-standard layout: it is copied wholesale to `/opt/voltronic/` in the `Dockerfile` and run via `PYTHONPATH=/opt/voltronic python3 -m voltronic`.
- The add-on manifest (`config.yaml`) `options`/`schema` is the ONLY source of user-facing configuration; the `Config` dataclass in `config.py` mirrors it by hand and must stay in sync.
- `src/rootfs/` is an s6-overlay root filesystem, not application code. The `run`/`finish` scripts there control the daemon lifecycle and must not be confused with the Python entry point.
- Sensor names and the original C++-derived field semantics (see docstrings in `parser.py`) are canonical; docs/comments referencing `inverter.cpp`/`main.cpp` refer to a legacy codebase not present in this repo.