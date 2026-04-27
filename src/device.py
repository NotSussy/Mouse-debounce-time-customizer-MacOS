"""
HID communication layer for Glorious mice.
Uses macOS IOKit directly — no external Python packages required.
"""
from . import macos_hid

PROTOCOL_GLORIOUS   = "glorious"    # VID 0x258A — vendor-specific 0xFF00 interface
PROTOCOL_SINOWEALTH = "sinowealth"  # VID 0x3794 — Generic Desktop interface, different command set

# (vendor_id, product_id, display_name, config_usage_page, config_usage, protocol)
SUPPORTED_DEVICES = [
    (0x258A, 0x0033, "Glorious Model O-",        0xFF00, 0x0000, PROTOCOL_GLORIOUS),
    (0x258A, 0x0036, "Glorious Model O",          0xFF00, 0x0000, PROTOCOL_GLORIOUS),
    (0x258A, 0x0049, "Glorious Model O 2",        0xFF00, 0x0000, PROTOCOL_GLORIOUS),
    (0x3794, 0xA000, "Glorious Model O Eternal",  0x0001, 0x0006, PROTOCOL_SINOWEALTH),
]

# Glorious (0x258A) supports 1–16 ms
DEBOUNCE_MIN = 1
DEBOUNCE_MAX = 16

# SINOWEALTH (0x3794) supports even values 4–16 ms (stored as ms // 2)
SINOWEALTH_DEBOUNCE_MIN  = 4
SINOWEALTH_DEBOUNCE_MAX  = 16
SINOWEALTH_DEBOUNCE_STEP = 2

# Glorious original protocol constants
_REPORT_LEN   = 65
_CMD_HEADER   = 0x04
_CMD_DEBOUNCE = 0x0D

# SINOWEALTH protocol constants (from libratbag driver-sinowealth.c and gloriousctl)
_SW_REPORT_LEN    = 6
_SW_REPORT_ID     = 0x05   # SINOWEALTH_REPORT_ID_CMD
_SW_CMD_DEBOUNCE  = 0x1A   # CMD_DEBOUNCE


def _config_interface(vid: int, pid: int, cfg_page: int, cfg_usage: int):
    """Return the first matching HID interface dict, or None."""
    for iface in macos_hid.enumerate_hid(vid=vid, pid=pid):
        if iface["usage_page"] != cfg_page:
            continue
        if cfg_usage and iface["usage"] != cfg_usage:
            continue
        return iface
    return None


def find_device():
    """Return (True, device_name, protocol) if a supported mouse is found, else (None, None, None)."""
    for vid, pid, name, page, usage, protocol in SUPPORTED_DEVICES:
        if _config_interface(vid, pid, page, usage) is not None:
            return True, name, protocol
    return None, None, None


def list_devices() -> list:
    """Return ALL HID interfaces for every supported mouse (diagnostics)."""
    results = []
    seen_keys = set()
    for vid, pid, name, *_ in SUPPORTED_DEVICES:
        if (vid, pid) in seen_keys:
            continue
        seen_keys.add((vid, pid))
        for iface in macos_hid.enumerate_hid(vid=vid, pid=pid):
            results.append({"name": name, "vid": f"0x{vid:04X}",
                            "pid": f"0x{pid:04X}", **iface})
    return results


def scan_all_hid() -> list:
    """Return every HID interface on any connected Glorious/SINOWEALTH device."""
    seen_vids = {vid for vid, *_ in SUPPORTED_DEVICES}
    results = []
    for vid in seen_vids:
        results.extend(macos_hid.enumerate_hid(vid=vid))
    return results


def _build_glorious_packet(ms: int) -> bytes:
    """65-byte vendor-specific report for original Glorious mice (VID 0x258A)."""
    pkt = bytearray(_REPORT_LEN)
    pkt[0] = 0x00          # report ID
    pkt[1] = _CMD_HEADER
    pkt[2] = _CMD_DEBOUNCE
    pkt[3] = 0x00
    pkt[4] = ms & 0xFF
    return bytes(pkt)


