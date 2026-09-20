from __future__ import annotations

import argparse

from src.app.application import ScreenTranslatorApplication


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Screen Translator for Windows 10/11")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    application = ScreenTranslatorApplication(debug=args.debug)
    return application.run()


if __name__ == "__main__":
    raise SystemExit(main())
