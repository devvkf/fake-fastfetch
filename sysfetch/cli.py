"""Command line interface for sysfetch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, collectors, config as config_mod, render, rows as rows_mod


def _configure_output() -> None:
    """Make stdout UTF-8 and enable ANSI processing on Windows consoles."""
    if sys.platform == "win32":
        try:
            from . import winapi

            winapi.kernel32.SetConsoleOutputCP(65001)
            handle = winapi.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = winapi.wt.DWORD()
            if winapi.kernel32.GetConsoleMode(handle, winapi.ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING | ENABLE_PROCESSED_OUTPUT
                winapi.kernel32.SetConsoleMode(handle, mode.value | 0x4 | 0x1)
        except Exception:  # noqa: BLE001 - output still works without colour
            pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sysfetch",
        description="A fastfetch-style system panel whose values come from config.json.",
        epilog=(
            "Profiles live in <config-dir>/profiles/<name>.json and are merged over "
            "config.json. Set SYSFETCH_PROFILE to pick one by default."
        ),
    )
    parser.add_argument(
        "-p",
        "--profile",
        metavar="NAME",
        help="profile to load (file name without .json, or a path to a JSON file)",
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="PATH",
        help="base config file (default: <config-dir>/config.json)",
    )
    parser.add_argument(
        "--config-dir",
        metavar="DIR",
        help="directory containing config.json and profiles/ "
        "(default: the repository root, or $SYSFETCH_CONFIG_DIR)",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="list available profiles and exit",
    )
    parser.add_argument(
        "--list-fields",
        action="store_true",
        help="list the fields usable in display.fields and exit",
    )
    parser.add_argument(
        "--show-spec",
        action="store_true",
        help="print every resolved system value (live detection included) and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the resolved spec and rows as JSON instead of the panel",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="no logo, no colours, one 'Label: value' block",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colours",
    )
    parser.add_argument(
        "--no-logo",
        action="store_true",
        help="hide the logo",
    )
    parser.add_argument(
        "--logo",
        metavar="NAME",
        help="override the logo (windows, windows_11, linux, ubuntu, macos, auto)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sysfetch {__version__}",
    )
    return parser


def _print_profiles(root: Path) -> int:
    profiles = config_mod.available_profiles(root)
    if not profiles:
        print(f"No profiles found in {root / 'profiles'}")
        return 0
    width = max(len(entry["name"]) for entry in profiles)
    for entry in profiles:
        suffix = f"  — {entry['description']}" if entry["description"] else ""
        if entry["error"]:
            suffix = f"  [invalid: {entry['error']}]"
        print(f"{entry['name'].ljust(width)}{suffix}")
    return 0


def _print_fields() -> int:
    width = max(len(name) for name in config_mod.ALL_FIELDS)
    for name in config_mod.ALL_FIELDS:
        if name in config_mod.DEFAULT_LABELS:
            print(f"{name.ljust(width)}  {config_mod.DEFAULT_LABELS[name]}")
        elif name == "title":
            print(f"{name.ljust(width)}  user@hostname header")
        elif name == "separator":
            print(f"{name.ljust(width)}  horizontal rule")
        else:
            print(f"{name.ljust(width)}  rows from system.custom")
    return 0


def _apply_overrides(config: dict, args: argparse.Namespace) -> None:
    display = config.setdefault("display", {})
    if args.no_color:
        display["color"] = False
    if args.plain:
        display["color"] = False
        display["showLogo"] = False
    if args.no_logo:
        display["showLogo"] = False
    if args.logo:
        display["showLogo"] = True
        display["logo"] = args.logo


def _build(config: dict, all_keys: bool = False) -> tuple[dict, set[str], list]:
    needed = set(config_mod.SPEC_KEYS) if all_keys else config_mod.needed_keys(config)
    live = collectors.collect(needed)
    spec, explicit = config_mod.resolve_spec(live, config)
    built = rows_mod.build_rows(config, spec, explicit)
    return spec, explicit, built


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _configure_output()

    root = config_mod.config_dir(args.config_dir)
    if args.list_profiles:
        return _print_profiles(root)
    if args.list_fields:
        return _print_fields()

    try:
        config, meta = config_mod.load_config(
            directory=args.config_dir,
            config_path=args.config,
            profile=args.profile,
        )
        _apply_overrides(config, args)
        # Re-validate: CLI overrides bypass the checks load_config ran.
        config_mod.validate(config)
        spec, explicit, built = _build(config, all_keys=args.show_spec or args.json)
    except config_mod.ConfigError as exc:
        print(f"sysfetch: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "profile": meta["profile"],
            "configPath": str(meta["config_path"]),
            "profilePath": str(meta["profile_path"]) if meta["profile_path"] else None,
            "spec": spec,
            "explicit": sorted(explicit),
            "rows": [
                {
                    "label": row.label,
                    "separator": row.separator,
                    "title": row.title,
                    "lines": row.lines,
                }
                for row in built
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return 0

    if args.show_spec:
        for key in config_mod.SPEC_KEYS:
            value = spec.get(key)
            marker = "*" if key in explicit else " "
            print(f"{marker} {key.ljust(20)} {json.dumps(value, ensure_ascii=False, default=str)}")
        print("\n(* = overridden by config)")
        return 0

    try:
        print(render.render(config, spec, built))
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
