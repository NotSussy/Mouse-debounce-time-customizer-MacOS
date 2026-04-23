"""
HID communication layer for Glorious mice.
Uses macOS IOKit directly — no external Python packages required.
"""
from . import macos_hid

# (vendor_id, product_id, display_name, config_usage_page, config_usage)
#
# config_usage_page / config_usage: the HID interface used for configuration.
#   Glorious original mice: vendor-specific page 0xFF00, any usage.
#   Model O Eternal (SINOWEALTH chip): only has Generic Desktop (0x0001)
#     interfaces; the keyboard-style sub-interface (usage 0x0006) is the
#     one gaming mice of this family use for custom commands.
SUPPORTED_DEVICES = [
    (0x258A, 0x0033, "Glorious Model O-",        0xFF00, 0x0000),
    (0x258A, 0x0036, "Glorious Model O",          0xFF00, 0x0000),
    (0x258A, 0x0049, "Glorious Model O 2",        0xFF00, 0x0000),
    (0x3794, 0xA000, "Glorious Model O Eternal",  0x0001, 0x0006),
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
    for vid, pid, name, page, usage in SUPPORTED_DEVICES:
        if _config_interface(vid, pid, page, usage) is not None:
            return True, name
    return None, None


def list_devices() -> list:
    """Return ALL HID interfaces for every supported mouse (diagnostics)."""
    results = []
    for vid, pid, name, _, _ in SUPPORTED_DEVICES:
        for iface in macos_hid.enumerate_hid(vid=vid, pid=pid):
            results.append({"name": name, "vid": f"0x{vid:04X}",
                            "pid": f"0x{pid:04X}", **iface})
    return results


def scan_all_hid() -> list:
    """Return every HID interface on any connected Glorious/SINOWEALTH device."""
    seen_vids = {vid for vid, _, _, _, _ in SUPPORTED_DEVICES}
    results = []
    for vid in seen_vids:
        results.extend(macos_hid.enumerate_hid(vid=vid))
    return results


def _build_debounce_packet(ms: int) -> bytes:
    """
    65-byte HID output report — Glorious/SINOWEALTH debounce command:
      [0] 0x00  report ID
      [1] 0x04  command header
      [2] 0x0D  sub-command: set debounce
      [3] 0x00  reserved
      [4] N     debounce in ms (1–16)
    """
    pkt = bytearray(_REPORT_LEN)
    pkt[0] = 0x00
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

    pkt = _build_debounce_packet(ms)
    if verbose:
        print(f"Packet: {pkt.hex(' ')}")

    last_err = None
    for vid, pid, name, cfg_page, cfg_usage in SUPPORTED_DEVICES:
        iface = _config_interface(vid, pid, cfg_page, cfg_usage)
        if iface is None:
            continue
        if verbose:
            print(f"Found {name} — interface usagePage=0x{cfg_page:04X} usage=0x{cfg_usage:04X}")
        try:
            macos_hid.send_output_report(
                vid, pid, cfg_page, pkt, usage=cfg_usage
            )
            if verbose:
                print("  → sent OK")
            return name
        except OSError as exc:
            last_err = exc
            if "not found" in str(exc):
                continue
            raise

    raise RuntimeError(
        "No supported Glorious mouse found.\n"
        "Make sure the mouse is connected via USB (not a wireless dongle).\n\n"
        f"Last error: {last_err}"
    )
