#!/usr/bin/env bash
# Frameless desktop window around the Toastmasters Tools hub.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 desktop/launch.py
