#!/usr/bin/env python3
"""SuperMedicine native desktop launcher."""

from __future__ import annotations

import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))


def main(argv: list[str] | None = None) -> int:
    """Run desktop self-test or launch the native pywebview application."""
    args = list(sys.argv[1:] if argv is None else argv)
    from core.web.desktop import desktop_self_test, launch_desktop

    if args and args[0] == "--self-test":
        report_path: Path | None = None
        if len(args) == 3 and args[1] == "--self-test-report":
            report_path = Path(args[2]).expanduser()
        elif len(args) != 1:
            sys.stderr.write(
                "usage: gui_entry.py [--self-test [--self-test-report PATH]]\n"
            )
            return 2
        report = desktop_self_test()
        serialized = json.dumps(report, ensure_ascii=False)
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(serialized + "\n", encoding="utf-8")
        else:
            sys.stdout.write(serialized)
        return 0 if report["ok"] else 1
    if args:
        sys.stderr.write(
            "usage: gui_entry.py [--self-test [--self-test-report PATH]]\n"
        )
        return 2
    try:
        launch_desktop()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        sys.stderr.write(f"Desktop startup failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
