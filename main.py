#!/usr/bin/env python3
"""
Mouse Debounce Time Customizer — Glorious Model O (macOS)

Usage:
    python main.py               Launch GUI
    python main.py --set <ms>    Set debounce in ms via CLI
    python main.py --list        List connected Glorious HID interfaces
    python main.py --probe       Probe device report IDs (diagnostics)
    python main.py --verbose     Show HID packet details (use with --set)
"""

import argparse
import sys


def _cli_set(ms: int, verbose: bool) -> None:
    from src.device import set_debounce

    try:
        name = set_debounce(ms, verbose=verbose)
        print(f"✓ Debounce set to {ms} ms on {name}")
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def _cli_probe() -> None:
    from src.device import probe_device

    print("Probing Model O Eternal — trying GET_REPORT for IDs 0x00–0x0F on all interfaces…")
    print("(This may take a few seconds.)\n")
    results = probe_device()
    if not results:
        print("No report IDs responded to GET_REPORT.")
        print("The device may require a different communication method.")
        return
    print(f"Responsive report IDs found ({len(results)}):\n")
    for r in results:
        print(
            f"  {r['iface']}  reportID=0x{r['report_id']:02X}  type={r['type']}\n"
            f"  data: {r['data']}\n"
        )


def _cli_list() -> None:
    from src.device import scan_all_hid

    devices = scan_all_hid()
    if not devices:
        print("No supported Glorious/SINOWEALTH devices found.")
        return

    print(f"Found {len(devices)} HID interface(s):\n")
    for d in devices:
        print(
            f"  VID=0x{d['vendor_id']:04X}  PID=0x{d['product_id']:04X}\n"
            f"    usage_page : 0x{d['usage_page']:04X}\n"
            f"    usage      : 0x{d['usage']:04X}\n"
            f"    interface  : {d['interface_number']}\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mouse-debounce",
        description="Control debounce time on Glorious Model O mice (macOS)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py               # Launch GUI\n"
            "  python main.py --set 4       # 4 ms debounce\n"
            "  python main.py --set 1       # Fastest (1 ms)\n"
            "  python main.py --set 16      # Most stable (16 ms)\n"
            "  python main.py --list        # Show HID interfaces\n"
            "  sudo python main.py --set 4  # If permission denied\n"
        ),
    )
    parser.add_argument(
        "--set", "-s",
        type=int,
        metavar="MS",
        help="Set debounce time in milliseconds (1–16)",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all detected Glorious HID interfaces",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Probe device report IDs via GET_REPORT (diagnostic for SINOWEALTH mice)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print HID packet bytes (useful with --set for debugging)",
    )

    args = parser.parse_args()

    if args.list:
        _cli_list()
        return

    if args.probe:
        _cli_probe()
        return

    if args.set is not None:
        _cli_set(args.set, args.verbose)
        return

    # No flags → open GUI
    from src.gui import run
    run()


if __name__ == "__main__":
    main()
