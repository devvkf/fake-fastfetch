"""Configuration loading, profile resolution and value merging.

Layout on disk::

    config.json                 base configuration (live detection + display)
    profiles/<name>.json        overlays on top of config.json

A profile is merged over the base config with :func:`deep_merge`, so a profile
only needs to contain the values it wants to change.  Any ``system`` value that
is ``null`` (or omitted) is filled in from the live machine.
"""

from __future__ import annotations

import copy
import difflib
import json
import os
from pathlib import Path

from . import logos

# Repository root: sysfetch/config.py -> sysfetch/ -> repo root.
DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent

PROFILE_ENV = "SYSFETCH_PROFILE"
CONFIG_DIR_ENV = "SYSFETCH_CONFIG_DIR"


class ConfigError(Exception):
    """Raised for unreadable, invalid or inconsistent configuration."""


# Every value the renderer knows how to display.  "Direct" keys override a
# whole field; the detailed keys let a user change one component of it.
SPEC_KEYS: tuple[str, ...] = (
    "user",
    "hostname",
    # OS
    "os",
    "osName",
    "osVersion",
    "osCodename",
    "osArch",
    # Host / machine
    "host",
    "hostVendor",
    "hostName",
    "hostVersion",
    "hostSerial",
    # Kernel
    "kernel",
    "kernelName",
    "kernelVersion",
    "kernelArch",
    # Uptime
    "uptime",
    "uptimeSeconds",
    # Packages
    "packages",
    "packagesAll",
    "packagesScoop",
    "packagesChoco",
    "packagesScoopGlobal",
    # Shell / terminal
    "shell",
    "shellName",
    "shellVersion",
    "shellPath",
    "terminal",
    # CPU
    "cpu",
    "cpuName",
    "cpuVendor",
    "cpuCores",
    "cpuThreads",
    "cpuFrequencyMhz",
    "cpuMarch",
    # GPU
    "gpu",
    # Memory / swap
    "memory",
    "memoryTotal",
    "memoryUsed",
    "swap",
    "swapTotal",
    "swapUsed",
    # Storage
    "disks",
    # Network
    "localIp",
    "macAddress",
    # Battery / displays
    "battery",
    "displays",
    # Desktop
    "locale",
    "theme",
    "wmTheme",
    "font",
    "cursor",
    "icons",
    # Free-form rows: [{"label": "...", "value": "..."}]
    "custom",
)

DEFAULT_FIELDS: tuple[str, ...] = (
    "title",
    "separator",
    "os",
    "host",
    "kernel",
    "uptime",
    "packages",
    "shell",
    "terminal",
    "cpu",
    "gpu",
    "memory",
    "swap",
    "disk",
    "localIp",
    "battery",
    "display",
    "locale",
    "theme",
    "wmTheme",
    "font",
    "cursor",
    "icons",
    "custom",
)

# Fields are display rows; these are the spec keys each row reads.  The first
# entry is the direct override key (when present, the rest are not needed).
FIELD_KEYS: dict[str, tuple[str, ...]] = {
    "title": ("user", "hostname"),
    "os": ("os", "osName", "osVersion", "osCodename", "osArch"),
    "host": ("host", "hostVendor", "hostName", "hostVersion", "hostSerial"),
    "kernel": ("kernel", "kernelName", "kernelVersion", "kernelArch"),
    "uptime": ("uptime", "uptimeSeconds"),
    "packages": (
        "packages",
        "packagesAll",
        "packagesScoop",
        "packagesChoco",
        "packagesScoopGlobal",
    ),
    "shell": ("shell", "shellName", "shellVersion", "shellPath"),
    "terminal": ("terminal",),
    "cpu": (
        "cpu",
        "cpuName",
        "cpuVendor",
        "cpuCores",
        "cpuThreads",
        "cpuFrequencyMhz",
        "cpuMarch",
    ),
    "gpu": ("gpu",),
    "memory": ("memory", "memoryTotal", "memoryUsed"),
    "swap": ("swap", "swapTotal", "swapUsed"),
    "disk": ("disks",),
    "localIp": ("localIp", "macAddress"),
    "battery": ("battery",),
    "display": ("displays",),
    "locale": ("locale",),
    "theme": ("theme",),
    "wmTheme": ("wmTheme",),
    "font": ("font",),
    "cursor": ("cursor",),
    "icons": ("icons",),
    "custom": ("custom",),
}

# Rows that are not backed by a single system key ("title" is in FIELD_KEYS
# because it consumes user + hostname).
PSEUDO_FIELDS = ("separator",)
ALL_FIELDS: tuple[str, ...] = tuple(FIELD_KEYS) + PSEUDO_FIELDS

