"""Thin ctypes layer over the Windows APIs used by the collectors.

Everything here is best-effort: each helper returns ``None`` (or an empty
container) instead of raising when a call is unavailable, so the collectors can
fall back gracefully and the fake-profile path never depends on real hardware.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import struct
import uuid

IS_WINDOWS = os.name == "nt"


def _load(name: str):
    if not IS_WINDOWS:
        return None
    try:
        return ctypes.WinDLL(name, use_last_error=True)
    except OSError:
        return None


kernel32 = _load("kernel32")
user32 = _load("user32")
advapi32 = _load("advapi32")
ntdll = _load("ntdll")
setupapi = _load("setupapi")
iphlpapi = _load("iphlpapi")
version = _load("version")
secur32 = _load("secur32")
winbrand = _load("winbrand")
shcore = _load("shcore")
dxgi = _load("dxgi")


# --------------------------------------------------------------------------- #
# Structures
# --------------------------------------------------------------------------- #
class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wt.DWORD), ("HighPart", ctypes.c_long)]


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", wt.WORD),
        ("Data3", wt.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, text: str) -> "GUID":
        raw = uuid.UUID(text).bytes_le
        return cls(
            int.from_bytes(raw[0:4], "little"),
            int.from_bytes(raw[4:6], "little"),
            int.from_bytes(raw[6:8], "little"),
            (ctypes.c_ubyte * 8)(*raw[8:]),
        )


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wt.DWORD),
        ("dwMemoryLoad", wt.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class PERFORMANCE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("CommitTotal", ctypes.c_size_t),
        ("CommitLimit", ctypes.c_size_t),
        ("CommitPeak", ctypes.c_size_t),
        ("PhysicalTotal", ctypes.c_size_t),
        ("PhysicalAvailable", ctypes.c_size_t),
        ("SystemCache", ctypes.c_size_t),
        ("KernelTotal", ctypes.c_size_t),
        ("KernelPaged", ctypes.c_size_t),
        ("KernelNonpaged", ctypes.c_size_t),
        ("PageSize", ctypes.c_size_t),
        ("HandleCount", wt.DWORD),
        ("ProcessCount", wt.DWORD),
        ("ThreadCount", wt.DWORD),
    ]


class GROUP_AFFINITY(ctypes.Structure):
    _fields_ = [
        ("Mask", ctypes.c_size_t),
        ("Group", wt.WORD),
        ("Reserved", wt.WORD * 3),
    ]


class PROCESSOR_RELATIONSHIP(ctypes.Structure):
    _fields_ = [
        ("Flags", ctypes.c_ubyte),
        ("EfficiencyClass", ctypes.c_ubyte),
        ("Reserved", ctypes.c_ubyte * 20),
        ("GroupCount", wt.WORD),
        ("GroupMask", GROUP_AFFINITY * 1),
    ]


class SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX(ctypes.Structure):
    _fields_ = [
        ("Relationship", wt.DWORD),
        ("Size", wt.DWORD),
        ("Processor", PROCESSOR_RELATIONSHIP),
    ]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", wt.DWORD),
        ("BatteryFullLifeTime", wt.DWORD),
    ]


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("DeviceName", wt.WCHAR * 32),
        ("DeviceString", wt.WCHAR * 128),
        ("StateFlags", wt.DWORD),
        ("DeviceID", wt.WCHAR * 128),
        ("DeviceKey", wt.WCHAR * 128),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wt.DWORD),
        ("szDevice", wt.WCHAR * 32),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", wt.USHORT),
        ("MaximumLength", wt.USHORT),
        ("Buffer", ctypes.c_void_p),
    ]


class SYSTEM_PAGEFILE_INFORMATION(ctypes.Structure):
    # The name is stored inline right after this header; there are no further
    # numeric fields on current Windows builds.
    _fields_ = [
        ("NextEntryOffset", wt.ULONG),
        ("TotalSize", wt.ULONG),  # pagefile size, in pages
        ("TotalInUse", wt.ULONG),  # pages currently in use
        ("PeakUsage", wt.ULONG),
        ("PageFileName", UNICODE_STRING),
    ]


class BATTERY_QUERY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BatteryTag", wt.ULONG),
        ("InformationLevel", wt.ULONG),
        ("AtRate", ctypes.c_long),
    ]


class BATTERY_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Capabilities", wt.ULONG),
        ("Technology", ctypes.c_ubyte),
        ("Reserved", ctypes.c_ubyte * 3),
        ("Chemistry", ctypes.c_char * 4),
        ("DesignedCapacity", wt.ULONG),
        ("FullChargedCapacity", wt.ULONG),
        ("DefaultAlert1", wt.ULONG),
        ("DefaultAlert2", wt.ULONG),
        ("CriticalBias", wt.ULONG),
        ("CycleCount", wt.ULONG),
    ]


class BATTERY_WAIT_STATUS(ctypes.Structure):
    _fields_ = [
        ("BatteryTag", wt.ULONG),
        ("Timeout", wt.ULONG),
        ("PowerState", wt.ULONG),
        ("LowCapacity", wt.ULONG),
        ("HighCapacity", wt.ULONG),
    ]


class BATTERY_STATUS(ctypes.Structure):
    _fields_ = [
        ("PowerState", wt.ULONG),
        ("Capacity", wt.ULONG),
        ("Voltage", wt.ULONG),
        ("Rate", ctypes.c_long),
    ]


class IP_ADAPTER_ADDRESSES(ctypes.Structure):
    pass


class SOCKADDR(ctypes.Structure):
    _fields_ = [("sa_family", wt.USHORT), ("sa_data", ctypes.c_ubyte * 14)]


class SOCKET_ADDRESS(ctypes.Structure):
    _fields_ = [
        ("lpSockaddr", ctypes.POINTER(SOCKADDR)),
        ("iSockaddrLength", ctypes.c_int),
    ]


class IP_ADAPTER_UNICAST_ADDRESS(ctypes.Structure):
    pass


IP_ADAPTER_UNICAST_ADDRESS._fields_ = [
    ("Length", wt.ULONG),
    ("Flags", wt.DWORD),
    ("Next", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),
    ("Address", SOCKET_ADDRESS),
    ("PrefixOrigin", ctypes.c_uint32),
    ("SuffixOrigin", ctypes.c_uint32),
    ("DadState", ctypes.c_uint32),
    ("ValidLifetime", wt.ULONG),
    ("PreferredLifetime", wt.ULONG),
    ("LeaseLifetime", wt.ULONG),
    ("OnLinkPrefixLength", ctypes.c_ubyte),
]

IP_ADAPTER_ADDRESSES._fields_ = [
    ("Length", wt.ULONG),
    ("IfIndex", wt.DWORD),
    ("Next", ctypes.POINTER(IP_ADAPTER_ADDRESSES)),
    ("AdapterName", ctypes.c_char_p),
    ("FirstUnicastAddress", ctypes.POINTER(IP_ADAPTER_UNICAST_ADDRESS)),
    ("FirstAnycastAddress", ctypes.c_void_p),
    ("FirstMulticastAddress", ctypes.c_void_p),
    ("FirstDnsServerAddress", ctypes.c_void_p),
    ("DnsSuffix", wt.LPWSTR),
    ("Description", wt.LPWSTR),
    ("FriendlyName", wt.LPWSTR),
    ("PhysicalAddress", ctypes.c_ubyte * 8),
    ("PhysicalAddressLength", wt.ULONG),
    ("Flags", wt.ULONG),
    ("Mtu", wt.ULONG),
    ("IfType", wt.ULONG),
    ("OperStatus", ctypes.c_uint32),
    ("Ipv6IfIndex", wt.ULONG),
    ("ZoneIndices", wt.ULONG * 16),
    ("FirstPrefix", ctypes.c_void_p),
    ("TransmitLinkSpeed", ctypes.c_uint64),
    ("ReceiveLinkSpeed", ctypes.c_uint64),
]


# --------------------------------------------------------------------------- #
# Prototypes
# --------------------------------------------------------------------------- #
def _prototype(lib, name, restype, argtypes):
    if lib is None:
        return None
    try:
        fn = getattr(lib, name)
    except AttributeError:
        return None
    fn.restype = restype
    fn.argtypes = argtypes
    return fn


if IS_WINDOWS:
    kernel32.GetTickCount64.restype = ctypes.c_ulonglong
    kernel32.GetComputerNameExW.argtypes = [wt.INT, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    kernel32.GetComputerNameExW.restype = wt.BOOL
    kernel32.GetSystemFirmwareTable.argtypes = [wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD]
    kernel32.GetSystemFirmwareTable.restype = wt.DWORD
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    kernel32.GlobalMemoryStatusEx.restype = wt.BOOL
    kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wt.BOOL
    kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wt.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.GetLogicalProcessorInformationEx.argtypes = [
        wt.DWORD,
        ctypes.c_void_p,
        ctypes.POINTER(wt.DWORD),
    ]
    kernel32.GetLogicalProcessorInformationEx.restype = wt.BOOL
    kernel32.GetSystemPowerStatus.argtypes = [ctypes.POINTER(SYSTEM_POWER_STATUS)]
    kernel32.GetSystemPowerStatus.restype = wt.BOOL
    kernel32.GetUserDefaultLocaleName.argtypes = [wt.LPWSTR, wt.INT]
    kernel32.GetUserDefaultLocaleName.restype = wt.INT
    kernel32.GetACP.restype = wt.UINT
    kernel32.GetDriveTypeW.argtypes = [wt.LPCWSTR]
    kernel32.GetDriveTypeW.restype = wt.UINT
    kernel32.GetLogicalDrives.restype = wt.DWORD
    kernel32.GetVolumeInformationW.argtypes = [
        wt.LPCWSTR,
        wt.LPWSTR,
        wt.DWORD,
        ctypes.POINTER(wt.DWORD),
        ctypes.POINTER(wt.DWORD),
        ctypes.POINTER(wt.DWORD),
        wt.LPWSTR,
        wt.DWORD,
    ]
    kernel32.GetVolumeInformationW.restype = wt.BOOL
    kernel32.GetDiskFreeSpaceExW.argtypes = [
        wt.LPCWSTR,
        ctypes.POINTER(ctypes.c_ulonglong),
        ctypes.POINTER(ctypes.c_ulonglong),
        ctypes.POINTER(ctypes.c_ulonglong),
    ]
    kernel32.GetDiskFreeSpaceExW.restype = wt.BOOL
    kernel32.CreateFileW.argtypes = [
        wt.LPCWSTR,
        wt.DWORD,
        wt.DWORD,
        ctypes.c_void_p,
        wt.DWORD,
        wt.DWORD,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.DeviceIoControl.argtypes = [
        ctypes.c_void_p,
        wt.DWORD,
        ctypes.c_void_p,
        wt.DWORD,
        ctypes.c_void_p,
        wt.DWORD,
        ctypes.POINTER(wt.DWORD),
        ctypes.c_void_p,
    ]
    kernel32.DeviceIoControl.restype = wt.BOOL
    kernel32.GetFileInformationByHandleEx.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        wt.DWORD,
    ]
    kernel32.GetFileInformationByHandleEx.restype = wt.BOOL

    psapi = _load("psapi")
    _prototype(
        psapi,
        "GetPerformanceInfo",
        wt.BOOL,
        [ctypes.POINTER(PERFORMANCE_INFORMATION), wt.DWORD],
    )

    user32.EnumDisplayDevicesW.argtypes = [
        wt.LPCWSTR,
        wt.DWORD,
        ctypes.POINTER(DISPLAY_DEVICEW),
        wt.DWORD,
    ]
    user32.EnumDisplayDevicesW.restype = wt.BOOL
    user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user32.SetProcessDpiAwarenessContext.restype = wt.BOOL
    user32.GetDpiForSystem.restype = wt.UINT
    user32.GetDisplayConfigBufferSizes.argtypes = [
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32),
    ]
    user32.GetDisplayConfigBufferSizes.restype = wt.LONG
    user32.QueryDisplayConfig.argtypes = [
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.QueryDisplayConfig.restype = wt.LONG
    user32.DisplayConfigGetDeviceInfo.argtypes = [ctypes.c_void_p]
    user32.DisplayConfigGetDeviceInfo.restype = wt.LONG
    user32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
    user32.MonitorFromPoint.restype = ctypes.c_void_p

    if shcore is not None:
        shcore.GetDpiForMonitor.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(wt.UINT),
            ctypes.POINTER(wt.UINT),
        ]
        shcore.GetDpiForMonitor.restype = wt.LONG

    _prototype(
        iphlpapi,
        "GetBestInterface",
        wt.DWORD,
        [wt.DWORD, ctypes.POINTER(wt.DWORD)],
    )

    if setupapi is not None:
        setupapi.SetupDiGetClassDevsW.argtypes = [
            ctypes.POINTER(GUID),
            wt.LPCWSTR,
            ctypes.c_void_p,
            wt.DWORD,
        ]
        setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
        setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(GUID),
            wt.DWORD,
            ctypes.c_void_p,
        ]
        setupapi.SetupDiEnumDeviceInterfaces.restype = wt.BOOL
        setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wt.DWORD,
            ctypes.POINTER(wt.DWORD),
            ctypes.c_void_p,
        ]
        setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wt.BOOL
        setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
        setupapi.SetupDiDestroyDeviceInfoList.restype = wt.BOOL

    _prototype(
        secur32,
        "GetUserNameExW",
        wt.BOOL,
        [wt.INT, wt.LPWSTR, ctypes.POINTER(wt.ULONG)],
    )

    _prototype(
        winbrand,
        "BrandingFormatString",
        ctypes.c_void_p,
        [wt.LPCWSTR],
    )

    _prototype(
        iphlpapi,
        "GetAdaptersAddresses",
        wt.ULONG,
        [wt.ULONG, wt.ULONG, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wt.ULONG)],
    )

    _prototype(
        version,
        "GetFileVersionInfoSizeW",
        wt.DWORD,
        [wt.LPCWSTR, ctypes.POINTER(wt.DWORD)],
    )
    _prototype(
        version,
        "GetFileVersionInfoW",
        wt.BOOL,
        [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p],
    )
    _prototype(
        version,
        "VerQueryValueW",
        wt.BOOL,
        [ctypes.c_void_p, wt.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wt.UINT)],
    )


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def dpi_aware() -> None:
    """Opt into per-monitor DPI awareness so monitor queries return real values."""
    if IS_WINDOWS:
        try:
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            pass


def file_version(path: str) -> str | None:
    if not IS_WINDOWS or version is None or not path:
        return None
    handle = wt.DWORD()
    size = version.GetFileVersionInfoSizeW(path, ctypes.byref(handle))
    if not size:
        return None
    buffer = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(path, 0, size, buffer):
        return None
    pointer = ctypes.c_void_p()
    length = wt.UINT()
    if not version.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)):
        return None

    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [
            ("dwSignature", wt.DWORD),
            ("dwStrucVersion", wt.DWORD),
            ("dwFileVersionMS", wt.DWORD),
            ("dwFileVersionLS", wt.DWORD),
            ("dwProductVersionMS", wt.DWORD),
            ("dwProductVersionLS", wt.DWORD),
            ("dwFileFlagsMask", wt.DWORD),
            ("dwFileFlags", wt.DWORD),
            ("dwFileOS", wt.DWORD),
            ("dwFileType", wt.DWORD),
            ("dwFileSubtype", wt.DWORD),
            ("dwFileDateMS", wt.DWORD),
            ("dwFileDateLS", wt.DWORD),
        ]

    info = VS_FIXEDFILEINFO.from_address(pointer.value)
    return (
        f"{info.dwFileVersionMS >> 16}.{info.dwFileVersionMS & 0xFFFF}."
        f"{info.dwFileVersionLS >> 16}.{info.dwFileVersionLS & 0xFFFF}"
    )


def branding_string(pattern: str = "%WINDOWS_LONG%") -> str | None:
    if not IS_WINDOWS or winbrand is None:
        return None
    pointer = winbrand.BrandingFormatString(pattern)
    if not pointer:
        return None
    try:
        text = ctypes.wstring_at(pointer)
    finally:
        try:
            ctypes.windll.kernel32.GlobalFree(ctypes.c_void_p(pointer))
        except Exception:
            pass
    return text or None


def smbios_table() -> bytes | None:
    """Raw SMBIOS table from the firmware (RSMB provider)."""
    if not IS_WINDOWS:
        return None
    size = kernel32.GetSystemFirmwareTable(0x52534D42, 0, None, 0)
    if not size:
        return None
    buffer = ctypes.create_string_buffer(size)
    written = kernel32.GetSystemFirmwareTable(0x52534D42, 0, buffer, size)
    if written < 8:
        return None
    return buffer.raw[:written]


def smbios_structures(data: bytes):
    """Yield ``(type, formatted_bytes, strings)`` for every SMBIOS structure."""
    if not data or len(data) < 9:
        return
    offset = 8  # RawSMBIOSData header: used, major, minor, size (dword)
    total = len(data)
    while offset + 4 <= total:
        kind = data[offset]
        length = data[offset + 1]
        if length < 4:
            return
        formatted = data[offset : offset + length]
        cursor = offset + length
        strings: list[str] = []
        if cursor + 1 < total and data[cursor] == 0 and data[cursor + 1] == 0:
            cursor += 2
        else:
            while cursor < total:
                end = data.find(b"\0", cursor)
                if end < 0:
                    return
                chunk = data[cursor:end]
                cursor = end + 1
                if not chunk:
                    break
                strings.append(chunk.decode("latin-1"))
        yield kind, formatted, strings
        if kind == 127:
            return
        offset = cursor


def smbios_string(strings: list[str], index: int) -> str | None:
    if index <= 0 or index > len(strings):
        return None
    value = strings[index - 1].strip()
    if not value:
        return None
    lowered = value.lower()
    for junk in ("to be filled", "to be set", "oem", "o.e.m.", "system product", "unknown product"):
        if lowered.startswith(junk):
            return None
    if lowered in {
        "none",
        "system name",
        "system version",
        "system sku#",
        "default string",
        "undefined",
        "not specified",
        "not applicable",
        "not defined",
        "not available",
        "invalid",
        "type1productconfigid",
        "tbd by oem",
        "no enclosure",
        "chassis version",
        "all series",
        "n/a",
        "unknown",
        "standard",
    }:
        return None
    if value.startswith("0x0") and set(value[2:]) <= {"0"}:
        return None
    return value


def cpu_topology() -> list[tuple[int, int]]:
    """Return ``[(efficiency_class, logical_count), ...]`` per physical core."""
    if not IS_WINDOWS:
        return []
    length = wt.DWORD(0)
    kernel32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(length))
    if not length.value:
        return []
    buffer = ctypes.create_string_buffer(length.value)
    if not kernel32.GetLogicalProcessorInformationEx(0, buffer, ctypes.byref(length)):
        return []
    records: list[tuple[int, int]] = []
    offset = 0
    while offset < length.value:
        header = SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX.from_buffer(buffer, offset)
        if header.Size <= 0:
            break
        if header.Relationship == 0:  # RelationProcessorCore
            core = PROCESSOR_RELATIONSHIP.from_buffer(buffer, offset + 8)
            count = 0
            for index in range(core.GroupCount):
                count += core.GroupMask[index].Mask.bit_count()
            records.append((core.EfficiencyClass, count))
        offset += header.Size
    return records


def page_size() -> int:
    if IS_WINDOWS:
        try:
            info = wt.SYSTEM_INFO()
            kernel32.GetSystemInfo(ctypes.byref(info))
            if info.dwPageSize:
                return int(info.dwPageSize)
        except Exception:
            pass
    return 4096


def process_table() -> dict[int, tuple[int, str]]:
    if not IS_WINDOWS:
        return {}
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return {}
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    table: dict[int, tuple[int, str]] = {}
    try:
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            table[int(entry.th32ProcessID)] = (int(entry.th32ParentProcessID), entry.szExeFile)
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(snapshot))
    return table


def registry_value(root, path: str, name: str | None):
    import winreg

    try:
        with winreg.OpenKey(root, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def registry_values(path: str, names: list[str], root=None) -> dict[str, object]:
    import winreg

    if root is None:
        root = winreg.HKEY_CURRENT_USER
    out: dict[str, object] = {}
    try:
        with winreg.OpenKey(root, path) as key:
            for name in names:
                try:
                    out[name] = winreg.QueryValueEx(key, name)[0]
                except OSError:
                    pass
    except OSError:
        pass
    return out


# --------------------------------------------------------------------------- #
# Memory / swap
# --------------------------------------------------------------------------- #
def memory() -> tuple[int, int] | None:
    """Return ``(total_bytes, available_bytes)``."""
    if not IS_WINDOWS:
        return None
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return int(status.ullTotalPhys), int(status.ullAvailPhys)


def performance_info() -> PERFORMANCE_INFORMATION | None:
    if not IS_WINDOWS or not hasattr(ctypes.windll, "psapi"):
        return None
    psapi = ctypes.WinDLL("psapi")
    info = PERFORMANCE_INFORMATION()
    info.cb = ctypes.sizeof(info)
    if not psapi.GetPerformanceInfo(ctypes.byref(info), info.cb):
        return None
    return info


def pagefiles() -> list[tuple[str, int, int]]:
    """Return ``[(path, used_bytes, total_bytes), ...]`` from NtQuerySystemInformation."""
    if not IS_WINDOWS or ntdll is None:
        return []
    size = wt.ULONG(65536)
    buffer = ctypes.create_string_buffer(size.value)
    status = ntdll.NtQuerySystemInformation(0x12, buffer, size.value, ctypes.byref(size))
    if status != 0:
        return []
    shift = page_size().bit_length() - 1
    out: list[tuple[str, int, int]] = []
    offset = 0
    while True:
        info = SYSTEM_PAGEFILE_INFORMATION.from_buffer(buffer, offset)
        name = ""
        if info.PageFileName.Buffer:
            name = ctypes.wstring_at(info.PageFileName.Buffer, info.PageFileName.Length // 2)
        if name.startswith("\\??\\"):
            name = name[4:]
        out.append((name, int(info.TotalInUse) << shift, int(info.TotalSize) << shift))
        if not info.NextEntryOffset:
            break
        offset += info.NextEntryOffset
    return out


# --------------------------------------------------------------------------- #
# CPU
# --------------------------------------------------------------------------- #
def max_frequency_mhz(core_count: int) -> int:
    """Highest reported MaxMhz from CallNtPowerInformation(ProcessorInformation)."""
    if not IS_WINDOWS:
        return 0
    try:
        powrprof = ctypes.WinDLL("powrprof")
    except OSError:
        return 0

    class PROCESSOR_POWER_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("Number", wt.ULONG),
            ("MaxMhz", wt.ULONG),
            ("CurrentMhz", wt.ULONG),
            ("MhzLimit", wt.ULONG),
            ("MaxIdleState", wt.ULONG),
            ("CurrentIdleState", wt.ULONG),
        ]

    count = max(core_count, 1)
    array = (PROCESSOR_POWER_INFORMATION * count)()
    status = powrprof.CallNtPowerInformation(
        11, None, 0, ctypes.byref(array), ctypes.sizeof(array)
    )
    if status != 0:
        return 0
    return max((entry.MaxMhz for entry in array), default=0)


def smbios_max_frequency_mhz(data: bytes | None) -> int:
    if not data:
        return 0
    for kind, formatted, _strings in smbios_structures(data):
        if kind == 4 and len(formatted) >= 0x18:
            return struct.unpack_from("<H", formatted, 0x14)[0]
    return 0


# --------------------------------------------------------------------------- #
# Displays
# --------------------------------------------------------------------------- #
def monitors() -> list[dict]:
    """Enumerate active display adapters with their monitors and DPI."""
    if not IS_WINDOWS:
        return []
    dpi_aware()
    results: list[dict] = []
    index = 0
    while True:
        adapter = DISPLAY_DEVICEW()
        adapter.cb = ctypes.sizeof(adapter)
        if not user32.EnumDisplayDevicesW(None, index, ctypes.byref(adapter), 0):
            break
        index += 1
        if not adapter.StateFlags & 0x1:  # DISPLAY_DEVICE_ATTACHED_TO_DESKTOP
            continue
        monitor = DISPLAY_DEVICEW()
        monitor.cb = ctypes.sizeof(monitor)
        if not user32.EnumDisplayDevicesW(
            adapter.DeviceName, 0, ctypes.byref(monitor), 0x1
        ):
            continue
        results.append(
            {
                "adapter": adapter.DeviceName,
                "adapter_name": adapter.DeviceString,
                "monitor": monitor.DeviceString,
                "monitor_id": monitor.DeviceID,
                "monitor_key": monitor.DeviceKey,
                "primary": bool(adapter.StateFlags & 0x4),
            }
        )
    return results


def monitor_dpi() -> dict[str, int]:
    """Map adapter device name (``\\\\.\\DISPLAY1``) to effective DPI."""
    if not IS_WINDOWS:
        return {}
    dpi_aware()
    mapping: dict[str, int] = {}

    def callback(hmonitor, _hdc, _rect, _data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            x = wt.UINT()
            y = wt.UINT()
            try:
                shcore.GetDpiForMonitor(hmonitor, 0, ctypes.byref(x), ctypes.byref(y))
                mapping[info.szDevice] = int(x.value or 96)
            except Exception:
                mapping[info.szDevice] = 96
        return True

    try:
        proc = ctypes.WINFUNCTYPE(
            wt.BOOL, wt.HANDLE, wt.HDC, ctypes.POINTER(RECT), wt.LPARAM
        )(callback)
        user32.EnumDisplayMonitors(None, None, proc, 0)
    except Exception:
        pass
    return mapping


def display_modes() -> dict[str, tuple[int, int, int]]:
    """Map adapter name to ``(width, height, refresh_hz)`` from the current mode."""
    if not IS_WINDOWS:
        return {}

    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", wt.WCHAR * 32),
            ("dmSpecVersion", wt.WORD),
            ("dmDriverVersion", wt.WORD),
            ("dmSize", wt.WORD),
            ("dmDriverExtra", wt.WORD),
            ("dmFields", wt.DWORD),
            ("dmPositionX", ctypes.c_long),
            ("dmPositionY", ctypes.c_long),
            ("dmDisplayOrientation", wt.DWORD),
            ("dmDisplayFixedOutput", wt.DWORD),
            ("dmColor", ctypes.c_short),
            ("dmDuplex", ctypes.c_short),
            ("dmYResolution", ctypes.c_short),
            ("dmTTOption", ctypes.c_short),
            ("dmCollate", ctypes.c_short),
            ("dmFormName", wt.WCHAR * 32),
            ("dmLogPixels", wt.WORD),
            ("dmBitsPerPel", wt.DWORD),
            ("dmPelsWidth", wt.DWORD),
            ("dmPelsHeight", wt.DWORD),
            ("dmDisplayFlags", wt.DWORD),
            ("dmDisplayFrequency", wt.DWORD),
            ("dmICMMethod", wt.DWORD),
            ("dmICMIntent", wt.DWORD),
            ("dmMediaType", wt.DWORD),
            ("dmDitherType", wt.DWORD),
            ("dmReserved1", wt.DWORD),
            ("dmReserved2", wt.DWORD),
            ("dmPanningWidth", wt.DWORD),
            ("dmPanningHeight", wt.DWORD),
        ]

    user32.EnumDisplaySettingsW.argtypes = [
        wt.LPCWSTR,
        wt.DWORD,
        ctypes.POINTER(DEVMODEW),
    ]
    user32.EnumDisplaySettingsW.restype = wt.BOOL

    out: dict[str, tuple[int, int, int]] = {}
    index = 0
    while True:
        adapter = DISPLAY_DEVICEW()
        adapter.cb = ctypes.sizeof(adapter)
        if not user32.EnumDisplayDevicesW(None, index, ctypes.byref(adapter), 0):
            break
        index += 1
        if not adapter.StateFlags & 0x1:
            continue
        mode = DEVMODEW()
        mode.dmSize = ctypes.sizeof(mode)
        if user32.EnumDisplaySettingsW(adapter.DeviceName, 0xFFFFFFFF, ctypes.byref(mode)):
            out[adapter.DeviceName] = (
                int(mode.dmPelsWidth),
                int(mode.dmPelsHeight),
                int(mode.dmDisplayFrequency),
            )
    return out


# --------------------------------------------------------------------------- #
# Displays (QueryDisplayConfig, matching fastfetch's Windows backend)
# --------------------------------------------------------------------------- #
class DISPLAYCONFIG_RATIONAL(ctypes.Structure):
    _fields_ = [("Numerator", ctypes.c_uint32), ("Denominator", ctypes.c_uint32)]


class DISPLAYCONFIG_PATH_SOURCE_INFO(ctypes.Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", ctypes.c_uint32),
        ("modeInfoIdx", ctypes.c_uint32),
        ("statusFlags", ctypes.c_uint32),
    ]


class DISPLAYCONFIG_PATH_TARGET_INFO(ctypes.Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", ctypes.c_uint32),
        ("modeInfoIdx", ctypes.c_uint32),
        ("outputTechnology", ctypes.c_uint32),
        ("rotation", ctypes.c_uint32),
        ("scaling", ctypes.c_uint32),
        ("refreshRate", DISPLAYCONFIG_RATIONAL),
        ("scanLineOrdering", ctypes.c_uint32),
        ("targetAvailable", wt.BOOL),
        ("statusFlags", ctypes.c_uint32),
    ]


class DISPLAYCONFIG_PATH_INFO(ctypes.Structure):
    _fields_ = [
        ("sourceInfo", DISPLAYCONFIG_PATH_SOURCE_INFO),
        ("targetInfo", DISPLAYCONFIG_PATH_TARGET_INFO),
        ("flags", ctypes.c_uint32),
    ]


class DISPLAYCONFIG_VIDEO_SIGNAL_INFO(ctypes.Structure):
    _fields_ = [
        ("pixelRate", ctypes.c_uint64),
        ("hSyncFreq", DISPLAYCONFIG_RATIONAL),
        ("vSyncFreq", DISPLAYCONFIG_RATIONAL),
        ("activeSize", ctypes.c_uint32 * 2),
        ("totalSize", ctypes.c_uint32 * 2),
        ("videoStandard", ctypes.c_uint32),
        ("scanLineOrdering", ctypes.c_uint32),
    ]


class DISPLAYCONFIG_SOURCE_MODE(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("pixelFormat", ctypes.c_uint32),
        ("position", wt.LONG * 2),
    ]


class _MODE_UNION(ctypes.Union):
    _fields_ = [
        ("sourceMode", DISPLAYCONFIG_SOURCE_MODE),
        ("targetMode", DISPLAYCONFIG_VIDEO_SIGNAL_INFO),
    ]


class DISPLAYCONFIG_MODE_INFO(ctypes.Structure):
    _fields_ = [
        ("infoType", ctypes.c_uint32),
        ("id", ctypes.c_uint32),
        ("adapterId", LUID),
        ("mode", _MODE_UNION),
    ]


class DISPLAYCONFIG_DEVICE_INFO_HEADER(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("size", ctypes.c_uint32),
        ("adapterId", LUID),
        ("id", ctypes.c_uint32),
    ]


class DISPLAYCONFIG_TARGET_DEVICE_NAME(ctypes.Structure):
    _fields_ = [
        ("header", DISPLAYCONFIG_DEVICE_INFO_HEADER),
        ("flags", ctypes.c_uint32),
        ("outputTechnology", ctypes.c_uint32),
        ("edidManufactureId", wt.USHORT),
        ("edidProductCodeId", wt.USHORT),
        ("connectorInstance", ctypes.c_uint32),
        ("monitorFriendlyDeviceName", wt.WCHAR * 64),
        ("monitorDevicePath", wt.WCHAR * 128),
    ]


class DISPLAYCONFIG_TARGET_PREFERRED_MODE(ctypes.Structure):
    _fields_ = [
        ("header", DISPLAYCONFIG_DEVICE_INFO_HEADER),
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("targetMode", DISPLAYCONFIG_VIDEO_SIGNAL_INFO),
    ]


_EDID_CACHE: dict[str, bytes | None] = {}


def _monitor_edid(device_path: str) -> bytes | None:
    """Read the 128-byte EDID blob for a monitor device path from the registry."""
    import winreg

    if not device_path:
        return None
    if device_path in _EDID_CACHE:
        return _EDID_CACHE[device_path]
    path = device_path[4:] if device_path.startswith("\\\\?\\") else device_path
    path = path.split("{", 1)[0].rstrip("#")
    key_path = "SYSTEM\\CurrentControlSet\\Enum\\" + path.replace("#", "\\") + "\\Device Parameters"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            data = winreg.QueryValueEx(key, "EDID")[0]
            _EDID_CACHE[device_path] = bytes(data)
            return bytes(data)
    except OSError:
        _EDID_CACHE[device_path] = None
        return None


def edid_name(edid: bytes) -> str | None:
    for offset in range(0x36, 0x7E, 0x12):
        if edid[offset] == 0 and edid[offset + 3] == 0xFC:
            chunk = edid[offset + 5 : offset + 18].split(b"\x0a", 1)[0]
            text = chunk.decode("latin-1").strip()
            if text:
                return text
    return None


def edid_physical_size(edid: bytes) -> tuple[int, int]:
    dw = ((edid[68] & 0xF0) << 4) + edid[66]
    dh = ((edid[68] & 0x0F) << 8) + edid[67]
    bw = edid[21] * 10
    bh = edid[22] * 10
    if abs(dw - bw) < 10 and abs(dh - bh) < 10:
        return dw, dh
    return bw, bh


def edid_manufacture_date(edid: bytes) -> tuple[int, int]:
    if 0 < edid[17] < 0xFF:
        week = 0 if edid[16] == 0xFF else edid[16]
        return edid[17] + 1990, week
    return 0, 0


def edid_serial(edid: bytes) -> str | None:
    for offset in (54, 72, 90, 108):
        if edid[offset] == 0 and edid[offset + 1] == 0 and edid[offset + 3] == 0xFF:
            chunk = edid[offset + 5 : offset + 18]
            for index, byte in enumerate(chunk):
                if byte in (0x0A, 0x00):
                    chunk = chunk[:index]
                    break
            text = chunk.decode("latin-1").strip()
            if text:
                return text
    return None


class DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO(ctypes.Structure):
    _fields_ = [
        ("header", DISPLAYCONFIG_DEVICE_INFO_HEADER),
        ("value", ctypes.c_uint32),
        ("colorEncoding", ctypes.c_uint32),
        ("bitsPerColorChannel", ctypes.c_uint32),
    ]


class DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO_2(ctypes.Structure):
    _fields_ = [
        ("header", DISPLAYCONFIG_DEVICE_INFO_HEADER),
        ("value", ctypes.c_uint32),
        ("colorEncoding", ctypes.c_uint32),
        ("bitsPerColorChannel", ctypes.c_uint32),
        ("activeColorMode", ctypes.c_uint32),
    ]


def _display_color_info(target) -> tuple[int, str]:
    """Return ``(bits_per_channel, hdr_status)`` for one display target."""
    if user32 is None:
        return 0, "Unknown"

    # The _2 structure is the modern query; fall back to the original one.
    info = DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO_2()
    info.header.type = 15  # DISPLAYCONFIG_DEVICE_INFO_GET_ADVANCED_COLOR_INFO_2
    info.header.size = ctypes.sizeof(info)
    info.header.adapterId = target.adapterId
    info.header.id = target.id
    if user32.DisplayConfigGetDeviceInfo(ctypes.byref(info)) == 0:
        value = info.value
        # Bit 4: highDynamicRangeSupported, bit 5: highDynamicRangeUserEnabled.
        if value & (1 << 5):
            status = "Enabled"
        elif value & (1 << 4):
            status = "Supported"
        else:
            status = "Unsupported"
        return int(info.bitsPerColorChannel), status

    legacy = DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO()
    legacy.header.type = 9  # DISPLAYCONFIG_DEVICE_INFO_GET_ADVANCED_COLOR_INFO
    legacy.header.size = ctypes.sizeof(legacy)
    legacy.header.adapterId = target.adapterId
    legacy.header.id = target.id
    if user32.DisplayConfigGetDeviceInfo(ctypes.byref(legacy)) == 0:
        value = legacy.value
        # Bit 0: advancedColorSupported, bit 1: advancedColorEnabled.
        if value & (1 << 1):
            status = "Enabled"
        elif value & (1 << 0):
            status = "Supported"
        else:
            status = "Unsupported"
        return int(legacy.bitsPerColorChannel), status

    return 0, "Unknown"


def displays() -> list[dict]:
    """Active displays with the same fields fastfetch reports."""
    if not IS_WINDOWS or user32 is None:
        return []
    dpi_aware()

    path_count = ctypes.c_uint32(0)
    mode_count = ctypes.c_uint32(0)
    if user32.GetDisplayConfigBufferSizes(
        0x2, ctypes.byref(path_count), ctypes.byref(mode_count)
    ) != 0:
        return []
    if path_count.value == 0:
        return []

    paths = (DISPLAYCONFIG_PATH_INFO * path_count.value)()
    modes = (DISPLAYCONFIG_MODE_INFO * mode_count.value)()
    if (
        user32.QueryDisplayConfig(
            0x2,
            ctypes.byref(path_count),
            paths,
            ctypes.byref(mode_count),
            modes,
            None,
        )
        != 0
    ):
        return []

    out: list[dict] = []
    for path in paths[: path_count.value]:
        index = path.sourceInfo.modeInfoIdx
        source = None
        if index < mode_count.value:
            source = modes[index].mode.sourceMode
        if source is None or not source.width:
            continue

        target_name = DISPLAYCONFIG_TARGET_DEVICE_NAME()
        target_name.header.type = 2  # DISPLAYCONFIG_DEVICE_INFO_GET_TARGET_NAME
        target_name.header.size = ctypes.sizeof(target_name)
        target_name.header.adapterId = path.targetInfo.adapterId
        target_name.header.id = path.targetInfo.id
        if user32.DisplayConfigGetDeviceInfo(ctypes.byref(target_name)) != 0:
            continue

        name = None
        physical = (0, 0)
        edid = _monitor_edid(target_name.monitorDevicePath)
        if edid and len(edid) >= 128:
            name = edid_name(edid)
            physical = edid_physical_size(edid)
        if not name:
            if target_name.flags & 0x1:  # friendlyNameFromEdid
                name = target_name.monitorFriendlyDeviceName
            else:
                parts = target_name.monitorDevicePath.split("#")
                name = parts[1] if len(parts) > 1 else target_name.monitorDevicePath

        width, height = int(source.width), int(source.height)
        rotation = {1: 0, 2: 90, 3: 180, 4: 270}.get(path.targetInfo.rotation, 0)
        if rotation in (90, 270):
            width, height = height, width

        refresh = 0.0
        if path.targetInfo.refreshRate.Denominator:
            refresh = path.targetInfo.refreshRate.Numerator / path.targetInfo.refreshRate.Denominator

        dpi = 96
        monitor_id = 0
        try:
            point = wt.POINT(int(source.position[0]), int(source.position[1]))
            monitor = user32.MonitorFromPoint(point, 0)
            if monitor:
                monitor_id = int(monitor)
                x = wt.UINT()
                y = wt.UINT()
                if shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(x), ctypes.byref(y)) == 0:
                    dpi = int(x.value or 96)
        except Exception:
            pass

        bit_depth, hdr_status = _display_color_info(path.targetInfo)

        preferred = DISPLAYCONFIG_TARGET_PREFERRED_MODE()
        preferred.header.type = 3  # DISPLAYCONFIG_DEVICE_INFO_GET_TARGET_PREFERRED_MODE
        preferred.header.size = ctypes.sizeof(preferred)
        preferred.header.adapterId = path.targetInfo.adapterId
        preferred.header.id = path.targetInfo.id
        preferred_width = preferred_height = 0
        preferred_refresh = 0.0
        if user32.DisplayConfigGetDeviceInfo(ctypes.byref(preferred)) == 0:
            preferred_width = int(preferred.width)
            preferred_height = int(preferred.height)
            rational = preferred.targetMode.vSyncFreq
            if rational.Denominator:
                preferred_refresh = rational.Numerator / rational.Denominator

        output = path.targetInfo.outputTechnology
        if output == 0xFFFFFFFF:  # OUTPUT_TECHNOLOGY_OTHER
            display_type = "Unknown"
        elif output in (0x80000000, 0x80000001, 0x80000002):  # INTERNAL / DP_EMBEDDED / UDI_EMBEDDED
            display_type = "Built-in"
        else:
            display_type = "External"

        year, week = edid_manufacture_date(edid) if edid and len(edid) >= 128 else (0, 0)
        out.append(
            {
                "id": monitor_id,
                "name": name or "",
                "width": width,
                "height": height,
                "refreshRate": refresh,
                "dpi": dpi,
                "preferredWidth": preferred_width,
                "preferredHeight": preferred_height,
                "preferredRefreshRate": preferred_refresh,
                "physicalWidth": physical[0],
                "physicalHeight": physical[1],
                "rotation": rotation,
                "bitDepth": bit_depth,
                "hdrStatus": hdr_status,
                "drrStatus": "Enabled" if path.flags & 0x10 else "Disabled",
                "type": display_type,
                "primary": source.position[0] == 0 and source.position[1] == 0,
                "manufactureYear": year,
                "manufactureWeek": week,
                "serial": edid_serial(edid) if edid and len(edid) >= 128 else None,
                "platformApi": "GDI",
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Network
# --------------------------------------------------------------------------- #
def adapters() -> list[dict]:
    """Return connected IPv4 adapters (friendly name, address, prefix, speed, mtu)."""
    if not IS_WINDOWS or iphlpapi is None:
        return []
    import socket

    flags = 0x2 | 0x4 | 0x8  # skip anycast / multicast / dns servers
    size = wt.ULONG(32768)
    buffer = ctypes.create_string_buffer(size.value)
    status = iphlpapi.GetAdaptersAddresses(0, flags, None, buffer, ctypes.byref(size))
    if status != 0:
        return []
    out: list[dict] = []
    node = ctypes.cast(buffer, ctypes.POINTER(IP_ADAPTER_ADDRESSES))
    while node:
        adapter = node.contents
        if adapter.OperStatus == 1:  # IfOperStatusUp
            addresses = []
            unicast = adapter.FirstUnicastAddress
            while unicast:
                sockaddr = unicast.contents.Address.lpSockaddr
                if sockaddr and sockaddr.contents.sa_family == socket.AF_INET:
                    raw = bytes(sockaddr.contents.sa_data[2:6])
                    addresses.append(
                        (socket.inet_ntoa(raw), int(unicast.contents.OnLinkPrefixLength))
                    )
                unicast = unicast.contents.Next
            if addresses:
                out.append(
                    {
                        "name": adapter.FriendlyName or "",
                        "description": adapter.Description or "",
                        "addresses": addresses,
                        "speed": int(adapter.TransmitLinkSpeed or 0),
                        "mtu": int(adapter.Mtu or 0),
                        "ifindex": int(adapter.IfIndex),
                        "iftype": int(adapter.IfType),
                        "mac": ":".join(
                            f"{byte:02X}"
                            for byte in adapter.PhysicalAddress[: adapter.PhysicalAddressLength]
                        ),
                    }
                )
        node = adapter.Next
    return out


def default_route_ipv4() -> int | None:
    """Index of the interface that would be used to reach the internet."""
    if not IS_WINDOWS or iphlpapi is None:
        return None
    index = wt.DWORD()
    status = iphlpapi.GetBestInterface(0x08080808, ctypes.byref(index))
    return int(index.value) if status == 0 else None


# --------------------------------------------------------------------------- #
# GPU
# --------------------------------------------------------------------------- #
class DXGI_ADAPTER_DESC1(ctypes.Structure):
    _fields_ = [
        ("Description", wt.WCHAR * 128),
        ("VendorId", ctypes.c_uint32),
        ("DeviceId", ctypes.c_uint32),
        ("SubSysId", ctypes.c_uint32),
        ("Revision", ctypes.c_uint32),
        ("DedicatedVideoMemory", ctypes.c_size_t),
        ("DedicatedSystemMemory", ctypes.c_size_t),
        ("SharedSystemMemory", ctypes.c_size_t),
        ("AdapterLuid", LUID),
        ("Flags", ctypes.c_uint32),
    ]


def _com_call(obj, index: int, restype, *argtypes):
    table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    prototype = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return prototype(table[index])


def dxgi_adapters() -> list[DXGI_ADAPTER_DESC1]:
    """Enumerate hardware adapters through DXGI (skips the software renderer)."""
    if not IS_WINDOWS or dxgi is None:
        return []
    iid = GUID(
        0x770AAE78,
        0xF26F,
        0x4DBA,
        (ctypes.c_ubyte * 8)(0xA8, 0x29, 0x25, 0x3C, 0x83, 0xD1, 0xB3, 0x87),
    )
    factory = ctypes.c_void_p()
    if dxgi.CreateDXGIFactory1(ctypes.byref(iid), ctypes.byref(factory)) != 0:
        return []
    enum_adapters = _com_call(factory, 12, ctypes.c_long, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p))
    get_desc = _com_call(factory, 10, ctypes.c_long, ctypes.POINTER(DXGI_ADAPTER_DESC1))
    out: list[DXGI_ADAPTER_DESC1] = []
    index = 0
    while True:
        adapter = ctypes.c_void_p()
        if enum_adapters(factory, index, ctypes.byref(adapter)) != 0:
            break
        index += 1
        desc = DXGI_ADAPTER_DESC1()
        desc_fn = _com_call(adapter, 10, ctypes.c_long, ctypes.POINTER(DXGI_ADAPTER_DESC1))
        if desc_fn(adapter, ctypes.byref(desc)) != 0:
            continue
        if desc.Flags & 0x2:  # DXGI_ADAPTER_FLAG_SOFTWARE
            continue
        out.append(desc)
    del get_desc
    return out


def gpu_driver_version(device_key: str) -> str | None:
    """Driver version from the display adapter's registry key."""
    if not device_key:
        return None
    import winreg

    for name in ("DriverVersion",):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, device_key) as key:
                value = winreg.QueryValueEx(key, name)[0]
                return str(value)
        except OSError:
            return None
    return None


