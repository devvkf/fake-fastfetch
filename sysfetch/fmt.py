"""Value formatting helpers, mirroring fastfetch's display rules."""

from __future__ import annotations

IEC = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
SI = ("B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
JEDEC = ("B", "KB", "MB", "GB", "TB")


def size(num: int | float, ndigits: int = 2, binary: str = "iec", space: bool = True) -> str:
    """Format a byte count the way fastfetch does (IEC by default)."""
    prefixes = {"iec": IEC, "si": SI, "jedec": JEDEC, "b": ("B",)}.get(binary, IEC)
    base = 1000 if binary == "si" else 1024
    value = float(num)
    counter = 0
    while value >= base and counter < len(prefixes) - 1:
        value /= base
        counter += 1
    if counter == 0:
        text = str(int(num))
    else:
        text = f"{value:.{ndigits}f}"
    return text + (" " if space else "") + prefixes[counter]


def percent(value: float, ndigits: int = 0, width: int = 0) -> str:
    return f"{value:{width}.{ndigits}f}%"


def freq(mhz: int | float) -> str:
    """fastfetch's ffFreqAppendNum: GHz with two decimals, trailing zeros kept."""
    if not mhz:
        return ""
    return f"{mhz / 1000.0:.2f} GHz"


def duration(total_seconds: int) -> str:
    """fastfetch's ffDurationAppendNum."""
    total_seconds = int(total_seconds)
    if total_seconds < 60:
        return f"{total_seconds} second" + ("" if total_seconds == 1 else "s")

    seconds = total_seconds % 60
    total_seconds //= 60
    if seconds >= 30:
        total_seconds += 1

    minutes = total_seconds % 60
    total_seconds //= 60
    hours = total_seconds % 24
    days = total_seconds // 24

    parts: list[str] = []
    if days > 0:
        text = f"{days} day" + ("" if days == 1 else "s")
        if days >= 100:
            text += "(!)"
        parts.append(text)
    if hours > 0:
        parts.append(f"{hours} hour" + ("" if hours == 1 else "s"))
    if minutes > 0:
        parts.append(f"{minutes} min" + ("" if minutes == 1 else "s"))
    return ", ".join(parts)


def number(value: float, ndigits: int = 2, trailing: bool = True) -> str:
    text = f"{value:.{ndigits}f}"
    if not trailing and "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def percent_color(value: float, green: float = 50, yellow: float = 80) -> str:
    """ANSI SGR parameters for a percentage, fastfetch style."""
    if green <= yellow:
        if value > yellow:
            return "91"
        if value > green:
            return "93"
        return "32"
    if value < yellow:
        return "91"
    if value < green:
        return "93"
    return "32"
