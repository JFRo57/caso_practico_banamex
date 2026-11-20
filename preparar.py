#!/usr/bin/env python3
"""Preparador nativo Windows/macOS/Linux. Usa preferentemente los iniciadores."""
import subprocess
import sys
from scripts.native_start import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nDemo detenida.")
        sys.exit(0)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Preparación incompleta: {error}", file=sys.stderr)
        sys.exit(1)
