"""Live collectors that fill in values the config leaves as ``null``.

Each collector group computes one or more spec keys.  Groups are only run when
a selected field actually needs one of their keys, so a config that overrides
everything never touches the hardware.
"""

from __future__ import annotations

from typing import Callable

from . import fmt, winapi

# key -> collector group name
KEY_GROUPS: dict[str, str] = {
    "user": "identity",
    "hostname": "identity",
    "os": "os",
    "osName": "os",
    "osVersion": "os",
    "osCodename": "os",
    "osArch": "os",
    "host": "host",
    "hostVendor": "host",
    "hostName": "host",
    "hostVersion": "host",
    "hostSerial": "host",
    "kernel": "kernel",
    "kernelName": "kernel",
    "kernelVersion": "kernel",
    "kernelArch": "kernel",
    "uptime": "uptime",
    "uptimeSeconds": "uptime",
    "packages": "packages",
    "packagesAll": "packages",
    "packagesScoop": "packages",
    "packagesChoco": "packages",
    "packagesScoopGlobal": "packages",
    "shell": "shell",
    "shellName": "shell",
    "shellVersion": "shell",
    "shellPath": "shell",
    "terminal": "terminal",
    "cpu": "cpu",
    "cpuName": "cpu",
    "cpuVendor": "cpu",
    "cpuCores": "cpu",
    "cpuThreads": "cpu",
    "cpuFrequencyMhz": "cpu",
    "cpuMarch": "cpu",
    "gpu": "gpu",
    "memory": "memory",
    "memoryTotal": "memory",
    "memoryUsed": "memory",
    "swap": "swap",
    "swapTotal": "swap",
    "swapUsed": "swap",
    "disks": "disks",
    "localIp": "network",
    "macAddress": "network",
    "battery": "battery",
    "displays": "displays",
    "locale": "locale",
    "theme": "theme",
    "wmTheme": "wmTheme",
    "font": "font",
    "cursor": "cursor",
    "icons": "icons",
}


def _safe(collector: Callable[[], dict]) -> dict:
    """Run a collector, returning an empty result instead of raising."""
    try:
        return collector() or {}
    except Exception:  # noqa: BLE001 - a fetch must never crash on one probe
        return {}


# --------------------------------------------------------------------------- #
# Identity / OS / host / kernel
# --------------------------------------------------------------------------- #
def collect_identity() -> dict:
    return {
        "user": winapi.user_name(),
        "hostname": winapi.host_name(),
    }


def collect_os() -> dict:
    info = winapi.os_info()
    kernel = winapi.kernel_info()
    return {
        "os": info.get("prettyName"),
        "osName": info.get("id") or info.get("name"),
        "osVersion": info.get("variant") or info.get("version"),
        "osCodename": info.get("codename") or None,
        "osArch": kernel.get("architecture"),
    }


def collect_host() -> dict:
    info = winapi.host_info() or {}
    vendor = (info.get("vendor") or "").strip()
    name = (info.get("name") or "").strip()
    version = (info.get("version") or "").strip()
    serial = (info.get("serial") or "").strip()
    composed = " ".join(part for part in (vendor, name, version) if part)
    return {
        "host": composed or None,
        "hostVendor": vendor or None,
        "hostName": name or None,
        "hostVersion": version or None,
        "hostSerial": serial or None,
    }


def collect_kernel() -> dict:
    info = winapi.kernel_info()
    name = info.get("name") or ""
    release = info.get("release") or ""
    arch = info.get("architecture") or ""
    composed = " ".join(part for part in (name, release, arch) if part)
    return {
        "kernel": composed or None,
        "kernelName": name or None,
        "kernelVersion": release or None,
        "kernelArch": arch or None,
    }


