"""
HID communication layer for Glorious Model O mice.
Uses macOS IOKit directly — no external Python packages required.
"""
from . import macos_hid

GLORIOUS_VID = 0x258A

SUPPORTED_PIDS: dict = {
    0x0033: "Glorious Model O-",
    0x0036: "Glorious Model O",
    0x0049: "Glorious Model O 2",
}

DEBOUNCE_MIN = 1
DEBOUNCE_MAX = 16

_REPORT_LEN    = 65
_CMD_HEADER    = 0x04
_CMD_DEBOUNCE  = 0x0D
_CONFIG_IFACE  = 0xFF00  # vendor-defined HID usage page for config


def find_device():
    """Return (True, device_name) if a supported mouse is found, else (None, None)."""
    for pid, name in SUPPORTED_PIDS.items():
        for d in macos_hid.enumerate_hid(vid=GLORIOUS_VID, pid=pid):
            if d["usage_page"] == _CONFIG_IFACE:
                return True, name
    return None, None


def list_devices() -> list:
    """Return all detected Glorious HID interfaces (for diagnostics)."""
    results = []
    for pid, name in SUPPORTED_PIDS.items():
        for d in macos_hid.enumerate_hid(vid=GLORIOUS_VID, pid=pid):
            results.append({"name": name, **d})
    return results


def _build_debounce_packet(ms: int) -> bytes:
    """
    65-byte HID output report for Glorious debounce command:
      [0] 0x00  report ID
      [1] 0x04  Glorious command header
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
    Set debounce time on the connected Glorious mouse.
    Returns device name on success. Raises ValueError or RuntimeError.
    """
    if not DEBOUNCE_MIN <= ms <= DEBOUNCE_MAX:
        raise ValueError(f"Debounce must be {DEBOUNCE_MIN}–{DEBOUNCE_MAX} ms, got {ms}")

    pkt = _build_debounce_packet(ms)
    if verbose:
        print(f"Packet: {pkt.hex(' ')}")

    last_err = None
    for pid, name in SUPPORTED_PIDS.items():
        if verbose:
            print(f"Trying {name} (PID 0x{pid:04X}) …")
        try:
            macos_hid.send_output_report(GLORIOUS_VID, pid, _CONFIG_IFACE, pkt)
            if verbose:
                print(f"  → sent OK")
            return name
        except OSError as exc:
            last_err = exc
            if "not found" in str(exc):
                continue
            raise  # re-raise permission / open errors immediately

    raise RuntimeError(
        "No supported Glorious mouse found.\n"
        "Make sure the mouse is connected via USB (not a wireless dongle).\n\n"
        f"Last error: {last_err}"
    )
