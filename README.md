# Mouse Debounce Controller — macOS

Raise or lower the **click debounce time** on your **Glorious Model O** (and O−, O 2) mouse on macOS — no Windows, no Glorious CORE, no virtual machine.

---

## What is debounce time?

Debounce time is how long the mouse ignores repeated signals after a click to filter out mechanical bounce.

| Value | Effect |
|-------|--------|
| **1 ms** | Fastest response — may cause unintended double-clicks |
| **4 ms** | Good balance (common factory default) |
| **16 ms** | Most stable — slightly slower perceived response |

---

## Supported mice

| Mouse | VID:PID |
|-------|---------|
| Glorious Model O  | `0x258A:0x0036` |
| Glorious Model O− | `0x258A:0x0033` |
| Glorious Model O 2 | `0x258A:0x0049` |

> The mouse **must be connected via USB cable** — wireless dongles don't expose the HID config interface.

---

## How to get the app

### Option 1 — Build a standalone `.app` (recommended)

You get a double-clickable **MouseDebounce.app** you can drop in `/Applications`.

**Requirements:** macOS 10.13+, Python 3.8+ ([download](https://www.python.org/downloads/macos/))

```bash
# 1. Clone or download this repo, then open Terminal in the folder:
cd Mouse-debounce-time-customizer-MacOS

# 2. Run the one-command build script:
chmod +x build_app.sh
./build_app.sh

# 3. The app appears in dist/:
open dist/
# Drag MouseDebounce.app to /Applications and double-click it.
```

> **First launch warning:** macOS may say _"unidentified developer"_.  
> Right-click the app → **Open** → **Open**. You only need to do this once.

---

### Option 2 — Run directly from Python (no build needed)

```bash
# One-time setup:
chmod +x setup.sh && ./setup.sh

# Launch the GUI every time:
source .venv/bin/activate
python main.py
```

---

## macOS permissions

If the app shows **"No Glorious mouse detected"** even though the mouse is plugged in, macOS is blocking HID access.

**Fix (30 seconds):**
1. Click **"Fix Permissions…"** inside the app  
   — it opens System Settings automatically.
2. In **Privacy & Security → Input Monitoring**, click **＋** and add  
   **MouseDebounce.app** (or Terminal if running from the command line).
3. Click **Apply** in the app again.

---

## CLI usage

```bash
source .venv/bin/activate

python main.py --set 4      # Set 4 ms debounce
python main.py --set 1      # 1 ms — fastest response
python main.py --set 16     # 16 ms — most stable
python main.py --list       # Show all detected HID interfaces
python main.py --set 4 -v   # Verbose: print raw HID bytes

# If permission is still denied, prefix with sudo:
sudo python main.py --set 4
```

---

## How it works

The Glorious Model O exposes two USB HID interfaces:

| Interface | Purpose |
|-----------|---------|
| Standard HID (`usage_page 0x0001`) | Mouse movement and buttons |
| Vendor HID (`usage_page 0xFF00`) | Configuration commands |

This tool writes a 65-byte output report to the vendor interface:

```
Byte  0   0x00  HID report ID
Byte  1   0x04  Glorious command header
Byte  2   0x0D  Sub-command: set debounce
Byte  3   0x00  Reserved
Byte  4   N     Debounce in ms (1–16)
Bytes 5–64      0x00 padding
```

Protocol based on community reverse-engineering of Glorious CORE.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No mouse found" | USB cable required (not wireless); try **Fix Permissions…** or `sudo` |
| Setting applied but feels unchanged | Power-cycle the mouse (unplug and replug) |
| `ModuleNotFoundError: hid` | Run `pip install hid` inside the virtual environment |
| macOS Gatekeeper warning on first launch | Right-click → Open → Open (once only) |
