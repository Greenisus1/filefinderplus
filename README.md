# FileFinder+ 1.1.2

Terminal file browser, UTF-8 line editor and explicit shell runner. Works over interactive SSH with no desktop or Tk. Optional Tk GUI stays available. Standalone, no App Store dependency. No telemetry, automatic execution, upload, file deletion or persistent history.

    python3 filefinderplus.py
    python3 filefinderplus.py /path/to/folder
    python3 filefinderplus.py --gui

Terminal: arrows (or j/k), Enter, Esc/q. Cyan header and highlighted selection; monochrome works when colors are unavailable. Open folders, go up/home/by-path, select a file then view/edit/run. View scrolls with arrows. Editor offers replace/insert/delete line, buffer view, Save and Save as. It is a line editor, not a full-screen cursor editor; new lines end in LF. Leaving edited content asks before discarding. Save confirms exact destination and overwriting. Existing source bytes are rechecked; changes are refused. Saves preserve permissions but are in-place, not crash-atomic. Back up important files.

Regular non-symlink UTF-8 files only, without NUL, max 2 MiB. Binary files refused. Hidden files shown, links labelled. Preview/UI replaces terminal control and invisible formatting characters; original bytes are not changed just by viewing. Terminal names/prompts are clipped to screen width. Noninteractive/no-TTY terminals get a clear error, not a fake working UI. Use a Unicode-capable monospace SSH terminal.

Run .sh first shows exact path/working folder and a warning, then explicit confirmation. Bash runs the on-disk script with current permissions, no sudo added. NOT sandboxed: scripts can change/delete files, use network or launch programs. Only run trusted scripts. stdin is closed, so interactive prompts are unsupported. In terminal mode output goes directly to the terminal (including control sequences) and is not capped; terminal scrollback is controlled by your terminal. Ctrl-C sends SIGTERM to its process group, with explicit force-kill choice if it ignores stop. Detached children may remain. GUI output stays capped at 1 MiB with Stop button. File changes between confirmation and run are possible; use stable trusted files.

## Optional GUI and reuse

    bash app-store.sh install
    bash app-store.sh run
    bash app-store.sh gui

Install needs no Tk/display and copies filefinderplus.py, terminal_browser.py and terminal_ui.py into ~/.local/share/filefinderplus. Reinstall replaces these modules. `gui` checks/installs missing python3-tk only root+apt, then requires desktop/VNC; Python --gui needs Tk already installed. GUI path bar, multiselect and text editing remain. Pushpuffin still uses the reusable Tk BrowserFrame and still needs desktop/VNC; it is not converted by this update.

`BrowserFrame(parent, start=None, select_only=False, selection_callback=None)` exposes `.frame`, `.selected_paths()`, callback, `.close()`. `select_only` removes editor/run. No remote downloads on Run.

Python 3.10+, stdlib curses, Bash and Linux. Tests: python3 -m unittest -v. Linux PTY terminal capture and virtual-display GUI tested; physical Pi/non-Linux untested. Resize and tiny terminals are clipped rather than crashing, but 80x24 or larger is recommended.

1.1.2 adds reusable terminal pick_paths(ui,start=None) for Pushpuffin multiselect; no edit/run in picker.

1.1.2: terminal lists support PageUp/PageDown, Home and End for large folders. Picker menus use same controls; no file/upload effects from navigation. Corrected terminal title.