DEFAULT_LABELS: dict[str, str] = {
    "os": "OS",
    "host": "Host",
    "kernel": "Kernel",
    "uptime": "Uptime",
    "packages": "Packages",
    "shell": "Shell",
    "terminal": "Terminal",
    "cpu": "CPU",
    "gpu": "GPU",
    "memory": "Memory",
    "swap": "Swap",
    "disk": "Disk",
    "localIp": "Local IP",
    "battery": "Battery",
    "display": "Display",
    "locale": "Locale",
    "theme": "Theme",
    "wmTheme": "WM Theme",
    "font": "Font",
    "cursor": "Cursor",
    "icons": "Icons",
}

DEFAULT_DISPLAY: dict = {
    "color": True,
    "showLogo": True,
    "logo": "auto",
    "logoArt": None,
    "logoColors": None,
    "logoGap": 2,
    "titleColor": "bright_cyan",
    "keyColor": "bright_cyan",
    "valueColor": None,
    "separatorColor": "bright_black",
    "fields": None,
    "hide": [],
    "labels": {},
    "alignValues": True,
}


def config_dir(explicit: str | os.PathLike | None = None) -> Path:
    """Resolve the directory that holds config.json and profiles/."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    from_env = os.environ.get(CONFIG_DIR_ENV)
    if from_env:
        return Path(from_env).expanduser().resolve()
    return DEFAULT_CONFIG_DIR


def read_json(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        reason = exc.strerror or str(exc)
        raise ConfigError(f"cannot read {path}: {reason}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a JSON object")
    return data


def deep_merge(base: dict, overlay: dict) -> dict:
    """Recursively merge ``overlay`` onto ``base`` without mutating either."""
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def profile_file(root: Path, name: str) -> Path:
    """Map a profile name (or path) to a JSON file."""
    text = str(name).strip()
    candidate = Path(text).expanduser()
    if candidate.suffix.lower() == ".json":
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate
    return root / "profiles" / f"{text}.json"


def available_profiles(root: Path) -> list[dict]:
    """Describe every profile in ``root/profiles`` (invalid files included)."""
    directory = root / "profiles"
    if not directory.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        entry = {"name": path.stem, "description": "", "path": path, "error": None}
        try:
            data = read_json(path)
        except ConfigError as exc:
            entry["error"] = str(exc)
        else:
            name = data.get("name")
            description = data.get("description")
            if isinstance(name, str) and name.strip():
                entry["name"] = name.strip()
            if isinstance(description, str):
                entry["description"] = description.strip()
        out.append(entry)
    return out


def _suggest(value: str, choices) -> str:
    matches = difflib.get_close_matches(value, list(choices), n=1)
    return f" (did you mean {matches[0]!r}?)" if matches else ""


def validate(config: dict) -> None:
    """Check the parts of the config the renderer depends on."""
    display = config.get("display", {})
    if not isinstance(display, dict):
        raise ConfigError("'display' must be a JSON object")

    system = config.get("system", {})
    if not isinstance(system, dict):
        raise ConfigError("'system' must be a JSON object")
    unknown = sorted(set(system) - set(SPEC_KEYS))
    if unknown:
        names = ", ".join(repr(name) for name in unknown)
        raise ConfigError(f"unknown system key(s): {names}{_suggest(unknown[0], SPEC_KEYS)}")

    fields = display.get("fields")
    if fields is not None:
        if not isinstance(fields, list) or not all(isinstance(f, str) for f in fields):
            raise ConfigError("'display.fields' must be a list of field names or null")
        unknown = [f for f in fields if f not in ALL_FIELDS]
        if unknown:
            raise ConfigError(
                f"unknown field(s) in 'display.fields': {', '.join(map(repr, unknown))}"
                f"{_suggest(unknown[0], ALL_FIELDS)}"
            )

    hidden = display.get("hide", [])
    if hidden is not None:
        if not isinstance(hidden, list) or not all(isinstance(f, str) for f in hidden):
            raise ConfigError("'display.hide' must be a list of field names")
        unknown = [f for f in hidden if f not in ALL_FIELDS]
        if unknown:
            raise ConfigError(f"unknown field(s) in 'display.hide': {', '.join(map(repr, unknown))}")

    labels = display.get("labels", {})
    if labels is not None and not isinstance(labels, dict):
        raise ConfigError("'display.labels' must be a JSON object")

    logo = display.get("logo")
    if logo is not None and not isinstance(logo, (str, bool)):
        raise ConfigError("'display.logo' must be a string, false or null")
    if isinstance(logo, str) and logo.strip().lower() not in ("", "auto", "default"):
        if logos.resolve(logo) is None and not display.get("logoArt"):
            builtins = ", ".join(sorted(logos.LOGOS))
            raise ConfigError(
                f"unknown logo {logo!r}{_suggest(logo, logos.LOGOS)} "
                f"(built-ins: {builtins}, or set 'display.logoArt')"
            )

    logo_colors = display.get("logoColors")
    if logo_colors is not None and not isinstance(logo_colors, list):
        raise ConfigError("'display.logoColors' must be a list of colours")

    logo_art = display.get("logoArt")
    if logo_art is not None and not isinstance(logo_art, str):
        raise ConfigError("'display.logoArt' must be a string of art lines")

    custom = system.get("custom")
    if custom is not None:
        if not isinstance(custom, list):
            raise ConfigError("'system.custom' must be a list")
        for index, item in enumerate(custom):
            if isinstance(item, dict):
                if "label" not in item or "value" not in item:
                    raise ConfigError(f"'system.custom[{index}]' needs 'label' and 'value'")
            elif not (isinstance(item, list) and len(item) == 2):
                raise ConfigError(
                    f"'system.custom[{index}]' must be an object or a [label, value] pair"
                )


def load_config(
    directory: str | os.PathLike | None = None,
    config_path: str | os.PathLike | None = None,
    profile: str | None = None,
) -> tuple[dict, dict]:
    """Load the base config, overlay a profile and return ``(config, meta)``.

    Profile precedence: explicit argument, ``SYSFETCH_PROFILE``, then the base
    config's ``defaultProfile``.
    """
    root = config_dir(directory)
    if config_path:
        base_path = Path(config_path).expanduser()
        if not base_path.is_absolute():
            base_path = Path.cwd() / base_path
    else:
        base_path = root / "config.json"

    if not base_path.exists():
        raise ConfigError(f"config not found: {base_path}")
    base = read_json(base_path)

    chosen = profile or os.environ.get(PROFILE_ENV) or base.get("defaultProfile")
    chosen = str(chosen).strip() if chosen else None
    merged = copy.deepcopy(base)
    profile_path: Path | None = None
    if chosen and chosen.lower() not in ("", "none"):
        profiles = available_profiles(root)
        profile_path = profile_file(root, chosen)
        if not profile_path.exists():
            # Also accept the "name" field written inside a profile file.
            match = next(
                (entry for entry in profiles if entry["name"].lower() == chosen.lower()),
                None,
            )
            if match:
                profile_path = match["path"]
        if not profile_path.exists():
            names = ", ".join(entry["name"] for entry in profiles) or "none"
            raise ConfigError(
                f"profile {chosen!r} not found at {profile_path} (available: {names})"
            )
        merged = deep_merge(merged, read_json(profile_path))

    # Fill display defaults so callers never have to test for missing keys.
    display = dict(DEFAULT_DISPLAY)
    display.update(merged.get("display") or {})
    merged["display"] = display
    merged.setdefault("system", {})

    validate(merged)
    meta = {
        "config_dir": root,
        "config_path": base_path,
        "profile": chosen if profile_path else None,
        "profile_path": profile_path,
    }
    return merged, meta


def selected_fields(config: dict) -> list[str]:
    display = config.get("display") or {}
    fields = display.get("fields")
    if fields is None:
        fields = list(DEFAULT_FIELDS)
    hidden = set(display.get("hide") or [])
    return [field for field in fields if field not in hidden]


def explicit_keys(config: dict) -> set[str]:
    """System keys the user set to something other than null."""
    system = config.get("system") or {}
    return {key for key, value in system.items() if value is not None}


def needed_keys(config: dict) -> set[str]:
    """Spec keys that must be collected live for the selected fields."""
    explicit = explicit_keys(config)
    system = config.get("system") or {}
    needed: set[str] = set()
    for field in selected_fields(config):
        keys = FIELD_KEYS.get(field)
        if not keys:
            continue
        if field == "title":
            # user and hostname are independent; either may still need live data.
            needed.update(key for key in keys if system.get(key) is None)
            continue
        direct = keys[0]
        # A direct override makes the detail keys irrelevant.
        if direct in explicit and system.get(direct) is not None:
            continue
        for key in keys:
            if system.get(key) is None:
                needed.add(key)
    return needed


def resolve_spec(live: dict, config: dict) -> tuple[dict, set[str]]:
    """Merge live values with user overrides.

    Returns the resolved spec and the set of keys the user explicitly set.
    """
    system = config.get("system") or {}
    resolved = {key: live.get(key) for key in SPEC_KEYS}
    explicit: set[str] = set()
    for key, value in system.items():
        if key not in resolved:
            continue
        if value is not None:
            resolved[key] = value
            explicit.add(key)
    return resolved, explicit
