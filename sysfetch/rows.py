"""Turn a resolved spec plus display config into renderable rows."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import fmt
from .config import DEFAULT_LABELS, FIELD_KEYS, selected_fields


@dataclass
class Row:
    """One output row; ``label`` is ``None`` for the separator."""

    label: str | None
    lines: list[str] = field(default_factory=list)
    separator: bool = False
    title: bool = False


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        # ``false`` is the documented way to suppress a row; ``true`` shows text.
        return "true" if value else None
    text = str(value).strip()
    return text or None


def _lines(value) -> list[str] | None:
    """Normalise a value into display lines (lists become multiple lines)."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            text = _text(item)
            if text:
                out.extend(text.splitlines())
        return out or None
    text = _text(value)
    return text.splitlines() if text else None


def _number(value) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return None
    return None


def _size(value) -> str | None:
    """Format a byte count; strings are passed through untouched."""
    if value is None:
        return None
    number = _number(value)
    if number is None:
        return _text(value)
    return fmt.size(number)


def _compose_os(spec: dict, explicit: set[str]) -> str | None:
    parts = []
    if "osName" in explicit:
        parts.append(_text(spec.get("osName")))
    if "osVersion" in explicit:
        parts.append(_text(spec.get("osVersion")))
    if "osCodename" in explicit:
        codename = _text(spec.get("osCodename"))
        if codename:
            parts.append(f"({codename})")
    if "osArch" in explicit:
        parts.append(_text(spec.get("osArch")))
    return " ".join(part for part in parts if part) or None


def _compose_host(spec: dict, explicit: set[str]) -> str | None:
    parts = []
    if "hostVendor" in explicit:
        parts.append(_text(spec.get("hostVendor")))
    if "hostName" in explicit:
        parts.append(_text(spec.get("hostName")))
    if "hostVersion" in explicit:
        parts.append(_text(spec.get("hostVersion")))
    if "hostSerial" in explicit:
        serial = _text(spec.get("hostSerial"))
        if serial:
            parts.append(f"(S/N {serial})")
    return " ".join(part for part in parts if part) or None


def _compose_kernel(spec: dict, explicit: set[str]) -> str | None:
    parts = []
    if "kernelName" in explicit:
        parts.append(_text(spec.get("kernelName")))
    if "kernelVersion" in explicit:
        parts.append(_text(spec.get("kernelVersion")))
    if "kernelArch" in explicit:
        parts.append(_text(spec.get("kernelArch")))
    return " ".join(part for part in parts if part) or None


def _compose_cpu(spec: dict, explicit: set[str]) -> str | None:
    parts = []
    if "cpuName" in explicit:
        parts.append(_text(spec.get("cpuName")))
    if "cpuThreads" in explicit:
        threads = _number(spec.get("cpuThreads"))
        if threads:
            parts.append(f"({int(threads)})")
    if "cpuFrequencyMhz" in explicit:
        mhz = _number(spec.get("cpuFrequencyMhz"))
        if mhz:
            parts.append(f"@ {fmt.freq(mhz)}")
    if "cpuMarch" in explicit:
        march = _text(spec.get("cpuMarch"))
        if march:
            parts.append(march)
    return " ".join(part for part in parts if part) or None


def _compose_packages(spec: dict, explicit: set[str]) -> str | None:
    total = _number(spec.get("packagesAll")) if "packagesAll" in explicit else None
    scoop = _number(spec.get("packagesScoop")) if "packagesScoop" in explicit else None
    choco = _number(spec.get("packagesChoco")) if "packagesChoco" in explicit else None
    if total is None:
        total = (scoop or 0) + (choco or 0) or None
    parts = []
    if scoop:
        parts.append(f"scoop {int(scoop)}")
    if choco:
        parts.append(f"choco {int(choco)}")
    if total is None:
        return None
    return f"{int(total)} ({', '.join(parts)})" if parts else str(int(total))