# --------------------------------------------------------------------------- #
# Battery
# --------------------------------------------------------------------------- #
def battery_present() -> bool:
    if not IS_WINDOWS:
        return False
    status = SYSTEM_POWER_STATUS()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return False
    return status.BatteryFlag not in (128, 255) and status.BatteryLifePercent != 255


def power_status() -> SYSTEM_POWER_STATUS | None:
    if not IS_WINDOWS:
        return None
    status = SYSTEM_POWER_STATUS()
    if not kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None
    return status


def _battery_handles() -> list[ctypes.c_void_p]:
    if not IS_WINDOWS:
        return []

    class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wt.DWORD),
            ("InterfaceClassGuid", ctypes.c_ubyte * 16),
            ("Flags", wt.DWORD),
            ("Reserved", ctypes.c_size_t),
        ]

    class SP_DEVICE_INTERFACE_DETAIL_DATA_W(ctypes.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("DevicePath", wt.WCHAR * 1)]

    guid = GUID.from_string("{72631e54-78a4-11d0-bcf7-00aa00b7b32a}")
    hdev = setupapi.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, 0x12)
    if not hdev or hdev == ctypes.c_void_p(-1).value:
        return []
    handles: list[ctypes.c_void_p] = []
    index = 0
    try:
        while True:
            iface = SP_DEVICE_INTERFACE_DATA()
            iface.cbSize = ctypes.sizeof(iface)
            if not setupapi.SetupDiEnumDeviceInterfaces(
                hdev, None, ctypes.byref(guid), index, ctypes.byref(iface)
            ):
                break
            index += 1
            needed = wt.DWORD()
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                hdev, ctypes.byref(iface), None, 0, ctypes.byref(needed), None
            )
            if not needed.value:
                continue
            buffer = ctypes.create_string_buffer(needed.value)
            ctypes.c_uint32.from_buffer(buffer).value = (
                8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            )
            if not setupapi.SetupDiGetDeviceInterfaceDetailW(
                hdev, ctypes.byref(iface), buffer, needed.value, ctypes.byref(needed), None
            ):
                continue
            path = ctypes.wstring_at(ctypes.addressof(buffer) + 4)
            handle = kernel32.CreateFileW(path, 0xC0000000, 3, None, 3, 0, None)
            if handle and handle != ctypes.c_void_p(-1).value:
                handles.append(handle)
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)
    return handles


