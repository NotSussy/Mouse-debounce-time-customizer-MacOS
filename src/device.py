"""
HID communication layer for Glorious Model O mice.

Protocol based on community reverse-engineering of the Glorious CORE software.
The mouse exposes a vendor-specific HID interface (usage_page=0xFF00) used for
configuration commands, separate from the standard mouse HID interface.
"""

import hid

GLORIOUS_VID = 0x258A

# Known product IDs for Glorious Model O family
SUPPORTED_PIDS: dict[int, str] = {
    0x0033: "Glorious Model O-",
    0x0036: "Glorious Model O",
    0x0049: "Glorious Model O 2",
}

DEBOUNCE_MIN = 1
DEBOUNCE_MAX = 16

# HID report size: 1-byte report ID + 64 bytes payload
_REPORT_LEN = 65

# Glorious command bytes for debounce
_CMD_HEADER = 0x04
_CMD_DEBOUNCE = 0x0D


def find_device() -> tuple[bytes | None, str | None]:
    """
    Search HID enumeration for a Glorious config interface (usage_page 0xFF00).
    Returns (path, device_name) or (None, None) if not found.
    """
    for pid, name in SUPPORTED_PIDS.items():
        for info in hid.enumerate(GLORIOUS_VID, pid):
            if info.get("usage_page") == 0xFF00:
                return info["path"], name
    return None, None


def list_devices() -> list[dict]:
    """Return all detected Glorious HID interfaces for diagnostics."""
    results = []
    for pid, name in SUPPORTED_PIDS.items():
        for info in hid.enumerate(GLORIOUS_VID, pid):
            results.append(
                {
                    "name": name,
                    "path": info["path"],
                    "usage_page": hex(info.get("usage_page", 0)),
                    "usage": hex(info.get("usage", 0)),
                    "interface": info.get("interface_number", -1),
                    "manufacturer": info.get("manufacturer_string", ""),
                    "product": info.get("product_string", ""),
                }
            )
    return results


def _build_debounce_packet(ms: int) -> bytes:
    """
    Build the 65-byte HID output report for setting debounce.

    Byte layout (Glorious Model O protocol):
      [0]  0x00  HID report ID (required by hidapi for output reports)
      [1]  0x04  Glorious command header
      [2]  0x0D  Sub-command: set debounce time
      [3]  0x00  Reserved
      [4]  N     Debounce value in milliseconds (1–16)
      [5–64]     0x00 padding
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

    Args:
        ms:      Debounce time in milliseconds (1–16).
        verbose: Print HID packet details to stdout.

    Returns:
        Device name string on success.

    Raises:
        ValueError:   ms is outside the valid range.
        RuntimeError: Mouse not found or write failed.
    """
    if not DEBOUNCE_MIN <= ms <= DEBOUNCE_MAX:
        raise ValueError(
            f"Debounce must be {DEBOUNCE_MIN}–{DEBOUNCE_MAX} ms, got {ms}"
        )

    path, name = find_device()
    if path is None:
        raise RuntimeError(
            "No supported Glorious mouse found.\n"
            "Make sure the mouse is connected via USB (not a wireless dongle).\n"
            "On macOS you may need to run with sudo, or grant Input Monitoring\n"
            "permission: System Preferences → Privacy → Input Monitoring."
        )

    pkt = _build_debounce_packet(ms)

    if verbose:
        print(f"Device : {name}")
        print(f"Path   : {path}")
        print(f"Packet : {pkt.hex(' ')}")

    dev = hid.Device(path=path)
    try:
        written = dev.write(pkt)
        if verbose:
            print(f"Wrote  : {written} bytes")

        # Some firmware versions send a response; timeout is short so we don't block.
        try:
            resp = dev.read(_REPORT_LEN, timeout_ms=500)
            if verbose and resp:
                print(f"Response: {bytes(resp[:8]).hex(' ')}")
        except Exception:
            pass

    finally:
        dev.close()

    return name