def _compose_shell(spec: dict, explicit: set[str]) -> str | None:
    parts = []
    if "shellName" in explicit:
        parts.append(_text(spec.get("shellName")))
    if "shellVersion" in explicit:
        parts.append(_text(spec.get("shellVersion")))
    if not parts and "shellPath" in explicit:
        parts.append(_text(spec.get("shellPath")))
    return " ".join(part for part in parts if part) or None


def _compose_memory(spec: dict, explicit: set[str], prefix: str) -> str | None:
    total_key = f"{prefix}Total"
    used_key = f"{prefix}Used"
    total = spec.get(total_key) if total_key in explicit else None
    used = spec.get(used_key) if used_key in explicit else None
    if total is None and used is None:
        return None
    total_text = _size(total)
    used_text = _size(used)
    if used_text and total_text:
        total_number = _number(total)
        used_number = _number(used)
        if total_number and used_number is not None:
            percent = used_number / total_number * 100
            return f"{used_text} / {total_text} ({fmt.percent(percent)})"
        return f"{used_text} / {total_text}"
    return used_text or total_text


def _format_custom(value: str, spec: dict) -> str:
    """Expand ``{key}`` placeholders in custom row values."""

    class _Missing(dict):
        def __missing__(self, key):  # noqa: D105 - keeps unknown keys literal
            return "{" + key + "}"

    try:
        return value.format_map(_Missing(spec))
    except (ValueError, IndexError):
        return value


def _row_value(field_name: str, spec: dict, explicit: set[str]):
    """Resolve one display row, honouring direct and component overrides."""
    keys = FIELD_KEYS[field_name]
    direct = keys[0]
    if direct in explicit:
        return spec.get(direct)

    components = [key for key in keys[1:] if key in explicit]
    if not components:
        return spec.get(direct)

    if field_name == "os":
        return _compose_os(spec, explicit)
    if field_name == "host":
        return _compose_host(spec, explicit)
    if field_name == "kernel":
        return _compose_kernel(spec, explicit)
    if field_name == "uptime":
        seconds = _number(spec.get("uptimeSeconds"))
        return fmt.duration(seconds) if seconds else None
    if field_name == "cpu":
        return _compose_cpu(spec, explicit)
    if field_name == "packages":
        return _compose_packages(spec, explicit)
    if field_name == "shell":
        return _compose_shell(spec, explicit)
    if field_name == "memory":
        return _compose_memory(spec, explicit, "memory")
    if field_name == "swap":
        return _compose_memory(spec, explicit, "swap")
    return spec.get(direct)


def _title(spec: dict) -> str | None:
    user = _text(spec.get("user"))
    hostname = _text(spec.get("hostname"))
    if user and hostname:
        return f"{user}@{hostname}"
    return user or hostname


def _custom_items(value) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not isinstance(value, list):
        return out
    for item in value:
        if isinstance(item, dict):
            label = _text(item.get("label"))
            text = item.get("value")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            label = _text(item[0])
            text = item[1]
        else:
            continue
        if not label or text is None or text is False:
            continue
        lines = _lines(text)
        if lines:
            out.append((label, "\n".join(lines)))
    return out


def build_rows(config: dict, spec: dict, explicit: set[str]) -> list[Row]:
    display = config.get("display") or {}
    labels = {**DEFAULT_LABELS, **(display.get("labels") or {})}
    rows: list[Row] = []

    for field_name in selected_fields(config):
        if field_name == "title":
            value = _title(spec)
            if value:
                rows.append(Row(label=None, lines=[value], title=True))
            continue

        if field_name == "separator":
            rows.append(Row(label=None, separator=True))
            continue

        if field_name == "custom":
            for label, value in _custom_items((config.get("system") or {}).get("custom")):
                rows.append(Row(label=label, lines=_format_custom(value, spec).splitlines()))
            continue

        value = _row_value(field_name, spec, explicit)
        lines = _lines(value)
        if not lines:
            continue
        label = labels.get(field_name)
        rows.append(Row(label=label, lines=lines))

    return rows