def battery_state() -> dict | None:
    """SYSTEM_BATTERY_STATE via NtPowerInformation (summary, all batteries)."""
    if not IS_WINDOWS or ntdll is None:
        return None
    try:
        powrprof = ctypes.WinDLL("powrprof")
    except OSError:
        return None

    class SYSTEM_BATTERY_STATE(ctypes.Structure):
        _fields_ = [
            ("AcOnLine", ctypes.c_ubyte),
            ("BatteryPresent", ctypes.c_ubyte),
            ("Charging", ctypes.c_ubyte),
            ("Discharging", ctypes.c_ubyte),
            ("Spare1", ctypes.c_ubyte * 3),
            ("MaxCapacity", wt.ULONG),
            ("RemainingCapacity", wt.ULONG),
            ("Rate", wt.ULONG),
            ("EstimatedTime", wt.ULONG),
            ("DefaultAlert1", wt.ULONG),
            ("DefaultAlert2", wt.ULONG),
        ]

    state = SYSTEM_BATTERY_STATE()
    status = powrprof.CallNtPowerInformation(
        5, None, 0, ctypes.byref(state), ctypes.sizeof(state)
    )
    if status != 0 or not state.BatteryPresent:
        return None
    return {
        "ac_online": bool(state.AcOnLine),
        "charging": bool(state.Charging),
        "discharging": bool(state.Discharging),
        "max_capacity": int(state.MaxCapacity),
        "remaining_capacity": int(state.RemainingCapacity),
        "rate": int(state.Rate),
        "estimated_time": int(state.EstimatedTime),
        "alert1": int(state.DefaultAlert1),
    }


