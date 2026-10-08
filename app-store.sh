#!/bin/bash
# pi-app-store: 1
set -eu
cd -- "$(dirname -- "$0")"
case "${1:-}" in
 install)
  python3 -c 'import tkinter' || { echo 'Install python3-tk and use a desktop or VNC.'; exit 1; }
  mkdir -p "$HOME/.local/share/filefinderplus"
  cp -- filefinderplus.py "$HOME/.local/share/filefinderplus/filefinderplus.py"
  ;;
 run) exec python3 filefinderplus.py ;;
 *) echo 'Usage: bash app-store.sh install|run'; exit 2 ;;
esac
