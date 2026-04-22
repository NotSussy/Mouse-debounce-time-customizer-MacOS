"""
macOS GUI using osascript (AppleScript) — no tkinter, no Tcl/Tk dependency.
Works on any macOS version without any installed packages.
"""
import subprocess

from .device import DEBOUNCE_MAX, DEBOUNCE_MIN, find_device, set_debounce


def _run(script: str) -> tuple[int, str]:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def run() -> None:
    while True:
        found, name = find_device()
        status = f"Connected: {name}" if found else "No Glorious mouse detected — connect USB"

        options = "{" + ", ".join(
            f'"{i} ms"' for i in range(DEBOUNCE_MIN, DEBOUNCE_MAX + 1)
        ) + "}"

        code, chosen = _run(f'''
            set opts to {options}
            set sel to (choose from list opts ¬
                with title "Glorious Mouse Debounce" ¬
                with prompt "{status}" & return & "Pick a debounce time and click Apply:" ¬
                default items {{"4 ms"}} ¬
                OK button name "Apply" ¬
                cancel button name "Quit")
            if sel is false then return ""
            return item 1 of sel
        ''')

        if code != 0 or not chosen:
            break

        ms = int(chosen.split()[0])

        try:
            dev_name = set_debounce(ms)
            _run(
                f'display notification "Set to {ms} ms on {dev_name}" '
                f'with title "Mouse Debounce Controller"'
            )
        except Exception as exc:
            safe = str(exc).replace('"', "'")
            _run(f'display alert "Error" message "{safe}" as critical')
