"""Tests for sysfetch's config merging, row composition and rendering.

Run with:  python -m unittest discover -s tests -v
No Windows APIs are required: collectors are replaced with canned values.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sysfetch import collectors, config as config_mod, render, rows as rows_mod  # noqa: E402
from sysfetch.cli import main  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

LIVE = {
    "user": "liveuser",
    "hostname": "livehost",
    "os": "Live OS 1.0",
    "osName": "Live OS",
    "osVersion": "1.0",
    "osCodename": "live",
    "osArch": "x86_64",
    "host": "Live Host",
    "hostVendor": "Live",
    "hostName": "Host",
    "hostVersion": None,
    "hostSerial": None,
    "kernel": "Linux 6.0 x86_64",
    "kernelName": "Linux",
    "kernelVersion": "6.0",
    "kernelArch": "x86_64",
    "uptime": "1 hour",
    "uptimeSeconds": 3600,
    "packages": "10",
    "packagesAll": 10,
    "packagesScoop": None,
    "packagesChoco": None,
    "packagesScoopGlobal": None,
    "shell": "bash 5.0",
    "shellName": "bash",
    "shellVersion": "5.0",
    "shellPath": "/bin/bash",
    "terminal": "Term",
    "cpu": "CPU (8) @ 3.00 GHz",
    "cpuName": "CPU",
    "cpuVendor": "Vendor",
    "cpuCores": 4,
    "cpuThreads": 8,
    "cpuFrequencyMhz": 3000,
    "cpuMarch": "x86_64-v3",
    "gpu": ["GPU (1.00 GiB) [Integrated]"],
    "memory": "1.00 GiB / 8.00 GiB (13%)",
    "memoryTotal": 8589934592,
    "memoryUsed": 1073741824,
    "swap": None,
    "swapTotal": None,
    "swapUsed": None,
    "disks": ["Disk (C:) 1.00 GiB / 2.00 GiB (50%)"],
    "localIp": "10.0.0.2 (eth0)",
    "macAddress": "AA:BB:CC:DD:EE:FF",
    "battery": "50% [AC]",
    "displays": ["1920x1080 @ 60 Hz"],
    "locale": "en_US.UTF-8",
    "theme": "Fluent",
    "wmTheme": "Dark",
    "font": "Font (10pt)",
    "cursor": "Cursor (24px)",
    "icons": "Recycle Bin",
    "custom": None,
}


class FakeCollectors:
    """Replace live detection with LIVE and record which keys were asked for."""

    def __init__(self):
        self.asked: set[str] = set()
        self._original = None

    def __enter__(self):
        self._original = collectors.collect

        def collect(needed_keys):
            self.asked = set(needed_keys)
            return {key: LIVE.get(key) for key in collectors.KEY_GROUPS}

        collectors.collect = collect
        return self

    def __exit__(self, *exc):
        collectors.collect = self._original


def make_dir(base: dict, profiles: dict[str, dict] | None = None) -> Path:
    root = Path(tempfile.mkdtemp(prefix="sysfetch-test-"))
    (root / "config.json").write_text(json.dumps(base), encoding="utf-8")
    if profiles:
        (root / "profiles").mkdir()
        for name, data in profiles.items():
            (root / "profiles" / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    return root


def render_config(base: dict, profile: str | None = None) -> tuple[str, set[str]]:
    with FakeCollectors() as fake:
        config, _meta = config_mod.load_config(
            directory=make_dir(base, {"p": {"system": {"os": "Profile OS"}}}),
            profile=profile,
        )
        spec, explicit = config_mod.resolve_spec(collectors.collect(config_mod.needed_keys(config)), config)
        built = rows_mod.build_rows(config, spec, explicit)
        text = render.render(config, spec, built)
    return text, fake.asked


class ConfigTests(unittest.TestCase):
    def test_deep_merge_does_not_mutate(self):
        base = {"display": {"labels": {"os": "A"}}, "system": {"os": "B"}}
        merged = config_mod.deep_merge(base, {"display": {"labels": {"cpu": "C"}}})
        self.assertEqual(merged["display"]["labels"], {"os": "A", "cpu": "C"})
        self.assertEqual(base["display"]["labels"], {"os": "A"})

    def test_profile_overrides_base_and_null_inherits(self):
        root = make_dir(
            {"system": {"os": "Base OS", "user": "base"}},
            {"p": {"system": {"os": "Profile OS", "hostname": None}}},
        )
        with FakeCollectors():
            config, meta = config_mod.load_config(directory=root, profile="p")
            spec, explicit = config_mod.resolve_spec(
                collectors.collect(config_mod.needed_keys(config)), config
            )
        self.assertEqual(meta["profile"], "p")
        self.assertEqual(spec["os"], "Profile OS")
        self.assertIn("os", explicit)
        self.assertEqual(spec["user"], "base")
        self.assertEqual(spec["hostname"], "livehost")

    def test_profile_lookup_by_inner_name(self):
        root = make_dir({}, {"steam-deck": {"name": "Steam Deck", "system": {"os": "X"}}})
        with FakeCollectors():
            config, meta = config_mod.load_config(directory=root, profile="Steam Deck")
        self.assertEqual(meta["profile_path"].name, "steam-deck.json")

    def test_unknown_profile_lists_available(self):
        root = make_dir({}, {"one": {}, "two": {}})
        with self.assertRaises(config_mod.ConfigError) as caught:
            config_mod.load_config(directory=root, profile="missing")
        self.assertIn("one", str(caught.exception))
        self.assertIn("two", str(caught.exception))

    def test_unknown_system_key_is_an_error(self):
        with self.assertRaises(config_mod.ConfigError) as caught:
            config_mod.load_config(directory=make_dir({"system": {"cpuNamee": "x"}}))
        self.assertIn("cpuNamee", str(caught.exception))
        self.assertIn("cpuName", str(caught.exception))

    def test_unknown_field_suggests_typo(self):
        with self.assertRaises(config_mod.ConfigError) as caught:
            config_mod.load_config(directory=make_dir({"display": {"fields": ["os", "memroy"]}}))
        self.assertIn("memory", str(caught.exception))

    def test_unknown_logo_is_an_error(self):
        with self.assertRaises(config_mod.ConfigError):
            config_mod.load_config(directory=make_dir({"display": {"logo": "windwos"}}))

    def test_invalid_json_reports_location(self):
        root = Path(tempfile.mkdtemp(prefix="sysfetch-test-"))
        (root / "config.json").write_text('{"system": {', encoding="utf-8")
        with self.assertRaises(config_mod.ConfigError) as caught:
            config_mod.load_config(directory=root)
        self.assertIn("line 1", str(caught.exception))

    def test_missing_config(self):
        with self.assertRaises(config_mod.ConfigError):
            config_mod.load_config(directory=Path(tempfile.mkdtemp()) / "nope")

    def test_default_profile_used(self):
        root = make_dir(
            {"defaultProfile": "p", "system": {"os": "Base"}},
            {"p": {"system": {"os": "Default Profile"}}},
        )
        with FakeCollectors():
            config, meta = config_mod.load_config(directory=root)
        self.assertEqual(meta["profile"], "p")
        self.assertEqual(config["system"]["os"], "Default Profile")

    def test_env_profile_used(self):
        root = make_dir({}, {"p": {"system": {"os": "Env"}}})
        import os

        os.environ[config_mod.PROFILE_ENV] = "p"
        try:
            with FakeCollectors():
                config, meta = config_mod.load_config(directory=root)
        finally:
            del os.environ[config_mod.PROFILE_ENV]
        self.assertEqual(meta["profile"], "p")

    def test_shipped_configs_validate(self):
        base = json.loads((REPO / "config.json").read_text(encoding="utf-8"))
        config_mod.validate({**base, "display": {**config_mod.DEFAULT_DISPLAY, **(base.get("display") or {})}})
        for path in sorted((REPO / "profiles").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            config_mod.validate(
                config_mod.deep_merge(
                    {**base, "display": {**config_mod.DEFAULT_DISPLAY, **(base.get("display") or {})}},
                    data,
                )
            )


class CollectionTests(unittest.TestCase):
    def test_only_needed_groups_are_collected(self):
        root = make_dir(
            {
                "display": {"fields": ["os", "cpu"]},
                "system": {"gpu": "Should not be probed"},
            }
        )
        with FakeCollectors() as fake:
            config, _ = config_mod.load_config(directory=root)
            needed = config_mod.needed_keys(config)
            collectors.collect(needed)
        self.assertEqual(needed, {"os", "osName", "osVersion", "osCodename", "osArch",
                                  "cpu", "cpuName", "cpuVendor", "cpuCores", "cpuThreads",
                                  "cpuFrequencyMhz", "cpuMarch"})
        self.assertEqual(collectors.KEY_GROUPS["gpu"], "gpu")
        self.assertNotIn("gpu", fake.asked)

    def test_direct_override_skips_component_keys(self):
        root = make_dir({"system": {"os": "Fake", "cpu": "Fake CPU"}})
        with FakeCollectors():
            config, _ = config_mod.load_config(directory=root)
            needed = config_mod.needed_keys(config)
        self.assertNotIn("osName", needed)
        self.assertNotIn("cpuName", needed)
        self.assertNotIn("cpuThreads", needed)

    def test_collector_failure_is_contained(self):
        original = collectors.COLLECTORS["os"]
        collectors.COLLECTORS["os"] = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            live = collectors.collect({"os"})
        finally:
            collectors.COLLECTORS["os"] = original
        self.assertIsNone(live["os"])


class RowTests(unittest.TestCase):
    def test_components_compose_when_no_direct_value(self):
        text, _ = render_config(
            {
                "display": {"showLogo": False, "color": False},
                "system": {"osName": "MyOS", "osVersion": "2.0"},
            }
        )
        self.assertIn("OS      : MyOS 2.0", text)

    def test_direct_value_wins_over_components(self):
        text, _ = render_config(
            {
                "display": {"showLogo": False},
                "system": {"os": "Whole OS", "osName": "Ignored"},
            }
        )
        self.assertIn("Whole OS", text)
        self.assertNotIn("Ignored", text)

    def test_null_value_hides_row(self):
        text, _ = render_config(
            {"display": {"showLogo": False, "fields": ["os", "battery"]}, "system": {"battery": None}},
            profile=None,
        )
        self.assertIn("OS", text)
        self.assertIn("Battery", text)  # live value still shows
        text, _ = render_config(
            {
                "display": {"showLogo": False, "fields": ["os", "battery"]},
                "system": {"battery": False},
            }
        )
        self.assertNotIn("Battery", text)

    def test_lists_become_multiple_lines(self):
        text, _ = render_config(
            {
                "display": {"showLogo": False, "fields": ["gpu"]},
                "system": {"gpu": ["GPU A", "GPU B"]},
            }
        )
        self.assertIn("GPU A", text)
        self.assertIn("GPU B", text)

    def test_custom_rows_and_placeholders(self):
        text, _ = render_config(
            {
                "display": {"showLogo": False, "color": False, "fields": ["custom"]},
                "system": {
                    "cpuName": "Ryzen",
                    "custom": [
                        {"label": "Chip", "value": "{cpuName}!"},
                        {"label": "Missing", "value": "{nope}"},
                        ["Pair", "value"],
                        {"label": "Dropped", "value": False},
                    ],
                },
            }
        )
        self.assertIn("Chip   : Ryzen!", text)
        self.assertIn("Missing: {nope}", text)
        self.assertIn("Pair   : value", text)
        self.assertNotIn("Dropped", text)

    def test_hide_and_labels(self):
        text, _ = render_config(
            {
                "display": {
                    "showLogo": False,
                    "hide": ["cpu"],
                    "labels": {"os": "System"},
                }
            }
        )
        self.assertIn("System", text)
        self.assertNotIn("CPU", text)

    def test_memory_bytes_formatting(self):
        text, _ = render_config(
            {
                "display": {"showLogo": False, "fields": ["memory"]},
                "system": {"memoryTotal": 17179869184, "memoryUsed": 4294967296},
            }
        )
        self.assertIn("4.00 GiB / 16.00 GiB (25%)", text)

    def test_memory_string_shown_verbatim(self):
        text, _ = render_config(
            {
                "display": {"showLogo": False, "fields": ["memory"]},
                "system": {"memory": "all of it"},
            }
        )
        self.assertIn("all of it", text)

    def test_uptime_from_seconds(self):
        text, _ = render_config(
            {
                "display": {"showLogo": False, "fields": ["uptime"]},
                "system": {"uptimeSeconds": 90061},
            }
        )
        self.assertIn("1 day, 1 hour, 1 min", text)


class RenderTests(unittest.TestCase):
    def test_plain_has_no_ansi(self):
        text, _ = render_config({"display": {"showLogo": False, "color": False}})
        self.assertNotIn("\x1b", text)

    def test_colour_codes(self):
        self.assertEqual(render.color_code("bright_cyan"), "96")
        self.assertEqual(render.color_code(196), "38;5;196")
        self.assertEqual(render.color_code("#ff0000"), "38;2;255;0;0")
        self.assertEqual(render.color_code("#f00"), "38;2;255;0;0")
        self.assertIsNone(render.color_code("auto"))
        self.assertIsNone(render.color_code(False))
        self.assertIsNone(render.color_code("not-a-colour"))

    def test_logo_auto_follows_os(self):
        self.assertEqual(render.auto_logo_name({"os": "macOS Sonoma"}), "macos")
        self.assertEqual(render.auto_logo_name({"os": "Ubuntu 24.04"}), "ubuntu")
        self.assertEqual(render.auto_logo_name({"os": "Arch Linux"}), "linux")
        self.assertEqual(render.auto_logo_name({"os": "Windows 11 Pro"}), "windows_11")
        self.assertEqual(render.auto_logo_name({"os": "Windows 98"}), "windows")

    def test_art_placeholders_never_leak(self):
        art, colors = render.logo_source({"logo": "auto", "color": True}, {"os": "Windows 11"})
        self.assertIn("$1", art)  # raw art keeps its placeholders...
        for line in render._paint_art_spans(art, colors):
            self.assertTrue(all("$" not in text for text, _ in line))  # ...spans do not

    def test_unknown_logo_name_falls_back_to_banner(self):
        # A logo name without built-in art (only reachable with custom art, which
        # validation requires) renders as a one-line banner.
        art, _colors = render.logo_source(
            {"logo": "NixOS", "logoArt": "$1AB"}, {"os": "Linux"}
        )
        self.assertEqual(art, "$1AB")

    def test_custom_art(self):
        art, _colors = render.logo_source(
            {"logo": "auto", "logoArt": "$1AB\n$2CD", "logoColors": ["red", "blue"]},
            {"os": "Windows 11"},
        )
        self.assertEqual(art, "$1AB\n$2CD")

    def test_columns_line_up(self):
        config = {
            "display": {"showLogo": True, "logo": "windows", "color": False},
            "system": {"os": "X"},
        }
        with FakeCollectors():
            loaded, _ = config_mod.load_config(directory=make_dir(config))
            spec, explicit = config_mod.resolve_spec(LIVE, loaded)
            text = render.render(loaded, spec, rows_mod.build_rows(loaded, spec, explicit))
        columns = {line.index("  bened") if "bened" in line else None for line in text.splitlines()}
        self.assertIsNotNone(columns)

    def test_json_output_is_valid(self):
        import contextlib
        import io

        with FakeCollectors():
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["--json", "--config-dir", str(make_dir({"system": {"os": "J"}}))])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["spec"]["os"], "J")
        self.assertTrue(payload["rows"])


if __name__ == "__main__":
    unittest.main()