def _build_sinowealth_packet(ms: int) -> bytes:
    """
    6-byte feature report for SINOWEALTH mice (VID 0x3794, e.g. Model O Eternal).
    Protocol from libratbag driver-sinowealth.c / gloriousctl:
      [0] 0x05  report ID (SINOWEALTH_REPORT_ID_CMD)
      [1] 0x1A  command: set debounce
      [2] N/2   debounce in 2ms units: 4ms→2, 6ms→3, 8ms→4, 10ms→5, 12ms→6, 14ms→7, 16ms→8
      [3] 0x00
      [4] 0x00
      [5] 0x00
    """
    return bytes([_SW_REPORT_ID, _SW_CMD_DEBOUNCE, ms // 2, 0x00, 0x00, 0x00])


def set_debounce(ms: int, verbose: bool = False) -> str:
    """
    Set debounce time on the connected mouse.
    Returns device name on success. Raises ValueError or RuntimeError.
    """
    last_err = None

    for vid, pid, name, cfg_page, cfg_usage, protocol in SUPPORTED_DEVICES:
        iface = _config_interface(vid, pid, cfg_page, cfg_usage)
        if iface is None:
            continue

        if protocol == PROTOCOL_SINOWEALTH:
            if not SINOWEALTH_DEBOUNCE_MIN <= ms <= SINOWEALTH_DEBOUNCE_MAX:
                raise ValueError(
                    f"Debounce must be {SINOWEALTH_DEBOUNCE_MIN}–{SINOWEALTH_DEBOUNCE_MAX} ms "
                    f"(even values only) for {name}, got {ms}"
                )
            if ms % 2 != 0:
                raise ValueError(
                    f"Debounce must be an even number of ms for {name}, got {ms} "
                    f"(try {ms - 1} or {ms + 1})"
                )
            pkt = _build_sinowealth_packet(ms)
            report_types = [(macos_hid._kIOHIDReportTypeFeature, "feature")]
        else:
            if not DEBOUNCE_MIN <= ms <= DEBOUNCE_MAX:
                raise ValueError(f"Debounce must be {DEBOUNCE_MIN}–{DEBOUNCE_MAX} ms, got {ms}")
            pkt = _build_glorious_packet(ms)
            report_types = [
                (macos_hid._kIOHIDReportTypeOutput,  "output"),
                (macos_hid._kIOHIDReportTypeFeature, "feature"),
            ]

        if verbose:
            print(f"Found {name} ({protocol}) — "
                  f"usagePage=0x{cfg_page:04X} usage=0x{cfg_usage:04X}")
            print(f"Packet: {pkt.hex(' ')}")

        for rtype, rtype_name in report_types:
            if verbose:
                print(f"  Trying {rtype_name} report …")
            try:
                macos_hid.send_output_report(
                    vid, pid, cfg_page, pkt,
                    usage=cfg_usage, report_type=rtype,
                )
                if verbose:
                    print(f"  → {rtype_name} report sent OK")
                return name
            except OSError as exc:
                last_err = exc
                if "not found" in str(exc):
                    break
                if verbose:
                    print(f"  → failed: {exc}")

    raise RuntimeError(
        "No supported Glorious mouse found.\n"
        "Make sure the mouse is connected via USB (not a wireless dongle).\n\n"
        f"Last error: {last_err}"
    )


def probe_device() -> list:
    """
    Try GET_REPORT on report IDs 0x00–0x0F on all SINOWEALTH interfaces.
    Returns a list of dicts for every report ID that responded successfully.
    """
    _PROBE_TYPES = [
        (macos_hid._kIOHIDReportTypeFeature, "feature"),
        (macos_hid._kIOHIDReportTypeOutput,  "input"),
    ]
    results = []
    seen_ifaces = set()

    for vid, pid, name, page, usage, protocol in SUPPORTED_DEVICES:
        if protocol != PROTOCOL_SINOWEALTH:
            continue
        key = (vid, pid, page, usage)
        if key in seen_ifaces:
            continue
        seen_ifaces.add(key)
        if _config_interface(vid, pid, page, usage) is None:
            continue
        for report_id in range(0x00, 0x10):
            for rtype, rtype_name in _PROBE_TYPES:
                try:
                    data = macos_hid.get_report(
                        vid, pid, page, report_id,
                        length=65, report_type=rtype, usage=usage,
                    )
                    results.append({
                        "name":      name,
                        "iface":     f"usagePage=0x{page:04X} usage=0x{usage:04X}",
                        "report_id": report_id,
                        "type":      rtype_name,
                        "data":      data.hex(" "),
                    })
                except OSError:
                    pass
    return results
