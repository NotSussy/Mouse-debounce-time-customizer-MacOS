"""
macOS GUI for the Glorious mouse debounce controller.
Uses tkinter (bundled with Python) so no extra GUI dependency is needed.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from .device import (
    DEBOUNCE_MAX,
    DEBOUNCE_MIN,
    find_device,
    set_debounce,
)

_ACCENT = "#007AFF"
_GREEN = "#34C759"
_RED = "#FF3B30"
_FONT_TITLE = ("Helvetica Neue", 18, "bold")
_FONT_BODY = ("Helvetica Neue", 12)
_FONT_SMALL = ("Helvetica Neue", 10)
_FONT_VALUE = ("Helvetica Neue", 36, "bold")


class DebounceApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Mouse Debounce Controller")
        self.resizable(False, False)
        self.configure(bg="white")
        self._build_ui()
        self._refresh_device_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = tk.Frame(self, bg="white", padx=30, pady=24)
        outer.pack(fill="both", expand=True)

        # Header
        tk.Label(
            outer,
            text="Glorious Mouse Debounce",
            font=_FONT_TITLE,
            bg="white",
        ).pack(anchor="w")

        # Device status badge
        self._status_var = tk.StringVar(value="Scanning for device…")
        self._status_lbl = tk.Label(
            outer,
            textvariable=self._status_var,
            font=_FONT_BODY,
            bg="white",
            fg="gray",
        )
        self._status_lbl.pack(anchor="w", pady=(4, 16))

        # ── Slider card ────────────────────────────────────────────────
        card = tk.Frame(outer, bg="#F2F2F7", bd=0, relief="flat", padx=20, pady=16)
        card.pack(fill="x")

        tk.Label(
            card,
            text=f"Debounce Time  ({DEBOUNCE_MIN}–{DEBOUNCE_MAX} ms)",
            font=_FONT_BODY,
            bg="#F2F2F7",
            fg="#3C3C43",
        ).pack(anchor="w")

        # Large numeric readout
        self._ms_var = tk.IntVar(value=4)
        self._value_lbl = tk.Label(
            card,
            text="4 ms",
            font=_FONT_VALUE,
            bg="#F2F2F7",
            fg=_ACCENT,
        )
        self._value_lbl.pack(pady=(8, 4))

        # Slider
        self._slider = ttk.Scale(
            card,
            from_=DEBOUNCE_MIN,
            to=DEBOUNCE_MAX,
            orient="horizontal",
            variable=self._ms_var,
            length=320,
            command=self._on_slider,
        )
        self._slider.pack()

        # Min / max labels
        row = tk.Frame(card, bg="#F2F2F7")
        row.pack(fill="x", pady=(2, 0))
        tk.Label(row, text=f"{DEBOUNCE_MIN} ms  (faster)", font=_FONT_SMALL, bg="#F2F2F7", fg="gray").pack(side="left")
        tk.Label(row, text=f"{DEBOUNCE_MAX} ms  (more stable)", font=_FONT_SMALL, bg="#F2F2F7", fg="gray").pack(side="right")

        # ── Hint text ─────────────────────────────────────────────────
        tk.Label(
            outer,
            text=(
                "Lower  →  faster response, may cause accidental double-clicks\n"
                "Higher →  fewer accidental double-clicks, slightly slower"
            ),
            font=_FONT_SMALL,
            bg="white",
            fg="#8E8E93",
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

        # ── Apply button ──────────────────────────────────────────────
        self._apply_btn = tk.Button(
            outer,
            text="Apply",
            font=("Helvetica Neue", 14),
            bg=_ACCENT,
            fg="white",
            activebackground="#005EC4",
            activeforeground="white",
            relief="flat",
            padx=24,
            pady=8,
            cursor="hand2",
            bd=0,
            highlightthickness=0,
            command=self._apply,
        )
        self._apply_btn.pack(pady=(18, 0))

        # Result / feedback label
        self._result_var = tk.StringVar()
        tk.Label(
            outer,
            textvariable=self._result_var,
            font=_FONT_SMALL,
            bg="white",
            fg=_GREEN,
        ).pack(pady=(6, 0))

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_slider(self, raw_val: str) -> None:
        ms = round(float(raw_val))
        self._ms_var.set(ms)
        self._value_lbl.config(text=f"{ms} ms")

    def _refresh_device_status(self) -> None:
        _, name = find_device()
        if name:
            self._status_var.set(f"Connected: {name}")
            self._status_lbl.config(fg=_GREEN)
        else:
            self._status_var.set("No Glorious mouse detected — connect via USB")
            self._status_lbl.config(fg=_RED)

    def _apply(self) -> None:
        ms = self._ms_var.get()
        self._result_var.set("")
        try:
            name = set_debounce(ms)
            self._result_var.set(f"✓  Set to {ms} ms on {name}")
            self._refresh_device_status()
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)


def run() -> None:
    app = DebounceApp()
    app.mainloop()