def batteries() -> list[dict]:
    """Read battery details through SetupAPI + IOCTL (fast, no WMI)."""
    if not IS_WINDOWS:
        return []
    out: list[dict] = []
    for handle in _battery_handles():
        try:
            tag = wt.ULONG()
            returned = wt.DWORD()
            if not kernel32.DeviceIoControl(
                handle, 0x294040, None, 0, ctypes.byref(tag), 4, ctypes.byref(returned), None
            ):
                continue
            entry: dict = {"tag": int(tag.value)}

            def query_text(level: int) -> str | None:
                request = BATTERY_QUERY_INFORMATION(tag.value, level, 0)
                buffer = ctypes.create_unicode_buffer(256)
                if kernel32.DeviceIoControl(
                    handle,
                    0x294044,
                    ctypes.byref(request),
                    ctypes.sizeof(request),
                    buffer,
                    ctypes.sizeof(buffer),
                    ctypes.byref(returned),
                    None,
                ):
                    return buffer.value or None
                return None

            entry["name"] = query_text(4)  # BATTERY_DEVICE_NAME
            entry["manufacturer"] = query_text(6)  # BATTERY_MANUFACTURE_NAME
            entry["serial"] = query_text(8)  # BATTERY_SERIAL_NUMBER

            request = BATTERY_QUERY_INFORMATION(tag.value, 0, 0)
            info = BATTERY_INFORMATION()
            if kernel32.DeviceIoControl(
                handle,
                0x294044,
                ctypes.byref(request),
                ctypes.sizeof(request),
                ctypes.byref(info),
                ctypes.sizeof(info),
                ctypes.byref(returned),
                None,
            ):
                entry["chemistry"] = info.Chemistry.decode("latin-1", "replace").strip("\0")
                entry["full_charge"] = int(info.FullChargedCapacity)
                entry["designed"] = int(info.DesignedCapacity)
                entry["cycle_count"] = int(info.CycleCount)
                entry["technology"] = int(info.Technology)
                entry["capabilities"] = int(info.Capabilities)

            request = BATTERY_QUERY_INFORMATION(tag.value, 1, 0)
            status = BATTERY_STATUS()
            if kernel32.DeviceIoControl(
                handle,
                0x294044,
                ctypes.byref(request),
                ctypes.sizeof(request),
                ctypes.byref(status),
                ctypes.sizeof(status),
                ctypes.byref(returned),
                None,
            ):
                entry["power_state"] = int(status.PowerState)
                entry["capacity_mwh"] = int(status.Capacity)
                entry["rate"] = int(status.Rate)
            out.append(entry)
        finally:
            kernel32.CloseHandle(handle)
    return out



