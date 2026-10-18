"""ANSI colouring, logo art and the side-by-side panel layout."""

from __future__ import annotations

import re

from . import logos
from .rows import Row

RESET = "\x1b[0m"

COLOR_NAMES: dict[str, str] = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}


def color_code(value) -> str | None:
    """Translate a config colour (name, 0-255 index, #RRGGBB) to SGR params."""
    if value is None or value is False:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return f"38;5;{value}" if 0 <= value <= 255 else None
    text = str(value).strip().lower()
    if text in ("", "none", "default", "auto"):
        return None
    if text in COLOR_NAMES:
        return COLOR_NAMES[text]
    if text.startswith("#") and len(text) in (4, 7):
        digits = text[1:]
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        try:
            red, green, blue = (int(digits[index : index + 2], 16) for index in (0, 2, 4))
        except ValueError:
            return None
        return f"38;2;{red};{green};{blue}"
    if text.isdigit() and 0 <= int(text) <= 255:
        return f"38;5;{int(text)}"
    return None


def paint(text: str, code: str | None, enabled: bool = True) -> str:
    """Colour ``text`` with an SGR code.

    fastfetch's art embeds colours but not resets; resetting every span keeps
    the logo from bleeding into the panel rows next to it.
    """
    if not enabled or not code:
        return text
    return f"\x1b[{code}m{text}{RESET}"


def paint_bold(text: str, code: str | None, enabled: bool = True) -> str:
    if not enabled or not code:
        return text
    return f"\x1b[1;{code}m{text}{RESET}"


def _art_palette(colors: list[str] | None) -> dict[int, str | None]:
    palette: dict[int, str | None] = {}
    if colors:
        for index, value in enumerate(colors, start=1):
            palette[index] = color_code(value)
    return palette


def _paint_art_spans(art: str, colors: list[str] | None) -> list[list[tuple[str, str | None]]]:
    """Split art lines into ``(text, SGR code)`` spans, without embedding ANSI."""
    palette = _art_palette(colors)
    pattern = re.compile(r"\$([1-9])")
    lines: list[list[tuple[str, str | None]]] = []
    for line in art.splitlines():
        spans: list[tuple[str, str | None]] = []
        position = 0
        code: str | None = None
        for match in pattern.finditer(line):
            if match.start() > position:
                spans.append((line[position : match.start()], code))
            code = palette.get(int(match.group(1)))
            position = match.end()
        if position < len(line):
            spans.append((line[position:], code))
        lines.append(spans)
    return lines


def _spans_text(spans: list[tuple[str, str | None]]) -> str:
    return "".join(text for text, _code in spans)


def auto_logo_name(spec: dict) -> str:
    """Pick a built-in logo from the (possibly faked) OS name."""
    haystack = " ".join(
        str(spec.get(key) or "") for key in ("os", "osName", "osVersion", "kernel", "kernelName")
    ).lower()
    if "macos" in haystack or "mac os" in haystack or "darwin" in haystack:
        return "macos"
    if "ubuntu" in haystack:
        return "ubuntu"
    if "linux" in haystack:
        return "linux"
    if "server 2022" in haystack or "windows 11" in haystack or "windows 12" in haystack:
        return "windows_11"
    return "windows"


def logo_source(display: dict, spec: dict) -> tuple[str | None, list[str]]:
    """Raw (placeholder) art text and its colour list for the configured logo."""
    setting = display.get("logo", "auto")
    if setting is False or setting is None:
        return None, []
    if isinstance(setting, bool):  # logo: true means auto
        setting = "auto"
    name = str(setting).strip()
    key = auto_logo_name(spec) if name.lower() in ("", "auto", "default") else logos.resolve(name)
    logo = logos.LOGOS.get(key) if key else None
    if logo is None:
        # No built-in match: use custom art when given, else the name as a banner.
        art = display.get("logoArt")
        if isinstance(art, str) and art:
            colors = display.get("logoColors")
            return art, list(colors) if isinstance(colors, list) else []
        if key:
            # A name the user chose explicitly that has no art: show it.
            return name, []
        return None, []
    art = display.get("logoArt") or logo["art"]
    colors = display.get("logoColors") or logo["colors"]
    if not isinstance(art, str):
        art = logo["art"]
    if not isinstance(colors, list):
        colors = logo["colors"]
    return art, list(colors)


def _row_lines(row: Row, label_width: int, colors: dict, color: bool) -> list[str]:
    if row.separator:
        return [paint("─" * 30, colors["separator"], color)]
    if row.title:
        return [paint_bold(row.lines[0], colors["title"], color)]

    label = row.label or ""
    head = paint(label.ljust(label_width), colors["key"], color)
    prefix = f"{head}: " if label_width or label else ""
    continuation = " " * (label_width + 2)
    out = []
    for index, line in enumerate(row.lines):
        body = paint(line, colors["value"], color)
        out.append((prefix if index == 0 else continuation) + body)
    return out


def render(config: dict, spec: dict, rows: list[Row]) -> str:
    display = config.get("display") or {}
    color = bool(display.get("color", True))
    colors = {
        "title": color_code(display.get("titleColor")),
        "key": color_code(display.get("keyColor")),
        "value": color_code(display.get("valueColor")),
        "separator": color_code(display.get("separatorColor")),
    }

    labels = [row.label for row in rows if row.label and not row.separator]
    label_width = max((len(label) for label in labels), default=0)
    if not display.get("alignValues", True):
        label_width = 0

    body = []
    for row in rows:
        body.extend(_row_lines(row, label_width, colors, color))

    art_spans: list[list[tuple[str, str | None]]] = []
    if display.get("showLogo", True):
        art_text, art_colors = logo_source(display, spec)
        if art_text:
            art_spans = _paint_art_spans(art_text, art_colors)

    if not art_spans:
        return "\n".join(body)

    gap = max(0, int(display.get("logoGap", 2) or 0))
    art_width = max(
        (len(_spans_text(spans)) for spans in art_spans),
        default=0,
    )
    height = max(len(art_spans), len(body))
    out = []
    for index in range(height):
        spans = art_spans[index] if index < len(art_spans) else []
        right = body[index] if index < len(body) else ""
        left_text = _spans_text(spans)
        if right:
            if color:
                left = "".join(
                    paint(text, code, True) if code else text for text, code in spans
                )
            else:
                left = left_text
            padding = " " * (art_width - len(left_text) + gap)
            out.append(left + padding + right)
        elif color:
            out.append(
                "".join(paint(text, code, True) if code else text for text, code in spans)
            )
        else:
            out.append(left_text)
    return "\n".join(line.rstrip() for line in out).rstrip("\n")
