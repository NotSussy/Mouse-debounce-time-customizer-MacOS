"""
HID communication layer for Glorious mice.
Uses macOS IOKit directly — no external Python packages required.
"""
from . import macos_hid

# (vendor_id, product_id, display_name)
SUPPORTED_DEVICES = [
    (0x258A, 0x0033, "Glorious Model O-"),
    (0x258A, 0x0036, "Glorious Model O"),
    (0x258A, 0x0049, "Glorious Model O 2"),
    (0x3794, 0xA000, "Glorious Model O Eternal"),  # SINOWEALTH chip
]

DEBOUNCE_MIN = 1
DEBOUNCE_MAX = 16

_REPORT_LEN   = 65
_CMD_HEADER   = 0x04
_CMD_DEBOUNCE = 0x0D

# Usage pages that may carry the config interface, in order of preference
_CONFIG_USAGE_PAGES = [0xFF00, 0xFF01, 0xFF10, 0xFF11]


def _all_interfaces(vid: int, pid: int) -> list:
    return macos_hid.enumerate_hid(vid=vid, pid=pid)


def _config_interface(vid: int, pid: int):
    """Return the first interface whose usage_page looks like a vendor config page."""
    for iface in _all_interfaces(vid, pid):
        if iface["usage_page"] in _CONFIG_USAGE_PAGES:
            return iface
    return None


def find_device():
    """Return (True, device_name) if a supported mouse is found, else (None, None)."""
    for vid, pid, name in SUPPORTED_DEVICES:
        if _config_interface(vid, pid) is not None:
            return True, name
    return None, None


def list_devices() -> list:
    """Return ALL HID interfaces for every supported mouse (for diagnostics)."""
    results = []
    for vid, pid, name in SUPPORTED_DEVICES:
        for iface in _all_interfaces(vid, pid):
            results.append({
                "name": name,
                "vid": f"0x{vid:04X}",
                "pid": f"0x{pid:04X}",
                **iface,
            })
    return results


def scan_all_hid() -> list:
    """Return every HID interface on any connected Glorious/SINOWEALTH device."""
    vids = {vid for vid, _, _ in SUPPORTED_DEVICES}
    results = []
    for vid in vids:
        for iface in macos_hid.enumerate_hid(vid=vid):
            results.append(iface)
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
    for vid, pid, name in SUPPORTED_DEVICES:
        iface = _config_interface(vid, pid)
        if iface is None:
            continue
        usage_page = iface["usage_page"]
        if verbose:
            print(f"Trying {name} (VID=0x{vid:04X} PID=0x{pid:04X} usagePage=0x{usage_page:04X}) …")
        try:
            macos_hid.send_output_report(vid, pid, usage_page, pkt)
            if verbose:
                print("  → sent OK")
            return name
        except OSError as exc:
            last_err = exc
            if "not found" in str(exc):
                continue
            raise  # re-raise permission errors immediately

    raise RuntimeError(
        "No supported Glorious mouse found.\n"
        "Make sure the mouse is connected via USB (not a wireless dongle).\n\n"
        f"Last error: {last_err}"
    )
