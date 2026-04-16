# Mouse Debounce Time Customizer — macOS

Raise or lower the **click debounce time** on your **Glorious Model O** (and O−, O 2) mouse directly from macOS — no Windows, no Glorious CORE, no virtual machine required.

---

## What is debounce time?

Debounce time is how long the mouse ignores repeated signals after a click to filter out mechanical bounce.

| Value | Effect |
|-------|--------|
| **1 ms** | Fastest response, may cause unintended double-clicks |
| **4 ms** | Good balance (factory default on most units) |
| **16 ms** | Most stable, slightly slower perceived response |

---

## Supported mice

| Mouse | VID:PID |
|-------|---------|
| Glorious Model O  | `0x258A:0x0036` |
| Glorious Model O− | `0x258A:0x0033` |
| Glorious Model O 2 | `0x258A:0x0049` |

> The mouse **must be connected via USB cable**. Wireless dongles do not expose the HID configuration interface.

---

## Requirements

- macOS 10.13 or newer
- Python 3.8+
- Glorious Model O connected via USB

---

## Setup

```bash
chmod +x setup.sh
./setup.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Usage

### GUI (recommended)

```bash
source .venv/bin/activate
python main.py
```

A window opens with a slider. Drag to the desired debounce time and click **Apply**.

### CLI

```bash
source .venv/bin/activate

python main.py --set 4      # Set 4 ms debounce
python main.py --set 1      # 1 ms — fastest
python main.py --set 16     # 16 ms — most stable
python main.py --list       # Show all detected HID interfaces
python main.py --set 4 -v   # Verbose: print raw HID bytes
```

---

## macOS permissions

If you see **"No supported Glorious mouse found"** even though the mouse is plugged in:

1. **Try sudo** (quickest fix):
   ```bash
   sudo python main.py --set 4
   ```

2. **Grant Input Monitoring permission** to Terminal (or your IDE):
   `System Preferences → Privacy & Security → Input Monitoring → ＋ Terminal`

3. Run `python main.py --list` to see all detected HID interfaces for your mouse. If usage_page `0xff00` doesn't appear, the configuration interface may not be accessible on your OS version.

---

## How it works

The Glorious Model O exposes two USB HID interfaces:

| Interface | Purpose |
|-----------|---------|
| Standard HID (usage page `0x0001`) | Mouse movement and buttons |
| Vendor HID (usage page `0xFF00`) | Configuration commands |

This tool writes a 65-byte HID output report to the vendor interface:

```
Byte  0   0x00  HID report ID
Byte  1   0x04  Glorious command header
Byte  2   0x0D  Sub-command: set debounce
Byte  3   0x00  Reserved
Byte  4   N     Debounce value in ms (1–16)
Bytes 5–64      0x00 padding
```

Protocol based on community reverse-engineering of the Glorious CORE software.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Device not found | Run with `sudo`; check USB cable (not wireless) |
| Setting appears to apply but feels unchanged | Some firmware versions require the mouse to be power-cycled |
| `ModuleNotFoundError: hid` | Run `pip install hid` inside the virtual environment |
| Permission denied on macOS Ventura+ | Grant Input Monitoring to Terminal in System Settings |
