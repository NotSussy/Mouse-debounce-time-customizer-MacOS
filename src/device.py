"""
HID communication layer for Glorious mice.
Uses macOS IOKit directly — no external Python packages required.
"""
from . import macos_hid

# (vendor_id, product_id, display_name, config_usage_page, config_usage, report_id)
#
# config_usage_page / config_usage: the HID interface used for configuration.
#   Glorious original mice: vendor-specific page 0xFF00, any usage.
#   Model O Eternal (SINOWEALTH chip): only has Generic Desktop (0x0001)
#     interfaces. We try the keyboard-style sub-interface (usage 0x0006)
#     and the mouse interface (usage 0x0002), each with report IDs 0x00
#     and 0x04, until one succeeds.
SUPPORTED_DEVICES = [
    (0x258A, 0x0033, "Glorious Model O-",        0xFF00, 0x0000, 0x00),
    (0x258A, 0x0036, "Glorious Model O",          0xFF00, 0x0000, 0x00),
    (0x258A, 0x0049, "Glorious Model O 2",        0xFF00, 0x0000, 0x00),
    (0x3794, 0xA000, "Glorious Model O Eternal",  0x0001, 0x0006, 0x00),
    (0x3794, 0xA000, "Glorious Model O Eternal",  0x0001, 0x0006, 0x04),
    (0x3794, 0xA000, "Glorious Model O Eternal",  0x0001, 0x0002, 0x00),
    (0x3794, 0xA000, "Glorious Model O Eternal",  0x0001, 0x0002, 0x04),
]

DEBOUNCE_MIN = 1
DEBOUNCE_MAX = 16

_REPORT_LEN   = 65
_CMD_HEADER   = 0x04
_CMD_DEBOUNCE = 0x0D


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
    """Return (True, device_name) if a supported mouse is found, else (None, None)."""
    seen = set()
    for vid, pid, name, page, usage, _rid in SUPPORTED_DEVICES:
        key = (vid, pid, page, usage)
        if key in seen:
            continue
        seen.add(key)
        if _config_interface(vid, pid, page, usage) is not None:
            return True, name
    return None, None


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


def _build_debounce_packet(ms: int, report_id: int = 0x00) -> bytes:
    """
    65-byte HID output report — Glorious/SINOWEALTH debounce command:
      [0] report_id  HID report ID (0x00 for original Glorious; try 0x04 for SINOWEALTH)
      [1] 0x04       command header
      [2] 0x0D       sub-command: set debounce
      [3] 0x00       reserved
      [4] N          debounce in ms (1–16)
    """
    pkt = bytearray(_REPORT_LEN)
    pkt[0] = report_id & 0xFF
    pkt[1] = _CMD_HEADER
    pkt[2] = _CMD_DEBOUNCE
    pkt[3] = 0x00
    pkt[4] = ms & 0xFF
    return bytes(pkt)


def set_debounce(ms: int, verbose: bool = False) -> str:
    """
    Set debounce time on the connected mouse.
    Returns device name on success. Raises ValueError or RuntimeError.
    """
    if not DEBOUNCE_MIN <= ms <= DEBOUNCE_MAX:
        raise ValueError(f"Debounce must be {DEBOUNCE_MIN}–{DEBOUNCE_MAX} ms, got {ms}")

    # Report types to try in order: output (1), then feature (2)
    _REPORT_TYPES = [
        (macos_hid._kIOHIDReportTypeOutput,  "output"),
        (macos_hid._kIOHIDReportTypeFeature, "feature"),
    ]

    last_err = None
    for vid, pid, name, cfg_page, cfg_usage, report_id in SUPPORTED_DEVICES:
        iface = _config_interface(vid, pid, cfg_page, cfg_usage)
        if iface is None:
            continue
        pkt = _build_debounce_packet(ms, report_id)
        if verbose:
            print(f"Found {name} — usagePage=0x{cfg_page:04X} usage=0x{cfg_usage:04X} "
                  f"reportID=0x{report_id:02X}")
            print(f"Packet: {pkt.hex(' ')}")
        for rtype, rtype_name in _REPORT_TYPES:
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
                err_str = str(exc)
                if "not found" in err_str:
                    break        # device not present, skip remaining report types
                if verbose:
                    print(f"  → failed: {exc}")
                continue         # try next report type

    raise RuntimeError(
        "No supported Glorious mouse found.\n"
        "Make sure the mouse is connected via USB (not a wireless dongle).\n\n"
        f"Last error: {last_err}"
    )


def probe_device() -> list:
    """
    Try GET_REPORT on every report ID 0x00–0x0F across all interfaces and
    report types for connected SINOWEALTH (VID 0x3794) devices.
    Returns a list of dicts describing every report ID that responded successfully.
    """
    _PROBE_TYPES = [
        (macos_hid._kIOHIDReportTypeFeature, "feature"),
        (macos_hid._kIOHIDReportTypeOutput,  "input"),
    ]
    results = []
    seen_ifaces = set()

    for vid, pid, name, page, usage, _rid in SUPPORTED_DEVICES:
        if vid != 0x3794:
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
                        "name":       name,
                        "iface":      f"usagePage=0x{page:04X} usage=0x{usage:04X}",
                        "report_id":  report_id,
                        "type":       rtype_name,
                        "data":       data.hex(" "),
                    })
                except OSError:
                    pass
    return results