# --------------------------------------------------------------------------- #
# D3DKMT GPU enumeration (matches fastfetch's Windows backend)
# --------------------------------------------------------------------------- #
gdi32 = _load("gdi32")


class D3DKMT_ADAPTERINFO(ctypes.Structure):
    _fields_ = [
        ("hAdapter", ctypes.c_uint32),
        ("AdapterLuid", LUID),
        ("NumOfSources", wt.ULONG),
        ("bPrecisePresentRegionsPreferred", wt.BOOL),
    ]


class D3DKMT_ENUMADAPTERS2(ctypes.Structure):
    _fields_ = [
        ("NumAdapters", wt.ULONG),
        ("pAdapters", ctypes.POINTER(D3DKMT_ADAPTERINFO)),
    ]


class D3DKMT_QUERYADAPTERINFO(ctypes.Structure):
    _fields_ = [
        ("hAdapter", ctypes.c_uint32),
        ("Type", ctypes.c_int),
        ("pPrivateDriverData", ctypes.c_void_p),
        ("PrivateDriverDataSize", ctypes.c_uint32),
    ]


class D3DKMT_ADAPTERREGISTRYINFO(ctypes.Structure):
    _fields_ = [
        ("AdapterString", wt.WCHAR * 260),
        ("BiosString", wt.WCHAR * 260),
        ("DacType", wt.WCHAR * 260),
        ("ChipType", wt.WCHAR * 260),
    ]


class D3DKMT_SEGMENTSIZEINFO(ctypes.Structure):
    _fields_ = [
        ("DedicatedVideoMemorySize", ctypes.c_uint64),
        ("DedicatedSystemMemorySize", ctypes.c_uint64),
        ("SharedSystemMemorySize", ctypes.c_uint64),
    ]


class D3DKMT_UMD_DRIVER_VERSION(ctypes.Structure):
    _fields_ = [("DriverVersion", ctypes.c_uint64)]


class D3DKMT_ADAPTERADDRESS(ctypes.Structure):
    _fields_ = [
        ("BusNumber", ctypes.c_uint32),
        ("DeviceNumber", ctypes.c_uint32),
        ("FunctionNumber", ctypes.c_uint32),
    ]


class D3DKMT_DEVICE_IDS(ctypes.Structure):
    _fields_ = [
        ("VendorID", ctypes.c_uint32),
        ("DeviceID", ctypes.c_uint32),
        ("SubVendorID", ctypes.c_uint32),
        ("SubSystemID", ctypes.c_uint32),
        ("RevisionID", ctypes.c_uint32),
        ("BusType", ctypes.c_uint32),
    ]