def collect_uptime() -> dict:
    seconds = max(0, winapi.uptime_ms() // 1000)
    return {
        "uptime": fmt.duration(seconds) if seconds else None,
        "uptimeSeconds": seconds,
    }


def collect_packages() -> dict:
    info = winapi.packages()
    total = int(info.get("all") or 0)
    scoop_user = int(info.get("scoopUser") or 0)
    scoop_global = int(info.get("scoopGlobal") or 0)
    choco = int(info.get("choco") or 0)

    parts = []
    if scoop_user or scoop_global:
        scoop = scoop_user + scoop_global
        parts.append(f"scoop {scoop}")
    if choco:
        parts.append(f"choco {choco}")
    composed = str(total)
    if parts:
        composed += f" ({', '.join(parts)})"
    return {
        "packages": composed if total else None,
        "packagesAll": total,
        "packagesScoop": scoop_user + scoop_global or None,
        "packagesScoopGlobal": scoop_global or None,
        "packagesChoco": choco or None,
    }


# --------------------------------------------------------------------------- #
# Shell / terminal
# --------------------------------------------------------------------------- #
def collect_shell() -> dict:
    info = winapi.shell_info() or {}
    name = info.get("prettyName") or ""
    version = info.get("version") or ""
    composed = " ".join(part for part in (name, version) if part)
    return {
        "shell": composed or None,
        "shellName": name or None,
        "shellVersion": version or None,
        "shellPath": info.get("exePath") or info.get("exe") or None,
    }


def collect_terminal() -> dict:
    info = winapi.terminal_info() or {}
    return {"terminal": info.get("prettyName") or None}


# --------------------------------------------------------------------------- #
# CPU / GPU
# --------------------------------------------------------------------------- #
def collect_cpu() -> dict:
    info = winapi.cpu_info() or {}
    name = (info.get("cpu") or "").strip()
    vendor = (info.get("vendor") or "").strip()
    cores = (info.get("cores") or {})
    physical = int(cores.get("physical") or 0)
    logical = int(cores.get("logical") or 0)
    frequency = (info.get("frequency") or {})
    base = int(frequency.get("base") or 0)
    maximum = int(frequency.get("max") or 0)
    march = info.get("march")

    parts = [name]
    if logical:
        parts.append(f"({logical})")
    speed = maximum or base
    if speed:
        parts.append(f"@ {fmt.freq(speed)}")
    composed = " ".join(part for part in parts if part)
    return {
        "cpu": composed or None,
        "cpuName": name or None,
        "cpuVendor": vendor or None,
        "cpuCores": physical or None,
        "cpuThreads": logical or None,
        "cpuFrequencyMhz": speed or None,
        "cpuMarch": march or None,
    }


def collect_gpu() -> dict:
    gpus = winapi.gpus()
    rows = []
    for gpu in gpus:
        name = (gpu.get("name") or "").strip() or (gpu.get("vendor") or "").strip()
        if not name:
            continue
        details = []
        dedicated = ((gpu.get("memory") or {}).get("dedicated") or {}).get("total")
        if dedicated:
            details.append(f"({fmt.size(dedicated)})")
        if gpu.get("type") and gpu["type"] != "Unknown":
            details.append(f"[{gpu['type']}]")
        rows.append(" ".join([name, *details]))
    return {"gpu": rows or None}


# --------------------------------------------------------------------------- #
# Memory / swap
# --------------------------------------------------------------------------- #
def collect_memory() -> dict:
    memory = winapi.memory()
    if not memory:
        return {"memory": None, "memoryTotal": None, "memoryUsed": None}
    total, available = memory
    used = max(0, total - available)
    percent = (used / total * 100) if total else 0
    composed = f"{fmt.size(used)} / {fmt.size(total)} ({fmt.percent(percent)})"
    return {"memory": composed, "memoryTotal": total, "memoryUsed": used}


def collect_swap() -> dict:
    pagefiles = winapi.pagefiles()
    if not pagefiles:
        return {"swap": None, "swapTotal": None, "swapUsed": None}
    total = sum(entry[2] for entry in pagefiles)
    used = sum(entry[1] for entry in pagefiles)
    if not total:
        return {"swap": None, "swapTotal": None, "swapUsed": None}
    percent = used / total * 100
    composed = f"{fmt.size(used)} / {fmt.size(total)} ({fmt.percent(percent)})"
    return {"swap": composed, "swapTotal": total, "swapUsed": used}


# --------------------------------------------------------------------------- #
# Disks / network / battery / displays
# --------------------------------------------------------------------------- #
def collect_disks() -> dict:
    rows = []
    for disk in winapi.disks():
        mount = disk.get("mountpoint") or ""
        label = disk.get("name") or ""
        bytes_ = disk.get("bytes") or {}
        total = int(bytes_.get("total") or 0)
        used = int(bytes_.get("used") or 0)
        if not total:
            continue
        percent = used / total * 100
        title = label or mount.rstrip("\\/")
        where = mount.rstrip("\\/")
        prefix = f"{title} ({where})" if where and where != title else title
        rows.append(f"{prefix} {fmt.size(used)} / {fmt.size(total)} ({fmt.percent(percent)})")
    return {"disks": rows or None}


def collect_network() -> dict:
    adapters = winapi.adapters()
    if not adapters:
        return {"localIp": None, "macAddress": None}
    route = winapi.default_route_ipv4()
    chosen = next((a for a in adapters if a.get("ifindex") == route), adapters[0])
    addresses = chosen.get("addresses") or []
    if not addresses:
        return {"localIp": None, "macAddress": chosen.get("mac") or None}
    address = addresses[0][0]
    name = chosen.get("name") or ""
    composed = f"{address} ({name})" if name else address
    return {"localIp": composed, "macAddress": chosen.get("mac") or None}


def collect_battery() -> dict:
    state = winapi.battery_state()
    if not state:
        return {"battery": None}
    capacity = state.get("max_capacity") or 0
    remaining = state.get("remaining_capacity") or 0
    if capacity:
        percent = round(remaining / capacity * 100)
        text = f"{percent}%"
    else:
        text = "Unknown"
    if state.get("charging"):
        text += " [Charging]"
    elif state.get("ac_online"):
        text += " [AC]"
    elif state.get("discharging"):
        text += " [Discharging]"
    return {"battery": text}


def _refresh_text(hz: float) -> str:
    if not hz:
        return ""
    if abs(hz - round(hz)) < 0.1:
        return f"{round(hz)} Hz"
    return f"{hz:.2f} Hz"


def collect_displays() -> dict:
    rows = []
    for display in winapi.displays():
        width = display.get("width") or 0
        height = display.get("height") or 0
        if not width or not height:
            continue
        parts = [f"{width}x{height}"]
        refresh = _refresh_text(display.get("refreshRate") or 0)
        if refresh:
            parts.append(f"@ {refresh}")
        name = (display.get("name") or "").strip()
        if name:
            parts.append(f"({name})")
        rows.append(" ".join(parts))
    return {"displays": rows or None}


# --------------------------------------------------------------------------- #
# Desktop appearance
# --------------------------------------------------------------------------- #
def collect_locale() -> dict:
    return {"locale": winapi.locale_info()}


def collect_theme() -> dict:
    return {"theme": (winapi.theme_info() or {}).get("theme1") or None}


def collect_wm_theme() -> dict:
    return {"wmTheme": winapi.wm_theme()}


def collect_font() -> dict:
    for name in winapi.fonts():
        if name:
            return {"font": name}
    return {"font": None}


def collect_cursor() -> dict:
    info = winapi.cursor_info()
    theme = info.get("theme") or ""
    size = info.get("size") or ""
    if theme and size:
        text = f"{theme} ({size}px)"
    else:
        text = theme or size or ""
    return {"cursor": text or None}


def collect_icons() -> dict:
    info = winapi.icons_info() or {}
    parts = [info.get("icons1") or "", info.get("icons2") or ""]
    text = ", ".join(part for part in parts if part)
    return {"icons": text or None}


COLLECTORS: dict[str, Callable[[], dict]] = {
    "identity": collect_identity,
    "os": collect_os,
    "host": collect_host,
    "kernel": collect_kernel,
    "uptime": collect_uptime,
    "packages": collect_packages,
    "shell": collect_shell,
    "terminal": collect_terminal,
    "cpu": collect_cpu,
    "gpu": collect_gpu,
    "memory": collect_memory,
    "swap": collect_swap,
    "disks": collect_disks,
    "network": collect_network,
    "battery": collect_battery,
    "displays": collect_displays,
    "locale": collect_locale,
    "theme": collect_theme,
    "wmTheme": collect_wm_theme,
    "font": collect_font,
    "cursor": collect_cursor,
    "icons": collect_icons,
}


def collect(needed_keys: set[str]) -> dict:
    """Collect every key needed for the selected fields.

    Values that could not be detected are ``None``; the renderer skips rows
    whose value is missing.
    """
    groups = {KEY_GROUPS[key] for key in needed_keys if key in KEY_GROUPS}
    live: dict = {key: None for key in KEY_GROUPS}
    for group in sorted(groups):
        live.update(_safe(COLLECTORS[group]))
    return live
