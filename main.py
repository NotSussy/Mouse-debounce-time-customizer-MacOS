#!/usr/bin/env python3
"""
Mouse Debounce Time Customizer — Glorious Model O (macOS)

Usage:
    python main.py               Launch GUI
    python main.py --set <ms>    Set debounce in ms via CLI
    python main.py --list        List connected Glorious HID interfaces
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


def _cli_list() -> None:
    from src.device import list_devices

    devices = list_devices()
    if not devices:
        print("No Glorious mice found.")
        return

    print(f"Found {len(devices)} HID interface(s):\n")
    for d in devices:
        print(
            f"  {d['name']}\n"
            f"    Interface : {d['interface']}\n"
            f"    Usage page: {d['usage_page']}\n"
            f"    Usage     : {d['usage']}\n"
            f"    Product   : {d['product']}\n"
            f"    Path      : {d['path']}\n"
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
        "--verbose", "-v",
        action="store_true",
        help="Print HID packet bytes (useful with --set for debugging)",
    )

    args = parser.parse_args()

    if args.list:
        _cli_list()
        return

    if args.set is not None:
        _cli_set(args.set, args.verbose)
        return

    # No flags → open GUI
    from src.gui import run
    run()


if __name__ == "__main__":
    main()
