# FileFinder+

Desktop file browser, UTF-8 text/shell editor and explicit shell runner. Python 3.10+, Tkinter, Bash, Linux desktop or VNC. No App Store dependency; standalone and reusable. No telemetry, automatic execution, upload, file deletion or persistent history.

Run `python3 filefinderplus.py` or pass a folder. Open folders by double-clicking, use Up/Home/path bar, select files, then Open text. Hidden files are shown; links are labelled. Text editing is limited to regular non-symlink UTF-8 files without NUL bytes, at most 2 MiB. Binary files are rejected, not decoded or executed. Text uses exact newline bytes when opened; editing can change them. Save and Save as confirm the destination and overwriting. Existing source bytes are rechecked before saving; changed files are refused. Close/open prompts for unsaved edits. Saves preserve permissions but are in-place, not crash-atomic; back up important files. Local files and file paths may contain private data.

Run .sh confirms the path and working folder. Bash executes the selected on-disk script with your current permissions, no sudo added. Scripts are NOT sandboxed: they can change/delete files, use the network and launch processes. Only run trusted scripts. stdin is closed: interactive password prompts are unsupported. Output is capped at 1 MiB, displayed as text. Stop requests SIGTERM to the process group; detached children or scripts ignoring signals may continue. File changes between confirmation and execution are possible: use stable trusted files. No safety verdict is made by listing a file.

`BrowserFrame(parent, start=None, select_only=False, selection_callback=None)` is the reusable component. Pack/grid its `.frame`. `.selected_paths()` returns a tuple of Paths. `select_only=True` removes editing/execution, suitable for upload selection. Callback receives selected paths. Call `.close()` before destroying a standalone window to handle dirty edits/running script.

App Store Install checks Tk and copies the reusable module into `~/.local/share/filefinderplus/filefinderplus.py`. It replaces that module when reinstalling/updating. Run starts the standalone window. Pushpuffin imports that installed module; no remote download on Run. Tests: `python3 -m unittest -v`. Version 1.0.1. Linux/Xvfb tested; physical Raspberry Pi, macOS and Windows untested. Headless DietPi needs a desktop/VNC session; a bare SSH console cannot show this window.

## Install repair (1.0.1)

If Tk is missing and apt-get is available while running as root, the reviewed install hook announces and installs python3-tk. Otherwise it stops with instructions. It does not install a desktop. The run hook reports missing or inaccessible DISPLAY with desktop/VNC guidance instead of a traceback.
