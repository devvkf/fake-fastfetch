# sysfetch

A neofetch / fastfetch-style system panel for Windows where **every value comes
from `config.json`**. Leave a value as `null` and it is detected live; set it to
anything else and that text is displayed instead. Profiles are overlays in
`profiles/` so you can switch between completely different "machines".

```
$ sysfetch -p macbook-pro
                     ..'        ada@macbook-pro
                 ,xNMM.         ──────────────────────────────
               .OMMMMo          OS      : macOS Sonoma 14.5
               lMM"             Host    : Apple MacBook Pro (16-inch, 2023)
     .;loddo:.  .olloddol;.     Kernel  : Darwin 23.5.0 arm64
   cKMMMMMMMMMMNWMMMMMMMMMM0:   Uptime  : 2 days, 7 hours, 14 mins
 .KMMMMMMMMMMMMMMMMMMMMMMMWd.   Packages: 184 (brew 173, brew-cask 11)
 XMMMMMMMMMMMMMMMMMMMMMMMX.     Shell   : zsh 5.9
;MMMMMMMMMMMMMMMMMMMMMMMM:      Terminal: iTerm2
:MMMMMMMMMMMMMMMMMMMMMMMM:      CPU     : Apple M3 Max (16) @ 4.05 GHz
.MMMMMMMMMMMMMMMMMMMMMMMMX.     GPU     : Apple M3 Max (40-core GPU) [Integrated]
 kMMMMMMMMMMMMMMMMMMMMMMMMWd.   Memory  : 15.12 GiB / 36.00 GiB (42%)
 'XMMMMMMMMMMMMMMMMMMMMMMMMMMk  Swap    : 0 B / 4.25 GiB (0%)
  'XMMMMMMMMMMMMMMMMMMMMMMMMK.  Disk    : Macintosh HD (/) 412.10 GiB / 926.35 GiB (44%)
    kMMMMMMMMMMMMMMMMMMMMMMd              Time Machine (External) 820.44 GiB / 1.82 TiB (44%)
     ;KMMMMMMMWXXWMMMMMMMk.     Local IP: 10.0.1.42 (en0)
       "cooc*"    "*coo'"       Battery : 78% [Discharging]
                                Display : 3456x2234 @ 120 Hz (Liquid Retina XDR)
                                ...
```

## Usage

```
sysfetch                        # config.json, live values for null fields
sysfetch -p steam-deck          # apply a profile
sysfetch --list-profiles        # list profiles
sysfetch --list-fields          # list fields usable in display.fields
sysfetch --plain                # no logo, no colours
sysfetch --no-color             # colours off, logo stays
sysfetch --no-logo
sysfetch --logo windows_11      # force a logo (windows, windows_11, linux, ubuntu, macos)
sysfetch --json                 # resolved spec + rendered rows as JSON
sysfetch --show-spec            # every resolved value, * marks config overrides
```

`sysfetch` is the shim in `C:\Commands` (`sysfetch.ps1` + `sysfetch.bat`); it
runs `python -m sysfetch` from the repo root. Profiles can also be selected with
the `SYSFETCH_PROFILE` environment variable, or by setting `"defaultProfile"` in
`config.json`.

## How values resolve

Each row is built from one *direct* key or several *component* keys:

| Row | Direct key | Component keys (used when the direct key is null) |
| --- | --- | --- |
| OS | `os` | `osName`, `osVersion`, `osCodename`, `osArch` |
| Host | `host` | `hostVendor`, `hostName`, `hostVersion`, `hostSerial` |
| Kernel | `kernel` | `kernelName`, `kernelVersion`, `kernelArch` |
| Uptime | `uptime` | `uptimeSeconds` |
| Packages | `packages` | `packagesAll`, `packagesScoop`, `packagesChoco`, `packagesScoopGlobal` |
| Shell | `shell` | `shellName`, `shellVersion`, `shellPath` |
| CPU | `cpu` | `cpuName`, `cpuVendor`, `cpuCores`, `cpuThreads`, `cpuFrequencyMhz`, `cpuMarch` |
| Memory / Swap | `memory` / `swap` | `memoryTotal`+`memoryUsed`, `swapTotal`+`swapUsed` (bytes) |
| Disk | `disks` | — (string or list of strings) |
| Local IP | `localIp` | `macAddress` |

Everything else (`gpu`, `terminal`, `battery`, `displays`, `locale`, `theme`,
`wmTheme`, `font`, `cursor`, `icons`, `user`, `hostname`) is a direct value.
Values may be a string, a number, or a **list of strings** (one line each).

Rules:

- `null` (or a missing key) means *detect live*.
- `false` means *hide this row*.
- A direct key set to a string overrides the component keys entirely.
- A component key set to a non-null value replaces just that part of the
  composed row, e.g. `"cpuThreads": 64` keeps the detected CPU name.
- Numbers that represent bytes (`memoryTotal`, `memoryUsed`, `swapTotal`,
  `swapUsed`) are formatted fastfetch-style; strings are shown verbatim.
- `system.custom` rows support `{key}` placeholders, e.g. `"{cpuName}"`.

Rows can be reordered, hidden, or relabelled in `display`:

```json
"display": {
  "fields": ["title", "separator", "os", "cpu", "custom"],
  "hide": ["locale"],
  "labels": { "os": "System" }
}
```

## Display options

| Key | Meaning |
| --- | --- |
| `color` | `false` disables all ANSI colour |
| `showLogo`, `logo`, `logoGap` | logo visibility, name (`auto` picks from the OS values), spacing |
| `logoArt`, `logoColors` | replace the art; `$1`..`$9` are placeholders for the colour list |
| `titleColor`, `keyColor`, `valueColor`, `separatorColor` | colour names, 0–255 indices or `#RRGGBB` |
| `fields`, `hide`, `labels`, `alignValues` | row selection and layout |

## Profiles

`profiles/*.json` are deep-merged over `config.json`, so a profile only lists
what differs. Shipped examples:

- `macbook-pro` — Apple M3 Max / macOS (switches to the Apple logo)
- `steam-deck` — SteamOS / AMD APU
- `workstation` — Threadripper + dual RTX 4090
- `retro` — Gateway 2000 / Windows 98 SE, green monochrome styling
- `ubuntu-server` — headless, no logo, custom rows

Create your own by copying any file; `--list-profiles` reads the `name` and
`description` fields from each one. JSON files are validated against
[`schema/config.schema.json`](schema/config.schema.json) (referenced by
`$schema` in `config.json`), and typos in `system` keys, `fields` or `logo`
produce a clear error with a suggestion.

## Layout

```
config.json                 base config (all values null = fully live)
profiles/<name>.json        overlays
schema/config.schema.json   JSON schema for both
sysfetch/
  config.py                 loading, merging, validation, key resolution
  collectors.py             live detection (one group per subsystem)
  rows.py                   turns the resolved spec into rows
  render.py                 colours, logo art, two-column layout
  fmt.py, logos.py, winapi.py   formatting helpers and Windows API layer
tests/test_sysfetch.py      stdlib unittest suite (no hardware needed)
```

Run the tests with:

```
python -m unittest discover -s tests -v
```