class D3DKMT_QUERY_DEVICE_IDS(ctypes.Structure):
    _fields_ = [
        ("PhysicalAdapterIndex", ctypes.c_uint32),
        ("DeviceIds", D3DKMT_DEVICE_IDS),
    ]


if IS_WINDOWS and gdi32 is not None:
    gdi32.D3DKMTEnumAdapters2.argtypes = [ctypes.POINTER(D3DKMT_ENUMADAPTERS2)]
    gdi32.D3DKMTEnumAdapters2.restype = ctypes.c_long
    gdi32.D3DKMTQueryAdapterInfo.argtypes = [ctypes.POINTER(D3DKMT_QUERYADAPTERINFO)]
    gdi32.D3DKMTQueryAdapterInfo.restype = ctypes.c_long

GPU_VENDORS = {
    0x106B: "Apple",
    0x1002: "AMD",
    0x1022: "AMD",
    0x1DD8: "AMD",
    0x8086: "Intel",
    0x8087: "Intel",
    0x03E7: "Intel",
    0x0955: "NVIDIA",
    0x10DE: "NVIDIA",
    0x12D2: "NVIDIA",
    0x1ED5: "Moore Threads",
    0x17CB: "Qualcomm",
    0x5143: "Qualcomm",
    0x14C3: "MediaTek",
    0x15AD: "VMware",
    0x1AF4: "Red Hat",
    0x1AB8: "Parallels",
    0x1414: "Microsoft",
    0x108E: "Oracle",
    0x182F: "Broadcom",
    0x14E4: "Broadcom",
    0x0014: "Loongson",
}


def _d3dkmt_query(handle: int, kind: int, structure):
    request = D3DKMT_QUERYADAPTERINFO(
        handle,
        kind,
        ctypes.cast(ctypes.byref(structure), ctypes.c_void_p),
        ctypes.sizeof(structure),
    )
    return gdi32.D3DKMTQueryAdapterInfo(ctypes.byref(request))


