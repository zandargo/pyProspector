"""launcher.py

PyInstaller entry point for pyProspector.

Configures the runtime environment, sets the Playwright browsers path to the
directory shipped inside the installer, then hands control to the Streamlit CLI.
A background thread opens the default browser after the server is ready.
"""

import os
import sys
import threading
import time
import webbrowser

_PORT = 8501


def _open_browser() -> None:
    """Open the default browser after Streamlit has had time to start."""
    time.sleep(3)
    webbrowser.open(f"http://localhost:{_PORT}")


def main() -> None:
    # ── Resolve paths ─────────────────────────────────────────────────────────
    if getattr(sys, "frozen", False):
        # PyInstaller one-dir bundle:
        #   sys.executable  -> …/pyProspector/pyProspector.exe
        #   sys._MEIPASS    -> …/pyProspector/_internal/
        internal_dir = sys._MEIPASS
        install_dir = os.path.dirname(sys.executable)

        # Direct Playwright to the Chromium browser bundled by the installer.
        browsers_path = os.path.join(install_dir, "playwright-browsers")
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", browsers_path)
    else:
        internal_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(internal_dir, "app.py")

    # ── Streamlit configuration ───────────────────────────────────────────────
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_SERVER_PORT", str(_PORT))

    # ── Open the browser once Streamlit is ready ───────────────────────────────
    threading.Thread(target=_open_browser, daemon=True).start()

    # ── Launch Streamlit ──────────────────────────────────────────────────────
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        f"--server.port={_PORT}",
        "--server.headless=true",
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