def gpus() -> list[dict]:
    """Enumerate hardware adapters through D3DKMT, fastfetch style."""
    if not IS_WINDOWS or gdi32 is None:
        return []
    adapters = (D3DKMT_ADAPTERINFO * 64)()
    enum = D3DKMT_ENUMADAPTERS2(64, adapters)
    if gdi32.D3DKMTEnumAdapters2(ctypes.byref(enum)) != 0:
        return []

    out: list[dict] = []
    for index in range(enum.NumAdapters):
        adapter = adapters[index]
        adapter_type = ctypes.c_uint32(0)
        if _d3dkmt_query(adapter.hAdapter, 15, adapter_type) != 0:  # KMTQAITYPE_ADAPTERTYPE
            continue
        flags = adapter_type.value
        if flags & (1 << 2):  # SoftwareDevice
            continue

        platform_api = "WDDM"
        wddm = ctypes.c_uint32(0)
        if _d3dkmt_query(adapter.hAdapter, 13, wddm) == 0:  # KMTQAITYPE_DRIVERVERSION
            platform_api = f"WDDM {wddm.value // 1000}.{(wddm.value % 1000) // 100}"

        address = D3DKMT_ADAPTERADDRESS()
        if _d3dkmt_query(adapter.hAdapter, 6, address) == 0 and address.FunctionNumber != 0xFFFF:
            device_id = (
                (int(address.BusNumber) << 8)
                | (int(address.DeviceNumber) << 3)
                | int(address.FunctionNumber)
            )
        else:
            device_id = (
                (int(adapter.AdapterLuid.HighPart) << 32) | int(adapter.AdapterLuid.LowPart)
            ) & 0xFFFFFFFF

        ids = D3DKMT_QUERY_DEVICE_IDS()
        vendor = ""
        if _d3dkmt_query(adapter.hAdapter, 31, ids) == 0:  # KMTQAITYPE_PHYSICALADAPTERDEVICEIDS
            vendor = GPU_VENDORS.get(int(ids.DeviceIds.VendorID), "")

        driver = None
        umd = D3DKMT_UMD_DRIVER_VERSION()
        if _d3dkmt_query(adapter.hAdapter, 18, umd) == 0:  # KMTQAITYPE_UMD_DRIVER_VERSION
            raw = int(umd.DriverVersion)
            driver = ".".join(str((raw >> shift) & 0xFFFF) for shift in (48, 32, 16, 0))

        name = ""
        registry_info = D3DKMT_ADAPTERREGISTRYINFO()
        if _d3dkmt_query(adapter.hAdapter, 8, registry_info) == 0:  # KMTQAITYPE_ADAPTERREGISTRYINFO
            name = registry_info.AdapterString or ""

        segments = D3DKMT_SEGMENTSIZEINFO()
        dedicated = shared = None
        if _d3dkmt_query(adapter.hAdapter, 3, segments) == 0:  # KMTQAITYPE_GETSEGMENTSIZE
            dedicated = int(segments.DedicatedVideoMemorySize)
            shared = int(segments.DedicatedSystemMemorySize + segments.SharedSystemMemorySize)

        if flags & (1 << 5):  # HybridIntegrated
            gpu_type = "Integrated"
        elif flags & (1 << 4):  # HybridDiscrete
            gpu_type = "Discrete"
        else:
            gpu_type = "Unknown"

        out.append(
            {
                "index": None,
                "coreCount": None,
                "coreUsage": None,
                "memory": {
                    "dedicated": {"total": dedicated, "used": None},
                    "shared": {"total": shared, "used": None},
                    "type": None,
                },
                "driver": driver,
                "name": name,
                "temperature": None,
                "type": gpu_type,
                "vendor": vendor,
                "platformApi": platform_api,
                "frequency": None,
                "deviceId": device_id,
                "pcieSpeed": None,
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Disks
# --------------------------------------------------------------------------- #
if IS_WINDOWS and kernel32 is not None:
    _prototype(kernel32, "QueryDosDeviceW", wt.DWORD, [wt.LPCWSTR, wt.LPWSTR, wt.DWORD])


def _volume_creation_time(handle: int) -> int | None:
    """Volume creation time in unix milliseconds (FILE_FS_VOLUME_INFORMATION)."""
    if ntdll is None:
        return None
    _prototype(
        ntdll,
        "NtQueryVolumeInformationFile",
        ctypes.c_long,
        [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.c_int],
    )
    buffer = ctypes.create_string_buffer(1024)
    status_block = ctypes.create_string_buffer(32)
    if ntdll.NtQueryVolumeInformationFile(handle, status_block, buffer, len(buffer), 1) != 0:
        return None
    stamp = int.from_bytes(buffer.raw[:8], "little")
    if not stamp:
        return None
    return (stamp - 116444736000000000) // 10000


def disks() -> list[dict]:
    """Mounted volumes with fastfetch's disk result shape."""
    if not IS_WINDOWS:
        return []
    mask = int(kernel32.GetLogicalDrives())
    out: list[dict] = []
    for offset in range(26):
        if not mask & (1 << offset):
            continue
        root = f"{chr(ord('A') + offset)}:\\"
        drive_type = int(kernel32.GetDriveTypeW(root))
        if drive_type == 1:  # DRIVE_NO_ROOT_DIR
            continue

        free = ctypes.c_ulonglong()
        total = ctypes.c_ulonglong()
        if not kernel32.GetDiskFreeSpaceExW(root, ctypes.byref(free), ctypes.byref(total), None):
            continue

        label = ctypes.create_unicode_buffer(261)
        filesystem = ctypes.create_unicode_buffer(261)
        if not kernel32.GetVolumeInformationW(
            root, label, len(label), None, None, None, filesystem, len(filesystem)
        ):
            continue

        device = ctypes.create_unicode_buffer(261)
        mount_from = ""
        if kernel32.QueryDosDeviceW(root[:2], device, len(device)):
            mount_from = device.value

        create_time = None
        handle = kernel32.CreateFileW(
            root, 0x80, 3, None, 3, 0x02000000, None  # FILE_READ_ATTRIBUTES, backup semantics
        )
        if handle and handle != ctypes.c_void_p(-1).value:
            try:
                create_time = _volume_creation_time(handle)
            finally:
                kernel32.CloseHandle(handle)

        if drive_type in (2, 4, 5):  # removable / remote / cdrom
            volume_type = ["External"]
        elif drive_type == 3:  # fixed
            volume_type = ["Regular"]
        else:
            volume_type = ["Hidden"]

        out.append(
            {
                "bytes": {
                    "available": int(free.value),
                    "free": int(free.value),
                    "total": int(total.value),
                    "used": int(total.value) - int(free.value),
                },
                "files": {"total": None, "used": None},
                "filesystem": filesystem.value,
                "mountpoint": root,
                "mountFrom": mount_from,
                "name": label.value,
                "volumeType": volume_type,
                "createTime": create_time,
            }
        )
    return out


# --------------------------------------------------------------------------- #
# Shell / terminal
# --------------------------------------------------------------------------- #
SHELL_SKIP = {
    "sudo",
    "su",
    "gdb",
    "lldb",
    "lldb-dap",
    "python",
    "python3",
    "py",
    "fastfetch",
    "flashfetch",
    "sysfetch",
    "cmd-shim",
    "shim",
}

SHELL_NAMES = {
    "pwsh": "PowerShell",
    "powershell": "Windows PowerShell",
    "powershell_ise": "Windows PowerShell ISE",
    "cmd": "CMD",
    "nu": "nushell",
    "explorer": "Windows Explorer",
    "busybox": "ash",
}

if IS_WINDOWS and kernel32 is not None:
    _prototype(kernel32, "OpenProcess", ctypes.c_void_p, [wt.DWORD, wt.BOOL, wt.DWORD])
    _prototype(
        kernel32,
        "QueryFullProcessImageNameW",
        wt.BOOL,
        [ctypes.c_void_p, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)],
    )


def _strip_exe(name: str) -> str:
    return name[:-4] if name.lower().endswith(".exe") else name


def _process_exe(pid: int) -> str | None:
    if not IS_WINDOWS or kernel32 is None:
        return None
    process = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not process:
        return None
    try:
        size = wt.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value
    finally:
        kernel32.CloseHandle(process)


def _shell_version(exe: str, name: str) -> str | None:
    import re
    import subprocess

    pretty = name.lower()
    commands = {
        "bash": ["--version"],
        "zsh": ["--version"],
        "fish": ["--version"],
        "dash": ["-c", "echo $DASH_VERSION"],
        "ksh": ["--version"],
        "pwsh": ["-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        "powershell": ["-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        "nu": ["--version"],
        "elvish": ["-version"],
        "xonsh": ["--version"],
        "sh": ["--version"],
        "cmd": [],
    }
    arguments = commands.get(pretty)
    if not exe or arguments is None:
        return None
    try:
        result = subprocess.run(
            [exe, *arguments],
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = (result.stdout or "") + (result.stderr or "")
    if pretty == "cmd":
        match = re.search(r"Version ([\d.]+)", text)
        return match.group(1) if match else None
    match = re.search(r"(\d+\.\d+(?:\.\d+)?(?:[-.\w]+)?)", text)
    return match.group(1) if match else None


def shell_info() -> dict | None:
    """Current shell, resolved by walking the process tree like fastfetch."""
    if not IS_WINDOWS:
        return None
    table = process_table()
    pid = os.getpid()
    seen: set[int] = set()
    process_name = ""
    exe_path = ""
    ppid = 0
    while pid and pid not in seen:
        seen.add(pid)
        entry = table.get(pid)
        if entry is None:
            break
        parent, exe_name = entry
        pretty = _strip_exe(exe_name)
        lowered = pretty.lower()
        if lowered in SHELL_SKIP or "debug" in lowered or lowered.startswith("conemuc"):
            pid = parent
            continue
        process_name = exe_name
        exe_path = _process_exe(pid) or ""
        ppid = parent
        break
    if not process_name:
        return None
    pretty = SHELL_NAMES.get(_strip_exe(process_name).lower(), _strip_exe(process_name))
    version = _shell_version(exe_path, pretty) or ""
    return {
        "exe": exe_path,
        "exeName": process_name,
        "exePath": exe_path,
        "pid": pid,
        "ppid": ppid,
        "processName": process_name,
        "prettyName": pretty,
        "version": version,
        "tty": None,
    }


TERMINAL_ENV = (
    ("WT_SESSION", "WindowsTerminal", "Windows Terminal"),
    ("WT_PROFILE_ID", "WindowsTerminal", "Windows Terminal"),
    ("ALACRITTY_SOCKET", "alacritty", "Alacritty"),
    ("ALACRITTY_LOG", "alacritty", "Alacritty"),
    ("ALACRITTY_WINDOW_ID", "alacritty", "Alacritty"),
    ("WEZTERM_EXECUTABLE", "wezterm-gui", "WezTerm"),
    ("KITTY_WINDOW_ID", "kitty", "kitty"),
    ("TERMINUS_SUBLIME", "terminus", "Terminus"),
    ("VSCode", "code", "Visual Studio Code"),
    ("HYPER", "hyper", "Hyper"),
    ("TABBY_CONFIG_DIRECTORY", "tabby", "Tabby"),
)


def terminal_info() -> dict | None:
    for variable, process, pretty in TERMINAL_ENV:
        if os.environ.get(variable):
            return {
                "processName": process,
                "exe": process,
                "exeName": "",
                "exePath": "",
                "pid": 0,
                "ppid": 0,
                "prettyName": pretty,
                "version": "",
                "tty": "",
            }
    if os.environ.get("ConEmuPID"):
        return {
            "processName": "ConEmu",
            "exe": "ConEmu",
            "exeName": "",
            "exePath": "",
            "pid": int(os.environ["ConEmuPID"] or 0),
            "ppid": 0,
            "prettyName": "ConEmu",
            "version": "",
            "tty": "",
        }
    if os.environ.get("SSH_CONNECTION"):
        return {
            "processName": "sshd",
            "exe": "sshd",
            "exeName": "",
            "exePath": "",
            "pid": 0,
            "ppid": 0,
            "prettyName": "SSH",
            "version": "",
            "tty": os.environ.get("SSH_TTY", ""),
        }
    return None


# --------------------------------------------------------------------------- #
# Host / OS / kernel / CPU / locale / uptime
# --------------------------------------------------------------------------- #
def _smbios_structure(data: bytes | None, kind: int):
    if not data:
        return None, []
    for entry_kind, formatted, strings in smbios_structures(data):
        if entry_kind == kind:
            return formatted, strings
    return None, []


def host_info() -> dict | None:
    data = smbios_table()
    formatted, strings = _smbios_structure(data, 1)
    if not formatted or len(formatted) < 0x1B:
        return None

    def string_at(offset: int) -> str:
        if offset >= len(formatted):
            return ""
        return smbios_string(strings, formatted[offset]) or ""

    uuid_text = ""
    if len(formatted) >= 0x19:
        raw = formatted[0x08:0x18]
        uuid_text = (
            f"{int.from_bytes(raw[0:4], 'little'):08X}-"
            f"{int.from_bytes(raw[4:6], 'little'):04X}-"
            f"{int.from_bytes(raw[6:8], 'little'):04X}-"
            f"{raw[8]:02X}{raw[9]:02X}-"
            f"{raw[10]:02X}{raw[11]:02X}{raw[12]:02X}{raw[13]:02X}{raw[14]:02X}{raw[15]:02X}"
        )

    return {
        "family": string_at(0x1A) if len(formatted) > 0x1A else "",
        "name": string_at(0x05),
        "version": string_at(0x06),
        "sku": string_at(0x19) if len(formatted) > 0x19 else "",
        "vendor": string_at(0x04),
        "serial": string_at(0x07),
        "uuid": uuid_text,
    }


def os_info() -> dict:
    import winreg

    raw = branding_string("%WINDOWS_LONG%") or ""
    if raw.startswith("Microsoft "):
        raw = raw[len("Microsoft "):]
    path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    if not raw:
        raw = registry_value(winreg.HKEY_LOCAL_MACHINE, path, "ProductName") or "Windows"

    pretty = raw.strip()
    name = "Windows"
    version = ""
    variant = pretty
    if pretty.startswith("Windows "):
        rest = pretty[len("Windows "):]
        if rest.startswith("Server "):
            name = "Windows Server"
            rest = rest[len("Server "):]
        elif rest.startswith("Embedded "):
            name = "Windows Embedded"
            rest = rest[len("Embedded "):]
        if rest.lower().startswith("(tm) "):
            rest = rest[5:]
        head, _, tail = rest.partition(" ")
        version = head
        variant = tail

    codename = (
        registry_value(winreg.HKEY_LOCAL_MACHINE, path, "DisplayVersion")
        or registry_value(winreg.HKEY_LOCAL_MACHINE, path, "ReleaseId")
        or ""
    )
    if codename:
        pretty = f"{pretty} ({codename})"

    return {
        "buildID": "",
        "codename": codename,
        "id": f"{name} {version}".strip(),
        "idLike": "Windows",
        "name": name,
        "prettyName": pretty,
        "variant": variant,
        "variantID": "",
        "version": version,
        "versionID": "",
    }


def kernel_info() -> dict:
    import platform
    import winreg

    path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    ubr = registry_value(winreg.HKEY_LOCAL_MACHINE, path, "UBR") or 0
    build_lab = registry_value(winreg.HKEY_LOCAL_MACHINE, path, "BuildLabEx") or ""
    release = platform.version()  # e.g. 10.0.26100
    machine = platform.machine()
    return {
        "architecture": "x86_64" if machine.endswith("64") else machine,
        "name": "WIN32_NT",
        "release": f"{release}.{ubr}",
        "version": build_lab,
        "pageSize": page_size(),
    }


def numa_nodes() -> int:
    if not IS_WINDOWS:
        return 0
    length = wt.DWORD(0)
    kernel32.GetLogicalProcessorInformationEx(1, None, ctypes.byref(length))
    if not length.value:
        return 0
    buffer = ctypes.create_string_buffer(length.value)
    if not kernel32.GetLogicalProcessorInformationEx(1, buffer, ctypes.byref(length)):
        return 0
    count = 0
    offset = 0
    while offset < length.value:
        header = SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX.from_buffer(buffer, offset)
        if header.Size <= 0:
            break
        if header.Relationship == 1:  # RelationNumaNode
            count += 1
        offset += header.Size
    return count


def cpu_info() -> dict | None:
    import platform
    import winreg

    path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    name = registry_value(winreg.HKEY_LOCAL_MACHINE, path, "ProcessorNameString") or ""
    vendor = registry_value(winreg.HKEY_LOCAL_MACHINE, path, "VendorIdentifier") or ""
    if not name and not vendor:
        return None

    topology = cpu_topology()
    core_types: list[dict] = []
    for efficiency, count in topology:
        bucket = efficiency + 1
        for entry in core_types:
            if entry["freq"] == bucket:
                entry["count"] += count
                break
        else:
            core_types.append({"count": count, "freq": bucket})
    core_types.sort(key=lambda entry: -entry["freq"])

    logical = os.cpu_count() or len(topology) or 1
    base = int(registry_value(winreg.HKEY_LOCAL_MACHINE, path, "~MHz") or 0)
    maximum = smbios_max_frequency_mhz(smbios_table())
    if maximum and base and not (base <= maximum <= 2 * base):
        maximum = 0

    return {
        "cpu": name.strip(),
        "vendor": vendor.strip(),
        "packages": 1,
        "cores": {
            "physical": len(topology) or logical,
            "logical": logical,
            "online": logical,
        },
        "frequency": {"base": base, "max": maximum},
        "coreTypes": core_types,
        "temperature": None,
        "march": microarchitecture(),
        "numaNodes": numa_nodes() or 1,
        "codeName": None,
        "technology": None,
    }


def machine_arch() -> str:
    import platform

    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        return "64"
    if machine in ("arm64", "aarch64"):
        return "arm64"
    return "32"


def microarchitecture() -> str | None:
    """x86-64 microarchitecture level from CPU feature bits (x86-64 psABI)."""
    arch = machine_arch()
    if arch == "arm64":
        return "aarch64"
    if arch != "64" or not IS_WINDOWS:
        return None
    # PF_SSE3_INSTRUCTIONS_AVAILABLE=13, PF_AVX_INSTRUCTIONS_AVAILABLE=17,
    # PF_AVX2_INSTRUCTIONS_AVAILABLE=22, PF_AVX512F_INSTRUCTIONS_AVAILABLE=27
    has = lambda feature: bool(kernel32.IsProcessorFeaturePresent(feature))  # noqa: E731
    if has(27):
        return "x86_64-v4"
    if has(22):
        return "x86_64-v3"
    if has(13) and has(17):
        return "x86_64-v2"
    return "x86_64"


def locale_info() -> str:
    for variable in ("LC_ALL", "LANG"):
        value = os.environ.get(variable)
        if value:
            return value

    buffer = ctypes.create_unicode_buffer(85)
    size = kernel32.GetUserDefaultLocaleName(buffer, len(buffer))
    if size <= 1:
        return "C"
    text = buffer.value
    if len(text) > 2 and text[2] == "-":
        text = text[:2] + "_" + text[3:]

    # fastfetch switches the console to UTF-8 at startup, so initCP is 65001.
    code_page = 65001
    names = {
        65001: "UTF-8",
        65000: "UTF-7",
        1200: "UTF-16LE",
        1201: "UTF-16BE",
        936: "GBK",
        54936: "GB18030",
        950: "BIG5",
        932: "Shift_JIS",
        949: "EUC-KR",
        20932: "EUC-JP",
        20866: "KOI8-R",
        21866: "KOI8-U",
        20127: "US-ASCII",
    }
    if code_page:
        suffix = names.get(code_page)
        if suffix is None:
            suffix = (
                f"Windows-{code_page}"
                if code_page == 874 or 1250 <= code_page <= 1258
                else f"CP{code_page}"
            )
        text = f"{text}.{suffix}"
    else:
        # fastfetch switches the console to UTF-8 at startup on Windows.
        text = f"{text}.UTF-8"
    return text


def uptime_ms() -> int:
    if not IS_WINDOWS:
        return 0
    return int(kernel32.GetTickCount64())


def user_name() -> str:
    if IS_WINDOWS and advapi32 is not None:
        size = wt.DWORD(257)
        buffer = ctypes.create_unicode_buffer(size.value)
        if advapi32.GetUserNameW(buffer, ctypes.byref(size)):
            return buffer.value
    return os.environ.get("USERNAME") or os.environ.get("USER") or "user"


def user_sid() -> str:
    """SID of the current user, as fastfetch reports it for the Title module."""
    if not IS_WINDOWS or advapi32 is None:
        return ""
    token = ctypes.c_void_p()
    if not advapi32.OpenProcessToken(ctypes.c_void_p(-1), 0x0008, ctypes.byref(token)):
        return ""
    try:
        size = wt.DWORD(0)
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))  # TokenUser
        if not size.value:
            return ""
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi32.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            return ""
        sid_pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = ctypes.c_wchar_p()
        if not advapi32.ConvertSidToStringSidW(
            ctypes.c_void_p(sid_pointer), ctypes.byref(text)
        ):
            return ""
        try:
            return text.value or ""
        finally:
            kernel32.LocalFree(text)
    finally:
        kernel32.CloseHandle(token)


def home_dir() -> str:
    return os.path.expanduser("~").replace("\\", "/") + "/"


def full_user_name() -> str:
    if IS_WINDOWS and secur32 is not None:
        size = wt.ULONG(257)
        buffer = ctypes.create_unicode_buffer(size.value)
        if secur32.GetUserNameExW(3, buffer, ctypes.byref(size)):  # NameDisplay
            return buffer.value
    return ""


def host_name() -> str:
    if IS_WINDOWS:
        # ComputerNameDnsHostname = 1 (preserves the case of the DNS name).
        size = wt.DWORD(257)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.GetComputerNameExW(1, buffer, ctypes.byref(size)):
            return buffer.value
    return os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "localhost"


# --------------------------------------------------------------------------- #
# Appearance: fonts, cursor, icons, WM, theme
# --------------------------------------------------------------------------- #
class LOGFONTW(ctypes.Structure):
    _fields_ = [
        ("lfHeight", ctypes.c_long),
        ("lfWidth", ctypes.c_long),
        ("lfEscapement", ctypes.c_long),
        ("lfOrientation", ctypes.c_long),
        ("lfWeight", ctypes.c_long),
        ("lfItalic", ctypes.c_ubyte),
        ("lfUnderline", ctypes.c_ubyte),
        ("lfStrikeOut", ctypes.c_ubyte),
        ("lfCharSet", ctypes.c_ubyte),
        ("lfOutPrecision", ctypes.c_ubyte),
        ("lfClipPrecision", ctypes.c_ubyte),
        ("lfQuality", ctypes.c_ubyte),
        ("lfPitchAndFamily", ctypes.c_ubyte),
        ("lfFaceName", wt.WCHAR * 32),
    ]


FONT_KEYS = ("CaptionFont", "MenuFont", "MessageFont", "StatusFont")


def fonts() -> list[str]:
    import winreg

    values = registry_values(
        r"Control Panel\Desktop\WindowMetrics", list(FONT_KEYS), root=winreg.HKEY_CURRENT_USER
    )
    out: list[str] = []
    for key in FONT_KEYS:
        blob = values.get(key)
        if not isinstance(blob, bytes) or len(blob) != ctypes.sizeof(LOGFONTW):
            out.append("")
            continue
        font = LOGFONTW.from_buffer_copy(blob)
        text = font.lfFaceName
        if font.lfHeight < 0:
            text += f" ({-font.lfHeight}pt)"
        out.append(text)
    return out


def cursor_info() -> dict:
    import winreg

    theme = registry_value(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", "") or ""
    size = registry_value(winreg.HKEY_CURRENT_USER, r"Control Panel\Cursors", "CursorBaseSize")
    lowered = theme.lower()
    for suffix in ("cursors", "cursor"):
        if lowered.endswith(suffix):
            theme = theme[: -len(suffix)]
            lowered = theme.lower()
    theme = theme.rstrip("_-")
    if not theme:
        theme = "default"
    return {"theme": theme, "size": str(int(size)) if size else ""}


ICON_GUIDS = (
    ("{20D04FE0-3AEA-1069-A2D8-08002B30309D}", "This PC"),
    ("{59031a47-3f72-44a7-89c5-5595fe6b30ee}", "User's Files"),
    ("{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}", "Remote Network"),
    ("{645FF040-5081-101B-9F08-00AA002F954E}", "Recycle Bin"),
    ("{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}", "Control Panel"),
)


def icons_info() -> dict | None:
    import winreg

    base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons"
    values: dict = {}
    for sub in ("NewStartPanel", "ClassicStartMenu"):
        found = registry_values(base + "\\" + sub, [guid for guid, _ in ICON_GUIDS])
        if found:
            values = found
            break
    if not values:
        return {"icons1": "", "icons2": "Recycle Bin"}

    # Values mean "hidden"; Recycle Bin is shown by default.
    hidden = {
        "This PC": values.get(ICON_GUIDS[0][0], 1),
        "User's Files": values.get(ICON_GUIDS[1][0], 1),
        "Remote Network": values.get(ICON_GUIDS[2][0], 1),
        "Recycle Bin": values.get(ICON_GUIDS[3][0], 0),
        "Control Panel": values.get(ICON_GUIDS[4][0], 1),
    }
    if all(hidden.values()):
        return {"icons1": "", "icons2": "All icons are hidden"}
    first = [name for name in ("This PC", "User's Files") if not hidden[name]]
    second = [name for name in ("Remote Network", "Recycle Bin", "Control Panel") if not hidden[name]]
    return {"icons1": ", ".join(first), "icons2": ", ".join(second)}


WM_THEME_COLORS = {
    0x696CC3: "Yellow gold",
    0xFF8C00: "Gold",
    0xF7630C: "Orange bright",
    0xCA5010: "Orange dark",
    0xDA3B01: "Rust",
    0xEF6950: "Pale rust",
    0xD13438: "Brick red",
    0xFF4343: "Mod red",
    0xE74856: "Pale red",
    0xE81123: "Red",
    0xEA005E: "Rose bright",
    0xC30052: "Rose",
    0xE3008C: "Plum light",
    0xBF0077: "Plum",
    0xC239B3: "Orchid light",
    0x9A0089: "Orchid",
    0x0078D4: "Blue",
    0x0063B1: "Navy blue",
    0x8D8BD7: "Purple shadow",
    0x6B69D6: "Purple shadow dark",
    0x8764B8: "Iris pastel",
    0x744DA9: "Iris Spring",
    0xB146C2: "Violet red light",
    0x881798: "Violet red",
    0x0099BC: "Cool blue bright",
    0x2D7D9A: "Cool blue",
    0x00B7C3: "Seafoam",
    0x038387: "Seafoam teal",
    0x00B294: "Mint light",
    0x018574: "Mint dark",
    0x00CC6A: "Turf green",
    0x10893E: "Sport green",
    0x7A7574: "Gray",
    0x5D5A58: "Gray brown",
    0x68768A: "Steel blue",
    0x515C6B: "Metal blue",
    0x567C73: "Pale moss",
    0x486860: "Moss",
    0x498205: "Meadow green",
    0x107C10: "Green",
    0x767676: "Overcast",
    0x4C4A48: "Storm",
    0x69797E: "Blue gray",
    0x4A5459: "Gray dark",
    0x647C64: "Liddy green",
    0x4C574E: "Sage",
    0x807143: "Camouflage desert",
    0x766C59: "Camouflage",
    0x000000: "Black",
    0xFFFFFF: "White",
}


def wm_theme() -> str | None:
    import winreg

    parts: list[str] = []
    theme = registry_value(
        winreg.HKEY_CURRENT_USER,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes",
        "CurrentTheme",
    )
    if theme:
        stem = theme.rsplit("\\", 1)[-1].rsplit(".", 1)[0]
        if stem:
            parts.append(stem[0].upper() + stem[1:])

    accent = registry_value(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM", "AccentColor")
    if isinstance(accent, int):
        rgb = ((accent & 0xFF) << 16) | (accent & 0xFF00) | ((accent >> 16) & 0xFF)
    else:
        colorization = registry_value(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM", "ColorizationColor"
        )
        rgb = (colorization & 0xFFFFFF) if isinstance(colorization, int) else None
    if rgb is not None:
        parts.append(WM_THEME_COLORS.get(rgb) or f"#{rgb:06X}")

    text = " - ".join(parts)

    personalize = registry_values(
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ["SystemUsesLightTheme", "AppsUseLightTheme"],
        root=winreg.HKEY_CURRENT_USER,
    )
    if personalize:
        system = personalize.get("SystemUsesLightTheme", 1)
        apps = personalize.get("AppsUseLightTheme", 1)
        # fastfetch appends the light/dark suffix with a space, not a " - " separator.
        suffix = f"System: {'Light' if system else 'Dark'}, Apps: {'Light' if apps else 'Dark'}"
        text = f"{text} ({suffix})" if text else suffix

    return text or None


def wm_info() -> dict | None:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    dwm = os.path.join(root, "System32", "dwm.exe")
    if not os.path.exists(dwm):
        return None
    return {
        "processName": "dwm.exe",
        "prettyName": "Desktop Window Manager",
        "protocolName": "",
        "pluginName": "",
        "version": file_version(dwm) or "",
    }


def theme_info() -> dict:
    import platform

    try:
        major = int(platform.release().split(".")[0])
    except (ValueError, IndexError):
        major = 10
    if major >= 10:
        return {"theme1": "Fluent", "theme2": ""}
    if major >= 8:
        return {"theme1": "Metro", "theme2": ""}
    return {"theme1": "Aero", "theme2": ""}


# --------------------------------------------------------------------------- #
# Packages
# --------------------------------------------------------------------------- #
def _count_children(path: str, ignore: str | None = None) -> int:
    try:
        entries = os.listdir(path)
    except OSError:
        return 0
    count = 0
    for entry in entries:
        if ignore is not None and entry.lower() == ignore.lower():
            continue
        if os.path.isdir(os.path.join(path, entry)):
            count += 1
    return count


def packages() -> dict:
    import json

    home = os.path.expanduser("~")
    scoop_root = None
    config = os.path.join(home, ".config", "scoop", "config.json")
    if os.path.exists(config):
        try:
            with open(config, encoding="utf-8") as handle:
                scoop_root = json.load(handle).get("root_path")
        except (OSError, ValueError):
            scoop_root = None
    user_root = scoop_root or os.path.join(home, "scoop")
    scoop_user = _count_children(os.path.join(user_root, "apps"), "scoop")
    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    scoop_global = _count_children(os.path.join(program_data, "scoop", "apps"), "scoop")

    choco = 0
    choco_root = os.environ.get("ChocolateyInstall")
    if choco_root:
        choco = _count_children(os.path.join(choco_root, "lib"), "choco")

    result = {"all": scoop_user + scoop_global + choco}
    if choco:
        result["choco"] = choco
    if scoop_global:
        result["scoopGlobal"] = scoop_global
    if scoop_user:
        result["scoopUser"] = scoop_user
    return result
